from django.core.management.base import BaseCommand
from chat.services import EmbeddingService
from chat.models import DocumentChunk, EmbeddingIndex
import logging
import sys

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django Management Command to rebuild the FAISS index.

    This command can be run from the terminal using:
    python manage.py rebuild_index
    """

    # Help text that appears when you run: python manage.py help rebuild_index
    help = 'Rebuild FAISS index from existing embeddings in the database'

    def add_arguments(self, parser):
        """
        Add command-line arguments to the command.
        This allows you to pass options like: python manage.py rebuild_index --force
        """
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild even if index exists and is recent',
        )

        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output during rebuild',
        )

    def handle(self, *args, **options):
        """
        Main method that gets executed when the command runs.
        *args and **options contain command-line arguments.
        """

        # Get command-line options
        force_rebuild = options['force']
        verbose = options['verbose']

        # Django provides self.stdout for colored output
        self.stdout.write('Starting FAISS index rebuild...')

        try:
            # Check if we have chunks with embeddings
            chunks_with_embeddings = DocumentChunk.objects.filter(
                embedding_vector__isnull=False
            )

            if not chunks_with_embeddings.exists():
                self.stdout.write(
                    self.style.WARNING('No document chunks with embeddings found!')
                )
                self.stdout.write('Please process some PDF documents first.')
                return

            # Check if we should skip rebuild
            if not force_rebuild:
                recent_index = EmbeddingIndex.objects.filter(
                    is_active=True
                ).first()

                if recent_index and recent_index.total_vectors == chunks_with_embeddings.count():
                    self.stdout.write(
                        self.style.SUCCESS('Index is already up to date. Use --force to rebuild anyway.')
                    )
                    return

            if verbose:
                self.stdout.write(f'Found {chunks_with_embeddings.count()} chunks with embeddings')

            # Initialize the embedding service
            embedding_service = EmbeddingService()

            # Show progress
            self.stdout.write('Rebuilding FAISS index...')

            # This is the main work - rebuild the index
            embedding_service.update_faiss_index()

            # Success message with green coloring
            self.stdout.write(
                self.style.SUCCESS('✅ Successfully rebuilt FAISS index!')
            )

            # Show stats
            new_index = EmbeddingIndex.objects.filter(is_active=True).first()
            if new_index:
                self.stdout.write(f'📊 Index contains {new_index.total_vectors} vectors')
                self.stdout.write(f'📏 Dimension: {new_index.dimension}')

        except Exception as e:
            # Error handling with red coloring
            logger.error(f"Error rebuilding FAISS index: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'❌ Error rebuilding index: {str(e)}')
            )
            # Exit with error code
            sys.exit(1)
