from django.core.management.base import BaseCommand
from chat.services import EmbeddingService
from chat.models import DocumentChunk
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Rebuild FAISS index with optimized settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild even if index exists',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting FAISS index rebuild...')
        
        try:
            # Check if chunks exist
            chunk_count = DocumentChunk.objects.filter(embedding_vector__isnull=False).count()
            if chunk_count == 0:
                self.stdout.write(
                    self.style.WARNING('No chunks with embeddings found. Please process some documents first.')
                )
                return

            self.stdout.write(f'Found {chunk_count} chunks with embeddings')
            
            # Initialize embedding service
            embedding_service = EmbeddingService()
            
            # Rebuild index
            embedding_service.update_faiss_index()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully rebuilt FAISS index with {chunk_count} vectors')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error rebuilding FAISS index: {str(e)}')
            )
            logger.error(f'Error rebuilding FAISS index: {str(e)}')
            raise
