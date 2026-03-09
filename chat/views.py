
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.utils.safestring import mark_safe
import json
import logging
import os
import time
from typing import Generator
from .models import PDFDocument, ChatSession, ChatMessage, ChatMessageSource, Feedback, SurveyResponse, AboutContent, HowItWorksContent
from .forms import FeedbackForm, SurveyFeedbackForm
from .services import PDFProcessingService, ChatService, EmbeddingService
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

# Initialize services once at module level
chat_service = ChatService()
embedding_service = EmbeddingService()

# Add this simple streaming method to your existing ChatService class
def add_streaming_to_chat_service():
    """Add streaming capability to existing ChatService"""
    def generate_response_stream(self, messages, similar_chunks=None):
        """Simple streaming implementation that works with Django dev server"""
        try:
            # Generate the complete response first
            full_response = self.generate_response(messages, similar_chunks)
            
            # Don't clean here - let JavaScript handle cleaning consistently
            # Split response into words and yield them with small delay
            words = full_response.split()
            for i, word in enumerate(words):
                if i == 0:
                    yield word
                else:
                    yield " " + word
                    
                # Small delay to simulate real streaming
                time.sleep(0.05)
                    
        except Exception as e:
            logger.error(f"Error in streaming generation: {str(e)}")
            yield "I encountered an error while generating a response."
    
    # Add the method to the ChatService class
    ChatService.generate_response_stream = generate_response_stream

# Call this to add streaming support
add_streaming_to_chat_service()


@login_required
def chat_home(request):
    """Main chat interface with caching"""
    cache_key = f"user_sessions_{request.user.id}"
    sessions = cache.get(cache_key)
    
    if sessions is None:
        sessions = list(ChatSession.objects.filter(user=request.user)
                       .select_related('user')
                       .prefetch_related('messages')
                       .order_by('-updated_at')[:10])
        cache.set(cache_key, sessions, 300)
    
    active_session = sessions[0] if sessions else None
    messages = list(active_session.messages.all()) if active_session else []

    context = {
        'sessions': sessions,
        'active_session': active_session,
        'messages': messages,
    }
    return render(request, 'chatbot/chat.html', context)


@login_required
def user_dashboard(request):
    """Dashboard for regular users: upload and view only their documents."""
    documents = PDFDocument.objects.filter(uploaded_by=request.user).order_by('-uploaded_at')
    return render(request, 'chatbot/user_dashboard.html', {
        'documents': documents,
    })


@login_required
def user_upload_pdf(request):
    if request.method == 'POST':
        files = request.FILES.getlist('pdf_files')
        if not files:
            messages.error(request, 'Please select at least one PDF file.')
            return redirect('chatbot:user_dashboard')
        for file in files:
            if not file.name.lower().endswith('.pdf'):
                continue
            try:
                document = PDFDocument.objects.create(
                    title=file.name.replace('.pdf', ''),
                    file=file,
                    uploaded_by=request.user
                )
                pdf_service = PDFProcessingService()
                pdf_service.process_document(document)
            except Exception as e:
                logger.error(f"User upload error: {str(e)}", exc_info=True)
        messages.success(request, 'Upload complete. Documents will appear once processed.')
    return redirect('chatbot:user_dashboard')


@login_required
def create_chat_session(request):
    """Create a new chat session"""
    session = ChatSession.objects.create(
        user=request.user,
        session_name="New Chat"
    )
    cache.delete(f"user_sessions_{request.user.id}")
    return redirect('chatbot:chat_session', session_id=session.id)


@login_required
def chat_session(request, session_id):
    """Display specific chat session with optimized queries"""
    active_session = get_object_or_404(
        ChatSession.objects.select_related('user').prefetch_related('messages'),
        id=session_id, 
        user=request.user
    )
    
    cache_key = f"user_sessions_{request.user.id}"
    sessions = cache.get(cache_key)
    if sessions is None:
        sessions = list(ChatSession.objects.filter(user=request.user)
                       .select_related('user')
                       .order_by('-updated_at'))
        cache.set(cache_key, sessions, 300)
    
    messages = list(active_session.messages.select_related('session').all())

    context = {
        'sessions': sessions,
        'active_session': active_session,
        'messages': messages,
    }
    return render(request, 'chatbot/chat.html', context)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """Handle sending messages in chat with RAG support"""
    try:
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            message_content = data.get('message', '').strip()
            session_id = data.get('session_id')
            streaming = data.get('streaming', False)
        else:
            message_content = request.POST.get('message', '').strip()
            session_id = request.POST.get('session_id')
            streaming = request.POST.get('streaming', 'false').lower() == 'true'

        if not message_content:
            return JsonResponse({'error': 'Message content is required'}, status=400)

        # Get or create session
        if not session_id:
            session = ChatSession.objects.create(
                user=request.user,
                session_name="New Chat"
            )
            cache.delete(f"user_sessions_{request.user.id}")
        else:
            session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        # Create user message
        user_message = ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=message_content
        )

        # Update session title if this is the first message
        if session.messages.count() == 1:
            session.update_title_from_message(message_content)
            # Invalidate cache after session update
            cache.delete(f"user_sessions_{request.user.id}")

        # Get conversation history
        messages = list(session.messages.select_related('session').all())
        
        # Get relevant document chunks using RAG with improved search
        similar_chunks = []
        try:
            # Use expanded search for better results, especially for comparative queries
            similar_chunks = embedding_service.search_similar_chunks_enhanced(
                message_content, 
                top_k=10,  # Increased from 3 to get more relevant content
                similarity_threshold=0.3  # Lowered from 0.4 for broader results
            )
            logger.info(f"Found {len(similar_chunks)} similar chunks for query")
        except Exception as e:
            logger.warning(f"Error in similarity search: {str(e)}")
            # Fallback to original method if enhanced search fails
            try:
                similar_chunks = embedding_service.search_similar_chunks(
                    message_content, 
                    top_k=10,
                    similarity_threshold=0.3
                )
                logger.info(f"Fallback search found {len(similar_chunks)} similar chunks")
            except Exception as fallback_e:
                logger.warning(f"Fallback search also failed: {str(fallback_e)}")
        
        if streaming:
            return send_message_stream(request, session, messages, similar_chunks)
        else:
            # Generate response with context
            response_content = chat_service.generate_response(messages, similar_chunks)
            
            # Save ORIGINAL markdown to database - preserve formatting structure
            assistant_message = ChatMessage.objects.create(
                session=session,
                message_type='assistant',
                content=response_content  # Save original markdown with full structure
            )

            # Invalidate cache after saving message
            cache.delete(f"user_sessions_{request.user.id}")

            # Add sources if chunks were used (UI will render as a separate block)
            sources_data = []
            if similar_chunks:
                def similarity_to_confidence(score: float) -> str:
                    if score >= 0.75:
                        return 'high'
                    if score >= 0.5:
                        return 'medium'
                    return 'low'

                for chunk_data in similar_chunks[:2]:
                    chunk = chunk_data['chunk']
                    assistant_message.sources.add(chunk)
                    score = float(chunk_data.get('similarity', 0.0))
                    # Persist source metadata
                    ChatMessageSource.objects.create(
                        message=assistant_message,
                        chunk=chunk,
                        similarity=score,
                        confidence=similarity_to_confidence(score),
                        url=request.build_absolute_uri(chunk.document.file.url) if hasattr(chunk.document.file, 'url') else ''
                    )
                    sources_data.append({
                        'title': chunk.document.title,
                        'page': chunk.page_number,
                        'similarity': score,
                        'confidence': similarity_to_confidence(score),
                        'url': request.build_absolute_uri(chunk.document.file.url) if hasattr(chunk.document.file, 'url') else ''
                    })

            # Send original markdown - let JavaScript handle cleaning and formatting consistently
            return JsonResponse({
                'status': 'success',
                'response': response_content,  # Send original markdown
                'session_name': session.session_name,
                'session_id': str(session.id),
                'sources': sources_data
            })

    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An error occurred while processing your message'}, status=500)


def send_message_stream(request, session, messages, similar_chunks=None):
    """Fixed streaming response that works with Django dev server"""
    from .services import post_process_response
    
    def generate_stream():
        try:
            full_response = ""
            
            # Generate streaming response - tokens come in real-time now
            for token in chat_service.generate_response_stream(messages, similar_chunks):
                if token:
                    full_response += token
                    
                    # Send token as Server-Sent Event for real-time display
                    yield f"data: {json.dumps({'token': token, 'type': 'token'})}\n\n"
            
            # Save the HTML response directly (no post-processing needed)
            if full_response.strip():
                # Validate response before saving
                from chat.services import validate_chatbot_response
                user_question = messages[-1].content
                is_valid, warnings = validate_chatbot_response(full_response, user_question)
                if warnings:
                    logger.warning(f"Streaming response validation warnings for question '{user_question[:100]}...': {warnings}")
                
                # Save the HTML response to database
                assistant_message = ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=full_response  # Save HTML response directly
                )
                
                # Invalidate cache after saving message
                cache.delete(f"user_sessions_{session.user.id}")
                
                # Add sources if available
                sources_data = []
                if similar_chunks:
                    def similarity_to_confidence(score: float) -> str:
                        if score >= 0.75:
                            return 'high'
                        if score >= 0.5:
                            return 'medium'
                        return 'low'

                    for chunk_data in similar_chunks[:2]:
                        chunk = chunk_data['chunk']
                        assistant_message.sources.add(chunk)
                        score = float(chunk_data.get('similarity', 0.0))
                        ChatMessageSource.objects.create(
                            message=assistant_message,
                            chunk=chunk,
                            similarity=score,
                            confidence=similarity_to_confidence(score),
                            url=''  # Set empty for now, can be updated later if needed
                        )
                        sources_data.append({
                            'title': chunk.document.title,
                            'page': chunk.page_number,
                            'similarity': score,
                            'confidence': similarity_to_confidence(score),
                            'url': request.build_absolute_uri(chunk.document.file.url) if hasattr(chunk.document.file, 'url') else ''
                        })
                else:
                    sources_data = []
            
            # Send completion signal with HTML content for final rendering
            yield f"data: {json.dumps({
                'type': 'complete', 
                'session_name': session.session_name, 
                'session_id': str(session.id),
                'sources': sources_data,
                'final_content': full_response if full_response.strip() else ''
            })}\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred while generating the response'})}\n\n"
    
    # Create streaming response without problematic headers
    response = StreamingHttpResponse(
        generate_stream(),
        content_type='text/event-stream'
    )
    
    # Set only safe headers for Django dev server
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # For nginx
    
    # DO NOT set Connection: keep-alive header - this causes the WSGI error
    # The Django dev server doesn't support this header properly
    
    return response


@login_required
@require_http_methods(["POST"])
def clear_chat(request, session_id):
    """Clear all messages in a chat session"""
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.messages.all().delete()
    return JsonResponse({'status': 'success'})


@login_required
def export_chat(request, session_id):
    """Export chat history as JSON with optimized query"""
    session = get_object_or_404(
        ChatSession.objects.prefetch_related('messages__sources__document'),
        id=session_id, 
        user=request.user
    )
    
    messages = []
    for msg in session.messages.all():
        message_data = {
            'type': msg.message_type,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),
        }
        if msg.sources.exists():
            message_data['sources'] = [{
                'title': source.document.title,
                'page': source.page_number
            } for source in msg.sources.all()]
        messages.append(message_data)

    response = HttpResponse(
        json.dumps({
            'session_name': session.session_name,
            'messages': messages
        }, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename=chat_export_{session_id}.json'
    return response


@login_required
@require_http_methods(["POST"])
def rename_session(request, session_id):
    """Rename a chat session"""
    try:
        data = json.loads(request.body)
        new_name = data.get('name', '').strip()
        if not new_name:
            return JsonResponse({'error': 'Name cannot be empty'}, status=400)

        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.session_name = new_name
        session.save()
        
        cache.delete(f"user_sessions_{request.user.id}")
        
        return JsonResponse({'status': 'success', 'name': new_name})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def delete_session(request, session_id):
    """Delete a chat session"""
    try:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.delete()
        cache.delete(f"user_sessions_{request.user.id}")
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'status': 'success', 'message': 'Chat session deleted successfully.'})
        else:
            messages.success(request, 'Chat session deleted successfully.')
            return redirect('chatbot:chat_home')
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'status': 'error', 'message': 'Failed to delete chat session.'}, status=500)
        else:
            messages.error(request, 'Failed to delete chat session.')
            return redirect('chatbot:chat_home')


# Admin Views
@staff_member_required
def admin_dashboard(request):
    """Optimized admin dashboard"""
    documents = PDFDocument.objects.select_related('uploaded_by').order_by('-uploaded_at')

    search_query = request.GET.get('search', '')
    if search_query:
        documents = documents.filter(
            Q(title__icontains=search_query) |
            Q(file__icontains=search_query)
        )

    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    documents_page = paginator.get_page(page_number)

    stats = PDFDocument.objects.aggregate(
        total_docs=Count('id'),
        processed_docs=Count('id', filter=Q(processed=True)),
        pending_docs=Count('id', filter=Q(processed=False))
    )

    cache_key = "total_chunks_count"
    total_chunks = cache.get(cache_key)
    if total_chunks is None:
        total_chunks = PDFDocument.objects.filter(processed=True).aggregate(
            total_chunks=Count('chunks')
        )['total_chunks'] or 0
        cache.set(cache_key, total_chunks, 300)

    feedback_list = Feedback.objects.select_related('user').order_by('-created_at')[:20]
    recent_survey_responses = SurveyResponse.objects.select_related('user').order_by('-created_at')[:20]

    context = {
        'documents': documents_page,
        'search_query': search_query,
        'total_docs': stats['total_docs'],
        'processed_docs': stats['processed_docs'],
        'pending_docs': stats['pending_docs'],
        'total_chunks': total_chunks,
        'paginator': paginator,
        'feedback_list': feedback_list,
        'recent_survey_responses': recent_survey_responses,
    }
    return render(request, 'chatbot/admin_dashboard.html', context)


@login_required
def feedback_view(request):
    """Render and process the Community Engagement Compass Feedback Survey."""
    if request.method == 'POST':
        form = SurveyFeedbackForm(request.POST)
        if form.is_valid():
            SurveyResponse.objects.create(
                user=request.user if request.user.is_authenticated else None,
                ease_of_use=form.cleaned_data['ease_of_use'],
                relevance=form.cleaned_data['relevance'],
                trust=form.cleaned_data['trust'],
                citations_helpfulness=form.cleaned_data['citations_helpfulness'],
                likelihood_of_use=form.cleaned_data['likelihood_of_use'],
                additional_sources=form.cleaned_data.get('additional_sources', ''),
                open_feedback=form.cleaned_data.get('open_feedback', ''),
            )
            messages.success(request, 'Thank you for sharing your insights and feedback! To learn more about Health Justice’s offerings, visit https://healthjustice.co.')
            return render(request, 'chatbot/feedback_thanks.html', {"redirect_url": 
                request.build_absolute_uri(
                    # Use absolute URL for robustness
                    redirect('chatbot:chat_home').url
                )
            })
    else:
        form = SurveyFeedbackForm()

    return render(request, 'chatbot/feedback.html', {"form": form})


@staff_member_required
def upload_pdf(request):
    """Optimized PDF upload with better error handling"""
    if request.method == 'POST':
        files = request.FILES.getlist('pdf_files')

        if not files:
            messages.error(request, 'Please select at least one PDF file.')
            return redirect('chatbot:admin_dashboard')

        uploaded_count = 0
        error_count = 0
        
        for file in files:
            if not file.name.lower().endswith('.pdf'):
                logger.warning(f"Skipping non-PDF file: {file.name}")
                continue
                
            try:
                if file.size > 50 * 1024 * 1024:
                    logger.warning(f"File too large: {file.name} ({file.size} bytes)")
                    error_count += 1
                    continue

                document = PDFDocument.objects.create(
                    title=file.name.replace('.pdf', ''),
                    file=file,
                    uploaded_by=request.user
                )

                logger.info(f"Starting to process document: {document.title}")
                pdf_service = PDFProcessingService()
                pdf_service.process_document(document)
                uploaded_count += 1
                
                cache.delete("total_chunks_count")
                logger.info(f"Successfully processed: {document.title}")

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing {file.name}: {str(e)}", exc_info=True)
                try:
                    document.processing_error = str(e)
                    document.processed = False
                    document.save()
                except:
                    pass

        if uploaded_count > 0:
            messages.success(request, f'Successfully uploaded and processed {uploaded_count} PDF(s).')
        if error_count > 0:
            messages.warning(request, f'{error_count} file(s) failed to process. Check the logs for details.')
        if uploaded_count == 0 and error_count == 0:
            messages.info(request, 'No PDF files were found to process.')

    return redirect('chatbot:admin_dashboard')


@staff_member_required
def delete_document(request, doc_id):
    """Delete document with proper cleanup"""
    if request.method == 'POST':
        document = get_object_or_404(PDFDocument, id=doc_id)
        document_title = document.title

        try:
            if document.file and os.path.exists(document.file.path):
                os.remove(document.file.path)

            document.delete()
            cache.delete("total_chunks_count")
            
            try:
                embedding_service.update_faiss_index()
            except Exception as e:
                logger.warning(f"Error updating FAISS index after deletion: {str(e)}")

            messages.success(request, f'Document "{document_title}" deleted successfully.')
            
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            messages.error(request, f'Error deleting document: {str(e)}')

    return redirect('chatbot:admin_dashboard')


@staff_member_required
def reprocess_document(request, doc_id):
    """Reprocess document with better error handling"""
    if request.method == 'POST':
        document = get_object_or_404(PDFDocument, id=doc_id)

        try:
            chunks_count = document.chunks.count()
            document.chunks.all().delete()
            logger.info(f"Deleted {chunks_count} existing chunks")

            document.processed = False
            document.processing_error = None
            document.save()

            pdf_service = PDFProcessingService()
            pdf_service.process_document(document)
            
            cache.delete("total_chunks_count")
            embedding_service.update_faiss_index()

            messages.success(request, f'Document "{document.title}" reprocessed successfully.')
            
        except Exception as e:
            logger.error(f"Error reprocessing document: {str(e)}", exc_info=True)
            messages.error(request, f'Error reprocessing document: {str(e)}')

    return redirect('chatbot:admin_dashboard')


@staff_member_required
def document_details(request, doc_id):
    """View document details with pagination"""
    document = get_object_or_404(
        PDFDocument.objects.prefetch_related('chunks'),
        id=doc_id
    )
    
    chunks = document.chunks.all().order_by('chunk_index')
    
    paginator = Paginator(chunks, 10)
    page_number = request.GET.get('page')
    chunks_page = paginator.get_page(page_number)

    context = {
        'document': document,
        'chunks': chunks_page,
        'chunk_count': chunks.count(),
        'paginator': paginator,
    }
    return render(request, 'chatbot/document_details.html', context)


def health_check(request):
    """Health check for monitoring"""
    try:
        PDFDocument.objects.count()
        
        chat_service_ready = chat_service._model is not None
        embedding_service_ready = embedding_service._model is not None
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'ok',
            'chat_service': 'ready' if chat_service_ready else 'not ready',
            'embedding_service': 'ready' if embedding_service_ready else 'not ready',
            'timestamp': time.time()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }, status=503)





# Add to your views.py
def emergency_memory_cleanup():
    """Call this if you still get memory errors"""
    import gc
    import torch
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    gc.collect()
    
    # Restart services if needed
    # chat_service.clear_cache()
    
# Call before heavy operations
emergency_memory_cleanup()


def about_content(request):
    """View to get About content for AJAX requests"""
    try:
        content = AboutContent.get_active_content()
        if content:
            return JsonResponse({
                'title': content.title,
                'content': mark_safe(content.content)
            })
        else:
            return JsonResponse({
                'title': 'About Community Engagement Compass',
                'content': '<p>Welcome to the Community Engagement Compass, a tool designed to support healthcare and public health professionals in applying trusted community engagement frameworks.</p>'
            })
    except Exception as e:
        logger.error(f"Error fetching about content: {str(e)}")
        return JsonResponse({
            'title': 'About Community Engagement Compass',
            'content': '<p>Welcome to the Community Engagement Compass.</p>'
        })


def how_it_works_content(request):
    """View to get How It Works content for AJAX requests"""
    try:
        content = HowItWorksContent.get_active_content()
        if content:
            return JsonResponse({
                'title': content.title,
                'content': mark_safe(content.content)
            })
        else:
            return JsonResponse({
                'title': 'How It Works',
                'content': '''
                <ol>
                    <li>Type a question about your uploaded documents or topics.</li>
                    <li>Toggle "Enable streaming responses" to see tokens as they generate.</li>
                    <li>Sources are listed under replies when available; click links to view.</li>
                    <li>Use "New Chat" to start a fresh conversation thread.</li>
                </ol>
                '''
            })
    except Exception as e:
        logger.error(f"Error fetching how it works content: {str(e)}")
        return JsonResponse({
            'title': 'How It Works',
            'content': '<p>How the Community Engagement Compass works.</p>'
        })