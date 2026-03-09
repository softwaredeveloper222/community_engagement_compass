from datetime import timedelta

from django.contrib.auth import get_user_model
# from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from chat.models import PDFDocument, DocumentChunk, ChatSession, ChatMessage

User = get_user_model()


class Command(BaseCommand):
    """
    Display statistics about the chatbot system.
    """

    help = 'Show chatbot system statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed statistics',
        )

    def handle(self, *args, **options):
        detailed = options['detailed']

        self.stdout.write(self.style.SUCCESS('🤖 Chatbot System Statistics'))
        self.stdout.write('=' * 50)

        # Document Statistics
        total_docs = PDFDocument.objects.count()
        processed_docs = PDFDocument.objects.filter(processed=True).count()
        failed_docs = PDFDocument.objects.filter(
            processed=False,
            processing_error__isnull=False
        ).count()
        pending_docs = PDFDocument.objects.filter(
            processed=False,
            processing_error__isnull=True
        ).count()

        self.stdout.write('\n📄 Document Statistics:')
        self.stdout.write(f'   Total documents: {total_docs}')
        self.stdout.write(f'   ✅ Processed: {processed_docs}')
        self.stdout.write(f'   ⏳ Pending: {pending_docs}')
        self.stdout.write(f'   ❌ Failed: {failed_docs}')

        # Chunk Statistics
        total_chunks = DocumentChunk.objects.count()
        chunks_with_embeddings = DocumentChunk.objects.filter(
            embedding_vector__isnull=False
        ).count()

        self.stdout.write('\n🧩 Chunk Statistics:')
        self.stdout.write(f'   Total chunks: {total_chunks}')
        self.stdout.write(f'   With embeddings: {chunks_with_embeddings}')

        if total_chunks > 0:
            avg_chunks_per_doc = total_chunks / processed_docs if processed_docs > 0 else 0
            self.stdout.write(f'   Average chunks per document: {avg_chunks_per_doc:.1f}')

        # Chat Statistics
        total_sessions = ChatSession.objects.count()
        total_messages = ChatMessage.objects.count()
        user_messages = ChatMessage.objects.filter(message_type='user').count()
        assistant_messages = ChatMessage.objects.filter(message_type='assistant').count()

        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_sessions = ChatSession.objects.filter(created_at__gte=week_ago).count()
        recent_messages = ChatMessage.objects.filter(timestamp__gte=week_ago).count()

        self.stdout.write('\n💬 Chat Statistics:')
        self.stdout.write(f'   Total chat sessions: {total_sessions}')
        self.stdout.write(f'   Total messages: {total_messages}')
        self.stdout.write(f'   👤 User messages: {user_messages}')
        self.stdout.write(f'   🤖 Assistant messages: {assistant_messages}')
        self.stdout.write(f'   📅 Sessions this week: {recent_sessions}')
        self.stdout.write(f'   💬 Messages this week: {recent_messages}')

        if total_sessions > 0:
            avg_messages_per_session = total_messages / total_sessions
            self.stdout.write(f'   Average messages per session: {avg_messages_per_session:.1f}')

        # User Statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(
            chatsession__created_at__gte=week_ago
        ).distinct().count()

        self.stdout.write('\n👥 User Statistics:')
        self.stdout.write(f'   Total users: {total_users}')
        self.stdout.write(f'   Active users (this week): {active_users}')

        # Detailed statistics
        if detailed:
            self.stdout.write('\n📊 Detailed Statistics:')

            # Top active users
            top_users = User.objects.annotate(
                session_count=Count('chatsession')
            ).filter(session_count__gt=0).order_by('-session_count')[:5]

            if top_users:
                self.stdout.write('\n   Most active users:')
                for user in top_users:
                    display_name = user.name or user.email
                    self.stdout.write(f'     {display_name}: {user.session_count} sessions')

            # Largest documents
            large_docs = PDFDocument.objects.annotate(
                chunk_count=Count('chunks')
            ).filter(chunk_count__gt=0).order_by('-chunk_count')[:5]

            if large_docs:
                self.stdout.write('\n   Largest documents (by chunks):')
                for doc in large_docs:
                    self.stdout.write(f'     {doc.title}: {doc.chunk_count} chunks')

            # Recent errors
            error_docs = PDFDocument.objects.filter(
                processing_error__isnull=False
            ).order_by('-uploaded_at')[:3]

            if error_docs:
                self.stdout.write('\n   ⚠️ Recent processing errors:')
                for doc in error_docs:
                    error_preview = doc.processing_error[:60] + '...' if len(
                        doc.processing_error) > 60 else doc.processing_error
                    self.stdout.write(f'     {doc.title}: {error_preview}')
