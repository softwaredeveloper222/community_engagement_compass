# import PyPDF2
# import numpy as np
# import faiss
# import pickle
# import os
# import threading
# from sentence_transformers import SentenceTransformer
# import ollama
# from django.conf import settings
# from .models import DocumentChunk, EmbeddingIndex
# import logging
# from typing import List, Dict, Generator, Optional
# import asyncio
# import json
# from django.http import StreamingHttpResponse
# import time

# logger = logging.getLogger(__name__)


# class PDFProcessingService:
#     def __init__(self):
#         self.chunk_size = 512  # Reduced for better performance
#         self.chunk_overlap = 50  # Reduced overlap

#     def extract_text_from_pdf(self, pdf_path):
#         """Extract text from PDF file"""
#         text_pages = []
#         try:
#             with open(pdf_path, 'rb') as file:
#                 pdf_reader = PyPDF2.PdfReader(file)
#                 for page_num, page in enumerate(pdf_reader.pages):
#                     text = page.extract_text()
#                     if text.strip():
#                         text_pages.append({
#                             'page': page_num + 1,
#                             'text': text.strip()
#                         })
#         except Exception as e:
#             logger.error(f"Error extracting text from PDF: {str(e)}")
#             raise

#         return text_pages

#     def create_chunks(self, text_pages):
#         """Split text into chunks with improved strategy"""
#         chunks = []
#         chunk_index = 0

#         for page_data in text_pages:
#             text = page_data['text']
#             page_num = page_data['page']

#             # Improved chunking strategy - split by sentences first
#             sentences = text.split('. ')
#             current_chunk = ""
            
#             for sentence in sentences:
#                 # If adding this sentence would exceed chunk size, save current chunk
#                 if len(current_chunk.split()) + len(sentence.split()) > self.chunk_size and current_chunk:
#                     chunks.append({
#                         'content': current_chunk.strip(),
#                         'page_number': page_num,
#                         'chunk_index': chunk_index
#                     })
#                     chunk_index += 1
#                     current_chunk = sentence
#                 else:
#                     current_chunk += ". " + sentence if current_chunk else sentence
            
#             # Add the last chunk if it has content
#             if current_chunk.strip():
#                 chunks.append({
#                     'content': current_chunk.strip(),
#                     'page_number': page_num,
#                     'chunk_index': chunk_index
#                 })
#                 chunk_index += 1

#         return chunks

#     def process_document(self, document):
#         """Process a PDF document and create embeddings"""
#         try:
#             # Extract text
#             text_pages = self.extract_text_from_pdf(document.file.path)

#             # Create chunks
#             chunks = self.create_chunks(text_pages)
#             logger.info(f"Created {len(chunks)} chunks for document: {document.title}")

#             # Get embedding service instance
#             embedding_service = EmbeddingService()

#             # Save chunks to database first
#             chunk_objects = []
#             chunk_contents = []
#             for chunk_data in chunks:
#                 chunk = DocumentChunk.objects.create(
#                     document=document,
#                     content=chunk_data['content'],
#                     page_number=chunk_data['page_number'],
#                     chunk_index=chunk_data['chunk_index']
#                 )
#                 chunk_objects.append(chunk)
#                 chunk_contents.append(chunk_data['content'])

#             # Create embeddings in batch for better performance
#             if chunk_contents:
#                 embeddings = embedding_service.create_embeddings_batch(chunk_contents)
#                 chunk_embeddings = []
                
#                 for chunk, embedding in zip(chunk_objects, embeddings):
#                     chunk.embedding_vector = pickle.dumps(embedding)
#                     chunk.save()
#                     chunk_embeddings.append((chunk.id, embedding))

#             # Incrementally update FAISS index instead of rebuilding
#             embedding_service.add_to_faiss_index(chunk_embeddings)

#             # Mark as processed
#             document.processed = True
#             document.processing_error = None
#             document.save()

#             logger.info(f"Successfully processed document: {document.title}")

#         except Exception as e:
#             document.processing_error = str(e)
#             document.processed = False
#             document.save()
#             logger.error(f"Error processing document {document.title}: {str(e)}")
#             raise


# class EmbeddingService:
#     _instance = None
#     _lock = threading.Lock()
    
#     def __new__(cls):
#         if cls._instance is None:
#             with cls._lock:
#                 if cls._instance is None:
#                     cls._instance = super().__new__(cls)
#         return cls._instance
    
#     def __init__(self):
#         if hasattr(self, 'initialized'):
#             return
            
#         # Use the best embedding model for improved accuracy and retrieval
#         # BAAI/bge-large-en-v1.5 is currently one of the best English embedding models
#         self.model = SentenceTransformer('BAAI/bge-large-en-v1.5')
#         self.dimension = 1024  # Dimension for BAAI/bge-large-en-v1.5
#         self.index_path = os.path.join(settings.MEDIA_ROOT, 'faiss_index.bin')
#         self.mapping_path = os.path.join(settings.MEDIA_ROOT, 'chunk_mapping.pkl')
#         self.initialized = True
#         logger.info(f"Initialized EmbeddingService with BAAI/bge-large-en-v1.5 (dim={self.dimension})")

#     def create_embedding(self, text):
#         """Create embedding for given text with query prefix for BGE model"""
#         # BGE models work better with instruction prefix for queries
#         prefixed_text = f"Represent this sentence for searching relevant passages: {text}"
#         return self.model.encode([prefixed_text], convert_to_tensor=False)[0]
    
#     def create_embeddings_batch(self, texts):
#         """Create embeddings for multiple texts at once (more efficient)"""
#         return self.model.encode(texts, convert_to_tensor=False)

#     def update_faiss_index(self):
#         """Rebuild FAISS index with all chunks"""
#         try:
#             chunks = DocumentChunk.objects.filter(embedding_vector__isnull=False)

#             if not chunks.exists():
#                 logger.warning("No chunks with embeddings found")
#                 return

#             # Collect all embeddings
#             embeddings = []
#             chunk_mapping = []

#             for chunk in chunks:
#                 if chunk.embedding_vector:
#                     embedding = pickle.loads(chunk.embedding_vector)
#                     embeddings.append(embedding)
#                     chunk_mapping.append(chunk.id)

#             if not embeddings:
#                 return

#             # Create FAISS index
#             embeddings_array = np.array(embeddings).astype('float32')  # Use float32 for better precision
#             index = faiss.IndexFlatIP(self.dimension)  # Inner product for similarity
#             faiss.normalize_L2(embeddings_array)  # Normalize for cosine similarity
#             index.add(embeddings_array)

#             # Save index and mapping
#             faiss.write_index(index, self.index_path)
#             with open(self.mapping_path, 'wb') as f:
#                 pickle.dump(chunk_mapping, f)

#             # Update metadata
#             EmbeddingIndex.objects.filter(is_active=True).update(is_active=False)
#             EmbeddingIndex.objects.create(
#                 index_file=self.index_path,
#                 dimension=self.dimension,
#                 total_vectors=len(embeddings),
#                 is_active=True
#             )

#             logger.info(f"Updated FAISS index with {len(embeddings)} vectors")

#         except Exception as e:
#             logger.error(f"Error updating FAISS index: {str(e)}")
#             raise
    
#     def add_to_faiss_index(self, chunk_embeddings):
#         """Add new embeddings to existing FAISS index incrementally"""
#         try:
#             if not chunk_embeddings:
#                 return
                
#             # Load existing index and mapping
#             if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
#                 index = faiss.read_index(self.index_path)
#                 with open(self.mapping_path, 'rb') as f:
#                     chunk_mapping = pickle.load(f)
#             else:
#                 # Create new index if it doesn't exist
#                 index = faiss.IndexFlatIP(self.dimension)
#                 chunk_mapping = []
            
#             # Prepare new embeddings
#             new_embeddings = []
#             new_chunk_ids = []
            
#             for chunk_id, embedding in chunk_embeddings:
#                 new_embeddings.append(embedding)
#                 new_chunk_ids.append(chunk_id)
            
#             if new_embeddings:
#                 # Convert to numpy array and normalize
#                 embeddings_array = np.array(new_embeddings).astype('float32')
#                 faiss.normalize_L2(embeddings_array)
                
#                 # Add to index
#                 index.add(embeddings_array)
                
#                 # Update mapping
#                 chunk_mapping.extend(new_chunk_ids)
                
#                 # Save updated index and mapping
#                 faiss.write_index(index, self.index_path)
#                 with open(self.mapping_path, 'wb') as f:
#                     pickle.dump(chunk_mapping, f)
                
#                 # Update metadata
#                 EmbeddingIndex.objects.filter(is_active=True).update(is_active=False)
#                 EmbeddingIndex.objects.create(
#                     index_file=self.index_path,
#                     dimension=self.dimension,
#                     total_vectors=len(chunk_mapping),
#                     is_active=True
#                 )
                
#                 logger.info(f"Added {len(new_embeddings)} new embeddings to FAISS index")
                
#         except Exception as e:
#             logger.error(f"Error adding to FAISS index: {str(e)}")
#             # Fallback to full rebuild
#             self.update_faiss_index()

#     def search_similar_chunks(self, query_text, top_k=40, similarity_threshold=0.4):
#         """Search for similar chunks using FAISS with improved accuracy"""
#         try:
#             if not os.path.exists(self.index_path) or not os.path.exists(self.mapping_path):
#                 logger.warning("FAISS index not found - no documents have been processed yet")
#                 return []

#             # Load index and mapping
#             index = faiss.read_index(self.index_path)
#             with open(self.mapping_path, 'rb') as f:
#                 chunk_mapping = pickle.load(f)

#             if not chunk_mapping:
#                 logger.warning("No chunks in mapping - index may be empty")
#                 return []

#             # Create query embedding
#             query_embedding = self.create_embedding(query_text)
#             query_vector = np.array([query_embedding]).astype('float32')
#             faiss.normalize_L2(query_vector)

#             # Search with more results to filter by threshold
#             search_k = min(top_k * 3, len(chunk_mapping))  # Get more results to filter
#             scores, indices = index.search(query_vector, search_k)

#             # Get corresponding chunks with better filtering
#             similar_chunks = []
#             for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
#                 if idx < len(chunk_mapping) and score > similarity_threshold:
#                     chunk_id = chunk_mapping[idx]
#                     try:
#                         chunk = DocumentChunk.objects.get(id=chunk_id)
#                         similar_chunks.append({
#                             'chunk': chunk,
#                             'similarity': float(score)
#                         })
#                     except DocumentChunk.DoesNotExist:
#                         logger.warning(f"Chunk {chunk_id} not found in database")
#                         continue
                
#                 # Stop if we have enough high-quality results
#                 if len(similar_chunks) >= top_k:
#                     break

#             # Sort by similarity score (descending)
#             similar_chunks.sort(key=lambda x: x['similarity'], reverse=True)
#             logger.info(f"Found {len(similar_chunks)} similar chunks for query")
#             return similar_chunks[:top_k]

#         except Exception as e:
#             logger.error(f"Error searching similar chunks: {str(e)}", exc_info=True)
#             return []


# class ChatService:
#     _instance = None
#     _lock = threading.Lock()
    
#     def __new__(cls):
#         if cls._instance is None:
#             with cls._lock:
#                 if cls._instance is None:
#                     cls._instance = super().__new__(cls)
#         return cls._instance
    
#     def __init__(self):
#         if hasattr(self, 'initialized'):
#             return
            
#         # Use Ollama for optimized model management
#         self.ollama_client = ollama.Client()
#         self.model_name = "phi4-mini:latest"
        
#         # Test Ollama connection
#         try:
#             models = self.ollama_client.list()
#             available_models = [m.model for m in models['models']]
#             if self.model_name in available_models:
#                 logger.info(f"✓ Ollama connected. Using {self.model_name}")
#                 self.ollama_available = True
#             else:
#                 logger.error(f"Model {self.model_name} not found in Ollama. Available: {available_models}")
#                 self.ollama_available = False
#         except Exception as e:
#             logger.error(f"Failed to connect to Ollama: {e}")
#             self.ollama_available = False
        
#         self.embedding_service = EmbeddingService()
#         self.initialized = True
#         logger.info("ChatService initialized with Ollama backend")

#     def load_model(self):
#         """Load model through Ollama - no manual loading needed"""
#         if not self.ollama_available:
#             raise Exception("Ollama not available. Please ensure Ollama is running and phi3:mini is installed.")
        
#         # Test the model
#         try:
#             response = self.ollama_client.generate(
#                 model=self.model_name,
#                 prompt="Test",
#                 stream=False
#             )
#             logger.info(f"✓ {self.model_name} model ready via Ollama")
#         except Exception as e:
#             logger.error(f"Error testing Ollama model: {str(e)}")
#             raise
    
#     def clear_gpu_cache(self):
#         """Clear GPU cache to free memory"""
#         if torch.cuda.is_available():
#             torch.cuda.empty_cache()

#     # def generate_response(self, messages):
#     #     try:
#     #         if self.model is None:
#     #             self.load_model()
#     #
#     #         # Format conversation history
#     #         conversation = ""
#     #         for msg in messages:
#     #             role = "Human: " if msg.message_type == 'user' else "Assistant: "
#     #             conversation += f"{role}{msg.content}\n"
#     #
#     #         conversation += "Assistant: "
#     #
#     #         # Create input tokens with proper attention mask
#     #         inputs = self.tokenizer(
#     #             conversation,
#     #             return_tensors="pt",
#     #             truncation=True,
#     #             max_length=2048,
#     #             padding=True,
#     #             add_special_tokens=True,
#     #             return_attention_mask=True
#     #         )
#     #
#     #         # Generate response with attention mask
#     #         outputs = self.model.generate(
#     #             input_ids=inputs["input_ids"],
#     #             attention_mask=inputs["attention_mask"],
#     #             max_length=4096,
#     #             num_return_sequences=1,
#     #             temperature=0.7,
#     #             do_sample=True,
#     #             pad_token_id=self.tokenizer.pad_token_id,
#     #             eos_token_id=self.tokenizer.eos_token_id,
#     #             repetition_penalty=1.2,
#     #             no_repeat_ngram_size=3,
#     #             use_cache=True
#     #         )
#     #
#     #         # Decode the response
#     #         response = self.tokenizer.decode(
#     #             outputs[0][inputs["input_ids"].shape[1]:],
#     #             skip_special_tokens=True,
#     #             clean_up_tokenization_spaces=True
#     #         )
#     #
#     #         # Clean up the response
#     #         response = response.strip()
#     #         if not response:
#     #             response = "I apologize, but I couldn't generate a meaningful response. Please try rephrasing your question."
#     #
#     #         return response
#     #
#     #     except Exception as e:
#     #         logger.error(f"Error generating response: {str(e)}")
#     #         raise

#     def get_relevant_context(self, query: str, top_k: int = 5) -> str:
#         """Retrieve relevant context from documents using RAG"""
#         try:
#             similar_chunks = self.embedding_service.search_similar_chunks(query, top_k=top_k)
            
#             if not similar_chunks:
#                 logger.info("No relevant chunks found, will generate response without context")
#                 return ""
            
#             context_parts = []
#             for chunk_data in similar_chunks:
#                 chunk = chunk_data['chunk']
#                 context_parts.append(f"Document: {chunk.document.title}\nContent: {chunk.content}")
            
#             logger.info(f"Found {len(similar_chunks)} relevant chunks for context")
#             return "\n\n".join(context_parts)
#         except Exception as e:
#             logger.error(f"Error retrieving context: {str(e)}")
#             return ""

#     def _format_context_from_chunks(self, similar_chunks) -> str:
#         """Format a context string from provided similar chunks."""
#         try:
#             if not similar_chunks:
#                 return ""
#             context_parts = []
#             for chunk_data in similar_chunks:
#                 chunk = chunk_data['chunk']
#                 context_parts.append(
#                     f"Document: {chunk.document.title}\nContent: {chunk.content}"
#                 )
#             return "\n\n".join(context_parts)
#         except Exception as e:
#             logger.warning(f"Error formatting context from chunks: {e}")
#             return ""
    
#     def generate_response(self, messages, similar_chunks=None):
#         """Generate response with RAG (Retrieval-Augmented Generation) - optimized for speed"""
#         try:
#             if not self.ollama_available:
#                 self.load_model()
            
#             user_prompt = messages[-1].content
            
#             # Get relevant context from documents (prefer provided chunks)
#             context = self._format_context_from_chunks(similar_chunks) if similar_chunks else self.get_relevant_context(user_prompt)
            
#             # Require KB context; don't generate generic answers
#             if not context:
#                 return "I could not find information in the knowledge base about that. Please rephrase or upload relevant documents."
            
#             # Create optimized prompt for Ollama
#             # Replace your system_prompt in both generate_response() and generate_response_stream() with this:

#             # Replace your system_prompt in both generate_response() and generate_response_stream() with this:

#             # Use this exact system prompt in your services.py file:

#             system_prompt = """You are a professional knowledge assistant. Format responses clearly with headings, paragraphs, and occasional bullet lists.

# FORMATTING REQUIREMENTS:

# 1. HEADINGS - Use **bold** for section titles:
#    - Format: **Section Title**
#    - Must be on its own line
#    - Add ONE blank line before it
#    - Add ONE blank line after it
#    - Never use ### or #

# 2. PARAGRAPHS - Use for explanations:
#    - Write 2-4 complete sentences per paragraph
#    - Add ONE blank line between paragraphs
#    - Do NOT start paragraphs with bullets

# 3. BULLET LISTS - Use only for listing items:
#    - Add ONE blank line before the list
#    - Format each bullet: - Item text
#    - Add ONE blank line after the list
#    - Use bullets for 3+ related items only

# EXAMPLE OF CORRECT FORMAT:

# **Consultation**

# Consultation involves seeking advice from community members on specific issues. The Health Department shares information and seeks feedback but retains final decision-making authority.

# Key aspects include:

# - Information sharing without full incorporation of input
# - Feedback is considered but may not influence decisions
# - Health Department retains ultimate authority

# **Collaboration**

# Collaboration involves working together as equal partners. Decisions are made through consensus between all parties.

# WHAT NOT TO DO:
# - Do NOT use bullets for every sentence
# - Do NOT put bullets before headings
# - Do NOT write one-sentence paragraphs followed by bullets
# - Do NOT use ---, ###, or other special characters

# CONTENT RULES:
# - Answer using ONLY the provided context
# - If not in context: "I could not find information in the knowledge base about that."
# - Be clear, professional, and well-structured"""

#             user_message = f"""
# CONTEXT from Knowledge Base:

# {context}

# USER QUESTION:

# {user_prompt}

# Please provide a comprehensive, well-formatted answer using the context above. Structure your response with:
# - Clear headings for main concepts
# - Explanatory paragraphs
# - Bullet points for key details
# - Proper spacing and line breaks

# Remember: Do NOT use ---, ###, or any special markdown characters in your response.
# """




# #             formatted_prompt = f"""### Context (knowledge base excerpts):
# # {context}

# # ### Task:
# # You are a public health expert responding to a question using ONLY the information provided above in the Context section.

# # STRICT RULES:
# # - Do NOT use any outside or prior knowledge.
# # - Do NOT guess or generalize.
# # - Do NOT paraphrase based on your own understanding.
# # - If the answer is not clearly stated in the Context, respond exactly: "I could not find information in the knowledge base about that."

# # INSTRUCTIONS FOR YOUR RESPONSE:
# # - Begin with a simple, direct explanation in full sentences.
# # - Use details and examples from the Context where possible.
# # - If helpful, synthesize across multiple excerpts in the Context.
# # - End your answer with 2–4 concise bullet point takeaways that summarize the key ideas.

# # Maintain a factual, professional tone. Do not mention or reference the Context section in your answer.

# # User question:
# # {user_prompt}

# # ### Response:
# # """




#             # Build prompt with strict instruction to use only the context
# #             formatted_prompt = f"""### Context (knowledge base excerpts):
# # {context}

# # ### Instruction:
# # Using ONLY the information in the Context, write a clear, well-structured answer in full paragraphs. Synthesize across documents when helpful. Do not mention that you used a context. If the answer is not present in the Context, reply exactly: "I could not find information in the knowledge base about that."

# # Guidelines:
# # - Aim for a concise but complete explanation (6-12 sentences)
# # - Use a neutral, informative tone
# # - Avoid bullet lists unless necessary

# # User question:
# # {user_prompt}

# # ### Response:
# # """

#             # Generate response using Ollama
#             response = self.ollama_client.chat(
#                 model=self.model_name,
#                 messages=[
#                     {'role': 'system', 'content': system_prompt},
#                     {'role': 'user', 'content': user_message}
#                 ],
#                 stream=False,
#                 options={
#                     'temperature': 0.3,
#                     'top_p': 0.9,
#                     'repeat_penalty': 1.2,
#                     'num_ctx': 4096,
#                 }
#             )
            
#             generated_text = response['message']['content'].strip()
            
#             if not generated_text:
#                 return "I'm here to help! How can I assist you today?"
                
#             return generated_text

#         except Exception as e:
#             logger.error(f"Error generating response with Ollama: {str(e)}")
#             return "I'm sorry, there was an error processing your request."
    
#     def generate_response_stream(self, messages, similar_chunks=None) -> Generator[str, None, None]:
#         """Generate streaming response with RAG using Ollama backend"""
#         try:
#             if not self.ollama_available:
#                 self.load_model()
            
#             user_prompt = messages[-1].content
            
#             # Get relevant context from documents (prefer provided chunks)
#             context = self._format_context_from_chunks(similar_chunks) if similar_chunks else self.get_relevant_context(user_prompt)
            
#             # Require KB context; don't generate generic answers
#             if not context:
#                 yield "I could not find information in the knowledge base about that. Please rephrase or upload relevant documents."
#                 return
            
#             # Create optimized prompt for Ollama
#             # Replace your system_prompt in both generate_response() and generate_response_stream() with this:

#             # Replace your system_prompt in both generate_response() and generate_response_stream() with this:

#             # Use this exact system prompt in your services.py file:

#             system_prompt = """You are a professional knowledge assistant. Format responses clearly with headings, paragraphs, and occasional bullet lists.

# FORMATTING REQUIREMENTS:

# 1. HEADINGS - Use **bold** for section titles:
#    - Format: **Section Title**
#    - Must be on its own line
#    - Add ONE blank line before it
#    - Add ONE blank line after it
#    - Never use ### or #

# 2. PARAGRAPHS - Use for explanations:
#    - Write 2-4 complete sentences per paragraph
#    - Add ONE blank line between paragraphs
#    - Do NOT start paragraphs with bullets

# 3. BULLET LISTS - Use only for listing items:
#    - Add ONE blank line before the list
#    - Format each bullet: - Item text
#    - Add ONE blank line after the list
#    - Use bullets for 3+ related items only

# EXAMPLE OF CORRECT FORMAT:

# **Consultation**

# Consultation involves seeking advice from community members on specific issues. The Health Department shares information and seeks feedback but retains final decision-making authority.

# Key aspects include:

# - Information sharing without full incorporation of input
# - Feedback is considered but may not influence decisions
# - Health Department retains ultimate authority

# **Collaboration**

# Collaboration involves working together as equal partners. Decisions are made through consensus between all parties.

# WHAT NOT TO DO:
# - Do NOT use bullets for every sentence
# - Do NOT put bullets before headings
# - Do NOT write one-sentence paragraphs followed by bullets
# - Do NOT use ---, ###, or other special characters

# CONTENT RULES:
# - Answer using ONLY the provided context
# - If not in context: "I could not find information in the knowledge base about that."
# - Be clear, professional, and well-structured"""

#             user_message = f"""
# CONTEXT from Knowledge Base:

# {context}

# USER QUESTION:

# {user_prompt}

# Please provide a comprehensive, well-formatted answer using the context above. Structure your response with:
# - Clear headings for main concepts
# - Explanatory paragraphs
# - Bullet points for key details
# - Proper spacing and line breaks

# Remember: Do NOT use ---, ###, or any special markdown characters in your response.
# """



#             # Stream response using Ollama
#             response_stream = self.ollama_client.chat(
#                 model=self.model_name,
#                 messages=[
#                     {'role': 'system', 'content': system_prompt},
#                     {'role': 'user', 'content': user_message}
#                 ],
#                 stream=True,
#                 options={
#                     'temperature': 0.3,
#                     'top_p': 0.9,
#                     'repeat_penalty': 1.2,
#                     'num_ctx': 4096,
#                 }
#             )
            
#             # Stream the response
#             for chunk in response_stream:
#                 if chunk['message']['content']:
#                     yield chunk['message']['content']

#         except Exception as e:
#             logger.error(f"Error generating streaming response with Ollama: {str(e)}", exc_info=True)
#             yield "I'm sorry, there was an error processing your request."

#     # def generate_response(self, messages):
#     #     try:
#     #         # Format prompt
#     #         user_prompt = messages[-1].content  # Assuming the last message is the user's
#     #         formatted_prompt = f"### Instruction:\n{user_prompt}\n\n### Response:\n"
#     #
#     #         inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.device)
#     #         from transformers import TextStreamer
#     #
#     #         # Assuming you've set up the tokenizer and model properly.
#     #         streamer = TextStreamer(self.tokenizer)
#     #
#     #         output = self.model.generate(
#     #             **inputs,
#     #             max_new_tokens=256,
#     #             do_sample=True,
#     #             top_p=0.95,
#     #             temperature=0.7,
#     #             pad_token_id=self.tokenizer.pad_token_id,
#     #             eos_token_id=self.tokenizer.eos_token_id,
#     #             streamer=streamer
#     #         )
#     #
#     #         response = self.tokenizer.decode(output[0], skip_special_tokens=True)
#     #         print("🧠 Model output:", response)
#     #         return response.split("### Response:")[-1].strip()
#     #
#     #     except Exception as e:
#     #         print("❌ Error generating response:", e)
#     #         return "I apologize, but I couldn't generate a meaningful response. Please try rephrasing your question."

import PyPDF2
import numpy as np
import faiss
import pickle
import os
import threading
import re
from sentence_transformers import SentenceTransformer
from groq import Groq
from django.conf import settings
from .models import DocumentChunk, EmbeddingIndex
import logging
from typing import List, Dict, Generator, Optional
import asyncio
import json
from django.http import StreamingHttpResponse
import time

logger = logging.getLogger(__name__)


def validate_chatbot_response(response_text, user_question):
    """
    Check if response follows framework guidelines.
    Returns: (is_valid, warnings_list)
    """
    warnings = []
    
    # Check 1: Inventing specific budget/cost information
    if any(indicator in response_text for indicator in ['$', 'dollars', 'budget of', 'costs around']):
        if 'framework doesn\'t specify' not in response_text.lower():
            warnings.append("BUDGET_INVENTION: Response includes specific costs not in framework")
    
    # Check 2: Out-of-scope questions should acknowledge limitations
    out_of_scope_keywords = [
        'current', 'now', 'today', 'latest', 'recent',
        'covid', 'pandemic',
        'other departments', 'other cities',
        'after 2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'
    ]
    if any(keyword in user_question.lower() for keyword in out_of_scope_keywords):
        if not any(phrase in response_text.lower() for phrase in [
            'framework doesn\'t',
            'document doesn\'t',
            'framework was published',
            'not addressed in the framework',
            'doesn\'t provide information about'
        ]):
            warnings.append("SCOPE_ACKNOWLEDGMENT: Out-of-scope question should acknowledge framework limitations")
    
    # Check 3: Look for overly prescriptive language
    prescriptive_phrases = [
        'you should implement',
        'best practice is to',
        'typically requires',
        'the correct approach is',
        'you must',
        'always do',
        'never do'
    ]
    for phrase in prescriptive_phrases:
        if phrase in response_text.lower():
            if 'framework' not in response_text.lower():
                warnings.append(f"PRESCRIPTIVE_LANGUAGE: Using '{phrase}' without framework attribution")
    
    # Check 4: Creating detailed scenario applications
    scenario_indicators = [
        'for example, you could',
        'step 1:', 'step 2:', 'step 3:',
        'here\'s how to',
        'implementation plan',
        'specific strategies include'
    ]
    if any(indicator in response_text.lower() for indicator in scenario_indicators):
        warnings.append("DETAILED_APPLICATION: May be creating scenarios not in framework")
    
    # Check 5: Length check - very long responses often include extrapolation
    word_count = len(response_text.split())
    if word_count > 400:
        warnings.append(f"LENGTH_WARNING: Response is {word_count} words (may indicate over-elaboration)")
    
    # Log warnings
    if warnings:
        logger.warning(f"Response validation warnings: {warnings}")
        logger.debug(f"Question: {user_question[:100]}...")
        logger.debug(f"Response: {response_text[:200]}...")
    
    # For now, don't block responses, just log
    return len(warnings) == 0, warnings


def validate_chatbot_response_with_rubric(response_text, user_question):
    """
    Enhanced validation that includes rubric scoring.
    Returns: (is_valid, warnings_list, rubric_scores)
    """
    # Get basic validation
    is_valid, warnings = validate_chatbot_response(response_text, user_question)
    
    # Get rubric scores
    try:
        from chat.rubric_validator import ResponseValidator
        rubric_scores = ResponseValidator.get_rubric_score(user_question, response_text)
        
        # Add rubric-specific warnings
        rubric_warnings = []
        if rubric_scores['recognizes_limits'] == 'FAIL':
            rubric_warnings.append("RUBRIC_FAIL: Does not recognize framework limitations")
        elif rubric_scores['recognizes_limits'] == 'PARTIAL':
            rubric_warnings.append("RUBRIC_PARTIAL: Limitation acknowledgment could be improved")
            
        if rubric_scores['avoids_fabrication'] == 'FAIL':
            rubric_warnings.append("RUBRIC_FAIL: Contains fabricated information")
        elif rubric_scores['avoids_fabrication'] == 'PARTIAL':
            rubric_warnings.append("RUBRIC_PARTIAL: Some prescriptive language without attribution")
            
        if rubric_scores['redirects_helpfully'] == 'PARTIAL':
            rubric_warnings.append("RUBRIC_PARTIAL: Could redirect more helpfully after acknowledging limitations")
            
        if rubric_scores['distinguishes_sources'] == 'PARTIAL':
            rubric_warnings.append("RUBRIC_PARTIAL: Blends general advice with framework content")
        
        # Combine warnings
        all_warnings = warnings + rubric_warnings
        
        # Log rubric scores
        logger.info(f"Rubric scores for '{user_question[:50]}...': {rubric_scores}")
        
        return len(all_warnings) == 0, all_warnings, rubric_scores
        
    except ImportError:
        logger.warning("Rubric validator not available, using basic validation only")
        return is_valid, warnings, None


class PDFProcessingService:
    def __init__(self):
        self.chunk_size = 512
        self.chunk_overlap = 50

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF file"""
        text_pages = []
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        text_pages.append({
                            'page': page_num + 1,
                            'text': text.strip()
                        })
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

        return text_pages

    def create_chunks(self, text_pages):
        """Split text into chunks with improved strategy"""
        chunks = []
        chunk_index = 0

        for page_data in text_pages:
            text = page_data['text']
            page_num = page_data['page']

            # Improved chunking strategy - split by sentences first
            sentences = text.split('. ')
            current_chunk = ""
            
            for sentence in sentences:
                # If adding this sentence would exceed chunk size, save current chunk
                if len(current_chunk.split()) + len(sentence.split()) > self.chunk_size and current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'page_number': page_num,
                        'chunk_index': chunk_index
                    })
                    chunk_index += 1
                    current_chunk = sentence
                else:
                    current_chunk += ". " + sentence if current_chunk else sentence
            
            # Add the last chunk if it has content
            if current_chunk.strip():
                chunks.append({
                    'content': current_chunk.strip(),
                    'page_number': page_num,
                    'chunk_index': chunk_index
                })
                chunk_index += 1

        return chunks

    def process_document(self, document):
        """Process a PDF document and create embeddings"""
        try:
            # Extract text
            text_pages = self.extract_text_from_pdf(document.file.path)

            # Create chunks
            chunks = self.create_chunks(text_pages)
            logger.info(f"Created {len(chunks)} chunks for document: {document.title}")

            # Get embedding service instance
            embedding_service = EmbeddingService()

            # Save chunks to database first
            chunk_objects = []
            chunk_contents = []
            for chunk_data in chunks:
                chunk = DocumentChunk.objects.create(
                    document=document,
                    content=chunk_data['content'],
                    page_number=chunk_data['page_number'],
                    chunk_index=chunk_data['chunk_index']
                )
                chunk_objects.append(chunk)
                chunk_contents.append(chunk_data['content'])

            # Create embeddings in batch for better performance
            if chunk_contents:
                embeddings = embedding_service.create_embeddings_batch(chunk_contents)
                chunk_embeddings = []
                
                for chunk, embedding in zip(chunk_objects, embeddings):
                    chunk.embedding_vector = pickle.dumps(embedding)
                    chunk.save()
                    chunk_embeddings.append((chunk.id, embedding))

            # Incrementally update FAISS index instead of rebuilding
            embedding_service.add_to_faiss_index(chunk_embeddings)

            # Mark as processed
            document.processed = True
            document.processing_error = None
            document.save()

            logger.info(f"Successfully processed document: {document.title}")

        except Exception as e:
            document.processing_error = str(e)
            document.processed = False
            document.save()
            logger.error(f"Error processing document {document.title}: {str(e)}")
            raise


class EmbeddingService:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, 'initialized'):
            return
            
        # Use the best embedding model for improved accuracy and retrieval
        self.model = SentenceTransformer('BAAI/bge-large-en-v1.5')
        self.dimension = 1024
        self.index_path = os.path.join(settings.MEDIA_ROOT, 'faiss_index.bin')
        self.mapping_path = os.path.join(settings.MEDIA_ROOT, 'chunk_mapping.pkl')
        self.initialized = True
        logger.info(f"Initialized EmbeddingService with BAAI/bge-large-en-v1.5 (dim={self.dimension})")

    def create_embedding(self, text):
        """Create embedding for given text with query prefix for BGE model"""
        prefixed_text = f"Represent this sentence for searching relevant passages: {text}"
        return self.model.encode([prefixed_text], convert_to_tensor=False)[0]
    
    def create_embeddings_batch(self, texts):
        """Create embeddings for multiple texts at once (more efficient)"""
        return self.model.encode(texts, convert_to_tensor=False)

    def update_faiss_index(self):
        """Rebuild FAISS index with all chunks"""
        try:
            chunks = DocumentChunk.objects.filter(embedding_vector__isnull=False)

            if not chunks.exists():
                logger.warning("No chunks with embeddings found")
                return

            # Collect all embeddings
            embeddings = []
            chunk_mapping = []

            for chunk in chunks:
                if chunk.embedding_vector:
                    embedding = pickle.loads(chunk.embedding_vector)
                    embeddings.append(embedding)
                    chunk_mapping.append(chunk.id)

            if not embeddings:
                return

            # Create FAISS index
            embeddings_array = np.array(embeddings).astype('float32')
            index = faiss.IndexFlatIP(self.dimension)
            faiss.normalize_L2(embeddings_array)
            index.add(embeddings_array)

            # Save index and mapping
            faiss.write_index(index, self.index_path)
            with open(self.mapping_path, 'wb') as f:
                pickle.dump(chunk_mapping, f)

            # Update metadata
            EmbeddingIndex.objects.filter(is_active=True).update(is_active=False)
            EmbeddingIndex.objects.create(
                index_file=self.index_path,
                dimension=self.dimension,
                total_vectors=len(embeddings),
                is_active=True
            )

            logger.info(f"Updated FAISS index with {len(embeddings)} vectors")

        except Exception as e:
            logger.error(f"Error updating FAISS index: {str(e)}")
            raise
    
    def add_to_faiss_index(self, chunk_embeddings):
        """Add new embeddings to existing FAISS index incrementally"""
        try:
            if not chunk_embeddings:
                return
                
            # Load existing index and mapping
            if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
                index = faiss.read_index(self.index_path)
                with open(self.mapping_path, 'rb') as f:
                    chunk_mapping = pickle.load(f)
            else:
                # Create new index if it doesn't exist
                index = faiss.IndexFlatIP(self.dimension)
                chunk_mapping = []
            
            # Prepare new embeddings
            new_embeddings = []
            new_chunk_ids = []
            
            for chunk_id, embedding in chunk_embeddings:
                new_embeddings.append(embedding)
                new_chunk_ids.append(chunk_id)
            
            if new_embeddings:
                # Convert to numpy array and normalize
                embeddings_array = np.array(new_embeddings).astype('float32')
                faiss.normalize_L2(embeddings_array)
                
                # Add to index
                index.add(embeddings_array)
                
                # Update mapping
                chunk_mapping.extend(new_chunk_ids)
                
                # Save updated index and mapping
                faiss.write_index(index, self.index_path)
                with open(self.mapping_path, 'wb') as f:
                    pickle.dump(chunk_mapping, f)
                
                # Update metadata
                EmbeddingIndex.objects.filter(is_active=True).update(is_active=False)
                EmbeddingIndex.objects.create(
                    index_file=self.index_path,
                    dimension=self.dimension,
                    total_vectors=len(chunk_mapping),
                    is_active=True
                )
                
                logger.info(f"Added {len(new_embeddings)} new embeddings to FAISS index")
                
        except Exception as e:
            logger.error(f"Error adding to FAISS index: {str(e)}")
            # Fallback to full rebuild
            self.update_faiss_index()

    def search_similar_chunks(self, query_text, top_k=30, similarity_threshold=0.4):
        """Search for similar chunks using FAISS with improved accuracy"""
        try:
            if not os.path.exists(self.index_path) or not os.path.exists(self.mapping_path):
                logger.warning("FAISS index not found - no documents have been processed yet")
                return []

            # Load index and mapping
            index = faiss.read_index(self.index_path)
            with open(self.mapping_path, 'rb') as f:
                chunk_mapping = pickle.load(f)

            if not chunk_mapping:
                logger.warning("No chunks in mapping - index may be empty")
                return []

            # Create query embedding
            query_embedding = self.create_embedding(query_text)
            query_vector = np.array([query_embedding]).astype('float32')
            faiss.normalize_L2(query_vector)

            # Search with more results to filter by threshold
            search_k = min(top_k * 3, len(chunk_mapping))
            scores, indices = index.search(query_vector, search_k)

            # Get corresponding chunks with better filtering
            similar_chunks = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(chunk_mapping) and score > similarity_threshold:
                    chunk_id = chunk_mapping[idx]
                    try:
                        chunk = DocumentChunk.objects.get(id=chunk_id)
                        similar_chunks.append({
                            'chunk': chunk,
                            'similarity': float(score)
                        })
                    except DocumentChunk.DoesNotExist:
                        logger.warning(f"Chunk {chunk_id} not found in database")
                        continue
                
                # Stop if we have enough high-quality results
                if len(similar_chunks) >= top_k:
                    break

            # Sort by similarity score (descending)
            similar_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            logger.info(f"Found {len(similar_chunks)} similar chunks for query")
            return similar_chunks[:top_k]

        except Exception as e:
            logger.error(f"Error searching similar chunks: {str(e)}", exc_info=True)
            return []

    def search_similar_chunks_enhanced(self, query_text, top_k=40, similarity_threshold=0.3):
        """Enhanced search with query expansion for comparative queries and better results"""
        try:
            if not os.path.exists(self.index_path) or not os.path.exists(self.mapping_path):
                logger.warning("FAISS index not found - no documents have been processed yet")
                return []

            # Load index and mapping
            index = faiss.read_index(self.index_path)
            with open(self.mapping_path, 'rb') as f:
                chunk_mapping = pickle.load(f)

            if not chunk_mapping:
                logger.warning("No chunks in mapping - index may be empty")
                return []

            # Detect if this is a comparative query (contains "vs", "versus", "compared to", etc.)
            comparative_patterns = ['vs', 'versus', 'compared to', 'difference between', 'vs.', 'compare']
            is_comparative = any(pattern in query_text.lower() for pattern in comparative_patterns)
            
            all_chunks = []
            
            if is_comparative:
                logger.info(f"Detected comparative query: {query_text}")
                
                # Extract the concepts being compared
                query_lower = query_text.lower()
                
                # Split on common comparison patterns
                concepts = []
                for pattern in ['vs', 'versus', 'vs.']:
                    if pattern in query_lower:
                        parts = query_lower.split(pattern)
                        if len(parts) >= 2:
                            concepts = [part.strip() for part in parts[:2]]
                            break
                
                # If no clear split, try "difference between X and Y"
                if not concepts and 'difference between' in query_lower:
                    parts = query_lower.replace('difference between', '').split(' and ')
                    if len(parts) >= 2:
                        concepts = [part.strip() for part in parts[:2]]
                
                # Search for each concept separately and combine results
                if concepts:
                    logger.info(f"Searching for concepts: {concepts}")
                    
                    for concept in concepts:
                        if concept.strip():
                            concept_results = self._search_single_concept(
                                concept.strip(), 
                                index, 
                                chunk_mapping, 
                                top_k//2,  # Split the results between concepts
                                similarity_threshold * 0.8  # Lower threshold for individual concepts
                            )
                            all_chunks.extend(concept_results)
                    
                    # Also search the full query
                    full_query_results = self._search_single_concept(
                        query_text, 
                        index, 
                        chunk_mapping, 
                        top_k//3, 
                        similarity_threshold
                    )
                    all_chunks.extend(full_query_results)
                else:
                    # Fallback to normal search if concept extraction fails
                    all_chunks = self._search_single_concept(
                        query_text, 
                        index, 
                        chunk_mapping, 
                        top_k, 
                        similarity_threshold
                    )
            else:
                # Normal single concept search
                all_chunks = self._search_single_concept(
                    query_text, 
                    index, 
                    chunk_mapping, 
                    top_k, 
                    similarity_threshold
                )
            
            # Remove duplicates and sort by similarity
            seen_chunk_ids = set()
            unique_chunks = []
            for chunk_data in all_chunks:
                chunk_id = chunk_data['chunk'].id
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    unique_chunks.append(chunk_data)
            
            # Sort by similarity score (descending)
            unique_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Return top results
            result_chunks = unique_chunks[:top_k]
            logger.info(f"Enhanced search found {len(result_chunks)} unique chunks for query: {query_text}")
            return result_chunks

        except Exception as e:
            logger.error(f"Error in enhanced search: {str(e)}", exc_info=True)
            # Fallback to regular search
            return self.search_similar_chunks(query_text, top_k, similarity_threshold)
    
    def _search_single_concept(self, concept_text, index, chunk_mapping, top_k, similarity_threshold):
        """Helper method to search for a single concept"""
        try:
            # Create query embedding
            query_embedding = self.create_embedding(concept_text)
            query_vector = np.array([query_embedding]).astype('float32')
            faiss.normalize_L2(query_vector)

            # Search with more results to filter by threshold
            search_k = min(top_k * 3, len(chunk_mapping))
            scores, indices = index.search(query_vector, search_k)

            # Get corresponding chunks with filtering
            similar_chunks = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(chunk_mapping) and score > similarity_threshold:
                    chunk_id = chunk_mapping[idx]
                    try:
                        chunk = DocumentChunk.objects.get(id=chunk_id)
                        similar_chunks.append({
                            'chunk': chunk,
                            'similarity': float(score)
                        })
                    except DocumentChunk.DoesNotExist:
                        logger.warning(f"Chunk {chunk_id} not found in database")
                        continue
                
                # Stop if we have enough results
                if len(similar_chunks) >= top_k:
                    break

            return similar_chunks
            
        except Exception as e:
            logger.error(f"Error searching single concept '{concept_text}': {str(e)}")
            return []


def post_process_response(text: str) -> str:
    """
    Clean up model output to ensure proper formatting before markdown conversion.
    Fixes common formatting issues from LLM responses.
    """
    if not text or not text.strip():
        return text
    
    lines = text.split('\n')
    cleaned_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines for now
        if not line:
            i += 1
            continue
        
        # Check if this is a heading (bold text alone on line)
        is_heading = bool(re.match(r'^\*\*[^*]+\*\*$', line))
        
        # Check if this is a bullet point
        is_bullet = line.startswith('- ') or line.startswith('* ')
        
        if is_heading:
            # Add blank line before heading (if not first line)
            if cleaned_lines and cleaned_lines[-1] != '':
                cleaned_lines.append('')
            
            # Add the heading
            cleaned_lines.append(line)
            
            # Add blank line after heading
            cleaned_lines.append('')
        
        elif is_bullet:
            # Normalize bullet to dash
            if line.startswith('* '):
                line = '- ' + line[2:]
            
            # Check if previous line was not a bullet - add blank line before list
            if cleaned_lines and not cleaned_lines[-1].startswith('- ') and cleaned_lines[-1] != '':
                cleaned_lines.append('')
            
            cleaned_lines.append(line)
            
            # Check if next line is not a bullet - add blank line after list
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('-') and not next_line.startswith('*'):
                    # Check if it's end of list
                    if not re.match(r'^\*\*[^*]+\*\*$', next_line):
                        # Next line is regular text, add spacing after list
                        pass
                    else:
                        # Next line is heading, spacing will be added by heading logic
                        pass
            
            # Add blank line after last bullet if next is not bullet
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('-') and not next_line.startswith('*'):
                    cleaned_lines.append('')
        
        else:
            # Regular paragraph text
            cleaned_lines.append(line)
            
            # Add blank line after paragraph if next line is heading or bullet
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line:
                    next_is_heading = bool(re.match(r'^\*\*[^*]+\*\*$', next_line))
                    next_is_bullet = next_line.startswith('-') or next_line.startswith('*')
                    
                    if next_is_heading or next_is_bullet:
                        cleaned_lines.append('')
        
        i += 1
    
    # Join and clean up excessive blank lines
    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()


class ChatService:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, 'initialized'):
            return

        # Use Groq cloud API for fast inference
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = "llama-3.3-70b-versatile"
        # Test Groq connection
        try:
            response = self.groq_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            logger.info(f"✓ Groq connected. Using {self.model_name}")
            self.groq_available = True
        except Exception as e:
            logger.error(f"Failed to connect to Groq: {e}")
            self.groq_available = False

        self.embedding_service = EmbeddingService()
        self.initialized = True
        logger.info("ChatService initialized with Groq backend")

    def load_model(self):
        """Verify Groq API is reachable"""
        if not self.groq_available:
            raise Exception("Groq API not available. Please check your GROQ_API_KEY.")

        try:
            response = self.groq_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5,
            )
            logger.info(f"✓ {self.model_name} model ready via Groq")
        except Exception as e:
            logger.error(f"Error testing Groq model: {str(e)}")
            raise

    def get_relevant_context(self, query: str, top_k: int = 50) -> str:
        """Retrieve relevant context from documents using RAG"""
        try:
            similar_chunks = self.embedding_service.search_similar_chunks(query, top_k=top_k)
            
            if not similar_chunks:
                logger.info("No relevant chunks found")
                return ""
            
            context_parts = []
            for chunk_data in similar_chunks:
                chunk = chunk_data['chunk']
                # Don't include document labels - just the content
                context_parts.append(chunk.content)
            
            logger.info(f"Found {len(similar_chunks)} relevant chunks for context")
            return "\n\n".join(context_parts)
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return ""

    def _format_context_from_chunks(self, similar_chunks) -> str:
        """Format a context string from provided similar chunks"""
        try:
            if not similar_chunks:
                return ""
            context_parts = []
            for chunk_data in similar_chunks:
                chunk = chunk_data['chunk']
                # Don't include document labels - just the content
                context_parts.append(chunk.content)
            return "\n\n".join(context_parts)
        except Exception as e:
            logger.warning(f"Error formatting context from chunks: {e}")
            return ""
    
    def generate_response(self, messages, similar_chunks=None):
        """Generate response with RAG (Retrieval-Augmented Generation)"""
        try:
            if not self.groq_available:
                self.load_model()

            user_prompt = messages[-1].content

            # Get relevant context from documents
            context = self._format_context_from_chunks(similar_chunks) if similar_chunks else self.get_relevant_context(user_prompt)

            # Require KB context
            if not context:
                return "I could not find information in the knowledge base about that. Please rephrase or upload relevant documents."
            # Concise system prompt for faster responses
            system_prompt = """You are a helpful assistant that answers questions based on provided context documents. Follow these rules:

1. Answer ONLY using the provided context. If the answer isn't in the context, say "I could not find that information in the knowledge base."
2. Be practical and concrete with actionable examples.
3. Use suggestive language ("You could...", "Consider...") not mandates ("You must...").
4. Format responses in clean HTML: use <p> for paragraphs, <ul><li> for lists, <strong> for emphasis.
5. Do NOT use markdown formatting (no *, **, -, #). HTML only.
6. Do NOT mention "the document says" or "according to the context".
7. Keep responses focused and concise."""
            user_message = f"""CONTEXT (the ONLY information you can use):

{context}

USER QUESTION: {user_prompt}

Provide a clear, well-structured HTML answer using ONLY the CONTEXT above. If the answer is not in the CONTEXT, respond exactly: "I could not find that information in the knowledge base."

Do NOT mention "Document", "Content", or any source references. Write naturally as if stating facts."""

            # Generate response using Groq
            response = self.groq_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message}
                ],
                temperature=0.3,
                top_p=0.9,
                max_tokens=512,
            )

            generated_text = response.choices[0].message.content.strip()
            
            # Skip post-processing since we're now using HTML format
            # generated_text = post_process_response(generated_text)
            
            if not generated_text:
                return "I'm here to help! How can I assist you today?"
            
            # Validate response before returning
            is_valid, warnings = validate_chatbot_response(generated_text, user_prompt)
            if warnings:
                logger.warning(f"Response validation warnings for question '{user_prompt[:100]}...': {warnings}")
                
            return generated_text

        except Exception as e:
            logger.error(f"Error generating response with Ollama: {str(e)}")
            return "I'm sorry, there was an error processing your request."
    
    def generate_response_stream(self, messages, similar_chunks=None) -> Generator[str, None, None]:
        """Generate streaming response with RAG using Groq backend"""
        try:
            if not self.groq_available:
                self.load_model()
            
            user_prompt = messages[-1].content
            
            # Get relevant context from documents
            context = self._format_context_from_chunks(similar_chunks) if similar_chunks else self.get_relevant_context(user_prompt)
            
            # Require KB context
            if not context:
                yield "I could not find information in the knowledge base about that. Please rephrase or upload relevant documents."
                return
             
            # System prompt for clean HTML responses with better formatting
            FEW_SHOT_EXAMPLES = """
<h3>ADDITIONAL EXAMPLES OF CORRECT RESPONSES</h3>

<h4>Question:</h4>
<p>What training programs are available for staff learning this framework?</p>
<h4>Answer:</h4>
<p>The framework doesn't specify particular training programs that are currently available. It mentions that the Community Engagement Workgroup made recommendations for "a process to train staff in the use of the framework and indicators," but doesn't detail what training was ultimately implemented.</p>
<p>For information about current training opportunities, you could contact NYC DOHMH directly or check their staff development resources.</p>

<h4>Question:</h4>
<p>Who is the current Commissioner of Health in NYC?</p>
<h4>Answer:</h4>
<p>According to the framework document published in May 2017, Dr. Mary T. Bassett was the Commissioner of Health at that time. However, I cannot confirm who the current Commissioner is, as that information would be outside the framework. You can find current leadership information at <a href="https://www.nyc.gov/health">nyc.gov/health</a>.</p>

<h4>Question:</h4>
<p>How does community engagement relate to social determinants of health?</p>
<h4>Answer:</h4>
<p>The framework doesn't use the term "social determinants of health" specifically, but it emphasizes that advancing health equity requires identifying "the underlying social and systemic injustices that drive health inequities" and designing strategies to change these systems.</p>
<p>It states that optimal health for all is not yet a reality because "some are unfairly disadvantaged by social conditions and systems, while others are unfairly advantaged." This aligns with addressing social determinants, though the framework focuses on community engagement as a strategy to address these systemic issues.</p>

<h4>Question:</h4>
<p>What are best practices for community engagement during COVID-19?</p>
<h4>Answer:</h4>
<p>The framework doesn't provide information about COVID-19.</p>
"""

          
            # System prompt for clean, structured answers
            system_prompt = """
<system_instructions>
You are a helpful assistant that answers questions about the NYC Department of Health and Mental Hygiene's Community Engagement Framework document (published May 2017). Follow the instructions below strictly.

<h3>RESPONSE APPROACH</h3>

<h4>1. BE PRACTICAL AND CONCRETE</h4>
<ul>
  <li>This framework is designed to guide real public health work</li>
  <li>Provide specific, actionable examples of how to apply framework principles</li>
  <li>Show what abstract concepts look like in practice</li>
  <li>Help users understand how to actually use the framework</li>
</ul>

<h4>2. GROUND EVERYTHING IN THE FRAMEWORK</h4>
<ul>
  <li>Every suggestion should trace back to principles, methods, or guidance in the document</li>
  <li>When framework says "go to the community" → Show concrete examples (community centers, faith spaces, schools)</li>
  <li>When framework says "partner with faith-based organizations" → That's explicitly mentioned, use it</li>
  <li>When framework describes "outreach" → Explain what an outreach campaign includes</li>
  <li>When framework discusses "infectious disease outbreaks" → Apply to COVID, flu, measles, etc.</li>
</ul>

<h4>3. THOUGHTFUL APPLICATION IS ENCOURAGED</h4>
<p><strong>Appropriate applications include:</strong></p>
<ul>
  <li>Framework describes "outreach for infectious disease outbreak" → Apply to COVID vaccination</li>
  <li>Framework says "linguistically appropriate materials" → Suggest multilingual resources</li>
  <li>Framework mentions "partner with faith-based organizations" → Suggest churches, mosques, temples</li>
  <li>Framework describes "shared leadership" → Explain what that looks like in specific contexts</li>
  <li>Framework lists "focus groups, surveys, listening sessions" → Describe how to use these</li>
</ul>

<h4>4. DON'T INVENT REQUIREMENTS OR MANDATES</h4>
<p><strong>Do NOT do the following:</strong></p>
<ul>
  <li>Don't specify required budget percentages not in framework ("must allocate 20%")</li>
  <li>Don't create mandatory timelines not specified ("requires 6 months minimum")</li>
  <li>Don't invent approval processes not mentioned ("needs Deputy Commissioner sign-off")</li>
  <li>Don't fabricate specific statistics or research findings</li>
  <li>Don't claim "the Health Department requires..." anything not explicitly stated</li>
</ul>

<h4>5. ACKNOWLEDGE TRUE LIMITATIONS</h4>
<p><strong>For questions about information truly not in framework:</strong></p>
<ul>
  <li>Current events after 2017 (current Commissioner, what happened after publication)</li>
  <li>Specific budgets, programs, or initiatives not mentioned</li>
  <li>Organizational policies or procedures not detailed</li>
</ul>
<p><strong>Response format:</strong></p>
<ul>
  <li>Lead with: "The framework doesn't provide information about [X]..."</li>
  <li>Then redirect to what the framework DOES offer that's relevant</li>
</ul>

<h4>6. USE APPROPRIATE LANGUAGE</h4>
<p><strong>Recommended phrasing:</strong></p>
<ul>
  <li>"You could..." / "You might..." / "Consider..." / "Approaches include..."</li>
  <li>"The framework recommends..." / "The framework emphasizes..."</li>
  <li>"This principle suggests..." / "Based on the framework's guidance..."</li>
</ul>
<p><strong>Avoid unless explicitly stated in framework:</strong></p>
<ul>
  <li>"You must..." / "It's required..." / "Policy mandates..."</li>
</ul>

<h3>THE KEY DISTINCTION</h3>
<ul>
  <li><strong>Good (applying framework with concrete examples):</strong> "Partner with churches to host vaccine events" — This applies framework guidance with concrete example</li>
  <li><strong>Bad (inventing requirements):</strong> "You must establish 3 advisory boards before proceeding" — Inventing specific requirement</li>
</ul>

<h3>HTML FORMATTING RULES — STRICTLY ENFORCED</h3>

<h4>Critical Formatting Requirements</h4>
<ul>
  <li>Use <code>&lt;h3&gt;</code> for section headings</li>
  <li>Use <code>&lt;p&gt;</code> for all narrative content and paragraphs</li>
  <li><strong>NEVER use asterisks (*), bullets (-), or markdown formatting</strong></li>
  <li><strong>NEVER use double asterisks (**) for bold</strong> — Use <code>&lt;strong&gt;</code> tags instead</li>
  <li>No markdown, no plain text — valid, well-formed HTML only</li>
  <li>ALWAYS ensure every opening tag has a matching closing tag</li>
  <li>Do NOT include phrases like "The document says" or "According to the framework"</li>
  <li>Do NOT repeat or rephrase the user's question</li>
  <li>Do NOT use Q&A formatting unless it appears in the framework</li>
</ul>

<h4>List Formatting — Use ONLY These Formats</h4>
<p><strong>For lists of items with descriptions, use ONLY one of these two formats:</strong></p>

<p><strong>Format 1 (Bullet List with Strong Tags):</strong></p>
<pre><code>&lt;ul&gt;
  &lt;li&gt;&lt;strong&gt;Item Name:&lt;/strong&gt; Description text here.&lt;/li&gt;
  &lt;li&gt;&lt;strong&gt;Another Item:&lt;/strong&gt; More description text.&lt;/li&gt;
&lt;/ul&gt;</code></pre>

<p><strong>Format 2 (Paragraph Format with Strong Tags):</strong></p>
<pre><code>&lt;p&gt;&lt;strong&gt;Item Name:&lt;/strong&gt; Description text here.&lt;/p&gt;
&lt;p&gt;&lt;strong&gt;Another Item:&lt;/strong&gt; More description text.&lt;/p&gt;</code></pre>

<h4>WRONG Formats — NEVER Use These</h4>
<ul>
  <li><strong>WRONG:</strong> <code>* &lt;strong&gt;Term:&lt;/strong&gt; Description</code> (asterisk before HTML tag)</li>
  <li><strong>WRONG:</strong> <code>** Term:** Description</code> (markdown-style asterisks)</li>
  <li><strong>WRONG:</strong> <code>&lt;p&gt;Term&lt;/p&gt;: Description</code> (closing tag followed by colon)</li>
  <li><strong>WRONG:</strong> <code>- &lt;p&gt;Term&lt;/p&gt;:</code> (mixing bullets with HTML tags)</li>
  <li><strong>WRONG:</strong> <code>* Term:** Description</code> (mixing asterisks with colons)</li>
  <li><strong>WRONG:</strong> Any combination of markdown and HTML</li>
</ul>

<h4>Examples of Correct vs Incorrect Formatting</h4>

<p><strong>✅ CORRECT — Bullet List Format:</strong></p>
<pre><code>&lt;ul&gt;
  &lt;li&gt;&lt;strong&gt;Outreach:&lt;/strong&gt; Conduct vigorous outreach campaigns to inform communities most likely to be affected.&lt;/li&gt;
  &lt;li&gt;&lt;strong&gt;Transparency:&lt;/strong&gt; Use widely available platforms to disseminate information and be consistent in communication.&lt;/li&gt;
&lt;/ul&gt;</code></pre>

<p><strong>✅ CORRECT — Paragraph Format:</strong></p>
<pre><code>&lt;p&gt;&lt;strong&gt;Outreach:&lt;/strong&gt; Conduct vigorous outreach campaigns to inform communities most likely to be affected.&lt;/p&gt;
&lt;p&gt;&lt;strong&gt;Transparency:&lt;/strong&gt; Use widely available platforms to disseminate information and be consistent in communication.&lt;/p&gt;</code></pre>

<p><strong>❌ WRONG — Markdown Mixed with HTML:</strong></p>
<pre><code>* &lt;strong&gt;Outreach:&lt;/strong&gt; Conduct vigorous outreach campaigns...
** Transparency:** Use widely available platforms...</code></pre>

<p><strong>❌ WRONG — Malformed HTML:</strong></p>
<pre><code>&lt;p&gt;Outreach&lt;/p&gt;: Conduct vigorous outreach campaigns...
- &lt;p&gt;Transparency&lt;/p&gt;: Use widely available platforms...</code></pre>

<h3>EXAMPLES OF PROPERLY FORMATTED RESPONSES</h3>

<h4>Example 1: COVID Vaccination Engagement</h4>
<p><strong>Question:</strong> "How do we engage communities for COVID vaccination?"</p>

<p>The framework provides guidance for infectious disease outbreaks that applies directly to COVID vaccination. It recommends using outreach for rapid information dissemination. Here's how to apply it:</p>

<p><strong>Go to the community:</strong> Set up vaccination sites in neighborhoods, community centers, faith spaces rather than only central locations. The framework emphasizes going to where people are rather than expecting them to come to you.</p>

<p><strong>Use trusted messengers:</strong> Partner with community health workers, faith leaders, and local organizations. The framework explicitly mentions partnering with faith-based organizations and community-based organizations.</p>

<p><strong>Ensure accessibility:</strong> Create multilingual materials and use interpretation services. The framework emphasizes linguistically appropriate communication.</p>

<p><strong>Build on existing networks:</strong> Leverage relationships with schools, churches, community groups. The framework recommends building diverse partnerships across sectors.</p>

<p><strong>Include community voice:</strong> Use focus groups and listening sessions to understand vaccine concerns and barriers. The framework describes these as consultation methods.</p>

<p>The core principles of transparency, equity, and prioritizing communities most affected by health inequities should guide your vaccination efforts.</p>

<h4>Example 2: Shared Leadership in Housing Advocacy</h4>
<p><strong>Question:</strong> "What would shared leadership look like for housing advocacy?"</p>

<p>Based on the framework's description of shared leadership, here's what it would include in a housing advocacy context:</p>

<p><strong>Equal representation:</strong> Residents experiencing housing issues have equal voice in decision-making alongside agencies and organizations. The framework describes stakeholders being "represented equally in the partnership."</p>

<p><strong>Consensus-driven:</strong> Strategic decisions are made jointly, not by the agency alone. This means community members help define what the housing problem is and what solutions to pursue.</p>

<p><strong>Shared accountability:</strong> All parties—residents, community organizations, government agencies—take responsibility for outcomes together.</p>

<p><strong>Flexible leadership:</strong> The health department or lead agency may support initiatives that residents or community organizations lead, rather than always being in charge.</p>

<p><strong>Resource sharing:</strong> Ensure community members have the knowledge, resources, and support needed to participate fully in leadership roles.</p>

<p>The framework notes this approach takes significant time and resources, requires flexibility about how problems are identified, and works best for broad issues where people with varying backgrounds can meaningfully participate.</p>

<h4>Example 3: Out of Scope Question</h4>
<p><strong>Question:</strong> "Who is the current NYC Health Commissioner?"</p>

<p>The framework document was published in May 2017 under Commissioner Dr. Mary T. Bassett's leadership. I cannot confirm who the current Commissioner is as that information would be outside this document. You can find current leadership information at nyc.gov/health.</p>

<h4>Example 4: Best Practices for Community Engagement</h4>
<p><strong>Question:</strong> "What are best practices for community engagement during COVID-19?"</p>

<p>The framework emphasizes the importance of community engagement, particularly during public health crises like the COVID-19 pandemic.</p>

<p><strong>Outreach:</strong> Conduct vigorous outreach campaigns to inform communities most likely to be affected by the outbreak and medical providers who serve those communities. This unidirectional flow of information aims to establish communication channels for outreach and community involvement.</p>

<p><strong>Bidirectional Communication:</strong> In situations like consultations, engage in bidirectional communication with specific communities or stakeholders. This approach fosters a two-way exchange of information, ideas, and feedback.</p>

<p>When engaging communities during the pandemic, it is essential to:</p>

<ul>
  <li><strong>Be Clear:</strong> Define the purpose, goals, and desired outcomes of community engagement efforts.</li>
  <li><strong>Identify Stakeholders:</strong> Determine who is most affected by the crisis and involve them in decision-making processes. This includes individuals or groups responsible for addressing the issue, as well as institutions with the power to make decisions.</li>
</ul>

<p>The framework also highlights the importance of:</p>

<ul>
  <li><strong>Transparency:</strong> Use widely available platforms to disseminate information and be consistent in communication. Ensure linguistically-appropriate language and honesty about intentions and outcomes.</li>
  <li><strong>Inclusivity:</strong> Engage a diverse spectrum of community stakeholders and partners, including City agencies, community-based organizations, faith-based organizations, private sector businesses, and academic institutions.</li>
  <li><strong>Go to the community:</strong> Build relationships with community leaders and work together to lay the groundwork for future collaborations.</li>
  <li><strong>Be flexible:</strong> Be open to reassessing processes throughout, recognizing that no external entity can bestow power on a group to act. Honor self-determination in all communities.</li>
</ul>

<p>The framework also emphasizes shared leadership during emergency situations, which involves strong relationships built on trust, reciprocity, and consensus-driven decision-making among community stakeholders and health department staff.</p>

<p>By following these best practices for community engagement during the COVID-19 pandemic, you can foster trust, build relationships, and promote effective communication with communities affected by the crisis.</p>

<h3>PRE-RESPONSE CHECKLIST</h3>
<p><strong>Before sending ANY response, verify:</strong></p>
<ul>
  <li>✅ No asterisks (*) or double asterisks (**) anywhere in the response</li>
  <li>✅ No markdown-style bullets (-) or numbered lists (1., 2., 3.)</li>
  <li>✅ No Colon (:)</li>
  <li>✅ All bold text uses <code>&lt;strong&gt;</code> tags, not **text**</li>
  <li>✅ All lists use proper <code>&lt;ul&gt;&lt;li&gt;</code> or <code>&lt;p&gt;</code> tags</li>
  <li>✅ No orphaned colons after closing tags (e.g., <code>&lt;/p&gt;:</code>)</li>
  <li>✅ All opening tags have matching closing tags</li>
  <li>✅ Content is grounded in the framework with practical application</li>
  <li>✅ No invented requirements, mandates, or statistics</li>
  <li>✅ No phrases like "The document says" or "According to the framework"</li>
  <li>✅ No Q&A formatting unless in the framework</li>
</ul>

<h3>SUMMARY</h3>
<p>Remember: Be helpful, concrete, and practical. Show users how to USE the framework, not just describe it abstractly. But don't invent requirements, mandates, or specific organizational policies not in the document. Always format responses in proper, well-formed HTML with absolutely NO markdown or asterisks.</p>
</system_instructions>
"""
            system_prompt=system_prompt + "\n\n" + FEW_SHOT_EXAMPLES


            user_message = f"""CONTEXT (the ONLY information you can use):

{context}

USER QUESTION: {user_prompt}

Provide a clear, well-structured HTML answer using ONLY the CONTEXT above. If the answer is not in the CONTEXT, respond exactly: "I could not find that information in the knowledge base."

Do NOT mention "Document", "Content", or any source references. Write naturally as if stating facts."""

            # Stream response using Groq - yield tokens in REAL-TIME
            response_stream = self.groq_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message}
                ],
                stream=True,
                temperature=0.3,
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.2,
                max_tokens=768,
            )

            # Stream tokens in real-time
            for chunk in response_stream:
                token = chunk.choices[0].delta.content
                if token:
                    yield token

        except Exception as e:
            logger.error(f"Error generating streaming response with Groq: {str(e)}", exc_info=True)
            yield "I'm sorry, there was an error processing your request."