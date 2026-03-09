# chat/apps.py
from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)

class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        """Initialize services when Django starts - ONLY ONCE"""
        # Prevent double initialization in development server
        if os.environ.get('RUN_MAIN') != 'true':
            return
            
        try:
            logger.info("Initializing ChatService and EmbeddingService...")
            
            # Set CUDA memory environment variables BEFORE importing services
            os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,max_split_size_mb:512'
            
            # Import here to avoid circular imports
            from .services import ChatService, EmbeddingService
            
            # Initialize services (singleton pattern ensures only one instance)
            chat_service = ChatService()
            embedding_service = EmbeddingService()
            
            logger.info("AI models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error initializing services: {str(e)}")
            # Don't raise - let Django continue starting
