from django.core.management.base import BaseCommand
from chat.models import PDFDocument
from chat.services import PDFProcessingService
import logging
from django.db import models

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Process all PDF documents that haven't been processed yet.
    Useful for batch processing or fixing failed documents.
    """

    help = 'Process all pending PDF documents and create embeddings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--retry-errors',
            action='store_true',
            help='Also retry documents that had processing errors',
        )

        parser.add_argument(
            '--document-id',
            type=str,
            help='Process only a specific document by ID',
        )

    def handle(self, *args, **options):
        retry_errors = options['retry_errors']
        specific_doc_id = options['document_id']

        # Build the query
        if specific_doc_id:
            # Process specific document
            try:
                documents = PDFDocument.objects.filter(id=specific_doc_id)
                if not documents.exists():
                    self.stdout.write(
                        self.style.ERROR(f'Document with ID {specific_doc_id} not found')
                    )
                    return
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid document ID format')
                )
                return
        else:
            # Process pending documents
            documents = PDFDocument.objects.filter(processed=False)

            if retry_errors:
                # Also include documents that had errors
                documents = PDFDocument.objects.filter(
                    models.Q(processed=False) | models.Q(processing_error__isnull=False)
                )

        if not documents.exists():
            self.stdout.write('No pending documents to process.')
            return

        self.stdout.write(f'Found {documents.count()} documents to process...')

        pdf_service = PDFProcessingService()
        processed_count = 0
        error_count = 0

        for document in documents:
            try:
                self.stdout.write(f'📄 Processing: {document.title}')

                # Clear any existing error
                document.processing_error = None
                document.save()

                # Process the document
                pdf_service.process_document(document)

                processed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Processed: {document.title}')
                )

            except Exception as e:
                error_count += 1
                error_msg = str(e)
                logger.error(f'Error processing {document.title}: {error_msg}')

                self.stdout.write(
                    self.style.ERROR(f'❌ Error processing {document.title}: {error_msg}')
                )

                # Save the error to the database
                document.processing_error = error_msg
                document.processed = False
                document.save()

        # Final summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(f'📊 Processing Summary:')
        self.stdout.write(f'   ✅ Successfully processed: {processed_count}')
        self.stdout.write(f'   ❌ Errors: {error_count}')

        if processed_count > 0:
            self.stdout.write('\n🔄 Rebuilding FAISS index...')
            try:
                from chat.services import EmbeddingService
                embedding_service = EmbeddingService()
                embedding_service.update_faiss_index()
                self.stdout.write(
                    self.style.SUCCESS('✅ FAISS index updated successfully!')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Index update failed: {str(e)}')
                )
