import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from ckeditor.fields import RichTextField

User = get_user_model()


class PDFDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(PDFDocument, related_name='chunks', on_delete=models.CASCADE)
    content = models.TextField()
    chunk_index = models.IntegerField()
    page_number = models.IntegerField(null=True, blank=True)
    embedding_vector = models.BinaryField(null=True, blank=True)  # Store serialized embedding

    class Meta:
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_name = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def update_title_from_message(self, message_content):
        """Update the chat title based on the first message"""
        # Truncate the message if it's too long and add ellipsis
        max_length = 50
        title = message_content[:max_length]
        if len(message_content) > max_length:
            title = title.rsplit(' ', 1)[0] + '...'

        self.session_name = title
        self.save()
        return self.session_name

    def __str__(self):
        return self.session_name


class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    sources = models.ManyToManyField(DocumentChunk, blank=True)  # Track which chunks were used

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."

    @property
    def is_user(self):
        """Return True if message is from user"""
        return self.message_type == 'user'

    @property
    def is_assistant(self):
        """Return True if message is from assistant"""
        return self.message_type == 'assistant'

    @property
    def is_system(self):
        """Return True if message is system message"""
        return self.message_type == 'system'


class ChatMessageSource(models.Model):
    """Stores per-message source metadata (best practice for persistence).

    We purposely keep the existing ManyToMany `ChatMessage.sources` for backward
    compatibility in templates and exports, while this model records similarity,
    confidence label, and an optional URL for viewing the source.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(ChatMessage, related_name='source_links', on_delete=models.CASCADE)
    chunk = models.ForeignKey(DocumentChunk, related_name='message_links', on_delete=models.CASCADE)
    similarity = models.FloatField(default=0.0)
    confidence = models.CharField(max_length=20, blank=True, null=True)
    url = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-similarity']
        indexes = [
            models.Index(fields=['message']),
            models.Index(fields=['chunk']),
        ]

    def __str__(self):
        return f"Source for {self.message_id} -> {self.chunk_id} ({self.similarity:.3f})"


@receiver(post_save, sender=ChatMessage)
def update_session_title(sender, instance, created, **kwargs):
    """Update chat session title based on the first user message"""
    if created and instance.message_type == 'user':
        # Count messages in the session
        message_count = ChatMessage.objects.filter(session=instance.session).count()

        # If this is the first message in the session
        if message_count == 1:
            # Create a title from the message content
            title = instance.content[:50].strip()
            if len(instance.content) > 50:
                title += "..."

            # Update the session name
            instance.session.session_name = title
            instance.session.save()


class EmbeddingIndex(models.Model):
    """Stores metadata about the FAISS index"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    index_file = models.CharField(max_length=255)  # Path to FAISS index file
    dimension = models.IntegerField(default=768)
    total_vectors = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']


class Feedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback from {self.name} <{self.email}>"


class SurveyResponse(models.Model):
    """Community Engagement Compass Feedback Survey response."""
    EASE_CHOICES = [
        ("easy", "Easy"),
        ("neutral", "Neutral"),
        ("difficult", "Difficult"),
    ]

    RELEVANCE_CHOICES = [
        ("relevant", "Relevant"),
        ("neutral", "Neutral"),
        ("not_relevant", "Not relevant"),
    ]

    TRUST_CHOICES = [
        ("confident", "Confident"),
        ("neutral", "Neutral"),
        ("not_confident", "Not confident"),
    ]

    CITATIONS_CHOICES = [
        ("helpful", "Helpful"),
        ("neutral", "Neutral"),
        ("not_helpful", "Not helpful"),
    ]

    LIKELIHOOD_CHOICES = [
        ("likely", "Likely"),
        ("neutral", "Neutral"),
        ("unlikely", "Unlikely"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ease_of_use = models.CharField(max_length=16, choices=EASE_CHOICES)
    relevance = models.CharField(max_length=16, choices=RELEVANCE_CHOICES)
    trust = models.CharField(max_length=16, choices=TRUST_CHOICES)
    citations_helpfulness = models.CharField(max_length=16, choices=CITATIONS_CHOICES)
    likelihood_of_use = models.CharField(max_length=16, choices=LIKELIHOOD_CHOICES)
    additional_sources = models.TextField(blank=True, null=True)
    open_feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"SurveyResponse {self.id} ({self.created_at:%Y-%m-%d %H:%M})"


class AboutContent(models.Model):
    """Stores the About page content that can be edited from admin."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, default="About Community Engagement Compass")
    content = RichTextField(help_text="Rich text content for the About page")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

    @classmethod
    def get_active_content(cls):
        """Get the active About content, or create a default one if none exists."""
        try:
            return cls.objects.filter(is_active=True).first()
        except cls.DoesNotExist:
            return None


class HowItWorksContent(models.Model):
    """Stores the How It Works content that can be edited from admin."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, default="How It Works")
    content = RichTextField(help_text="Rich text content for the How It Works page")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

    @classmethod
    def get_active_content(cls):
        """Get the active How It Works content, or create a default one if none exists."""
        try:
            return cls.objects.filter(is_active=True).first()
        except cls.DoesNotExist:
            return None
