
from django.contrib import admin
from django.db import models
from .models import PDFDocument, DocumentChunk, ChatSession, ChatMessage, EmbeddingIndex, Feedback, SurveyResponse, AboutContent, HowItWorksContent
from ckeditor.widgets import CKEditorWidget


@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'uploaded_by', 'uploaded_at', 'processed', 'chunk_count']
    list_filter = ['processed', 'uploaded_at', 'uploaded_by']
    search_fields = ['title', 'file']
    readonly_fields = ['uploaded_at', 'processing_error']

    def chunk_count(self, obj):
        return obj.chunks.count()

    chunk_count.short_description = 'Chunks'


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'chunk_index', 'page_number', 'content_preview']
    list_filter = ['document', 'page_number']
    search_fields = ['content', 'document__title']
    readonly_fields = ['embedding_vector']

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content

    content_preview.short_description = 'Content Preview'


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_name', 'user', 'created_at', 'message_count']
    list_filter = ['created_at', 'user']
    search_fields = ['session_name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = 'Messages'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'message_type', 'timestamp', 'content_preview']
    list_filter = ['message_type', 'timestamp', 'session']
    search_fields = ['content', 'session__session_name']
    readonly_fields = ['timestamp']

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content

    content_preview.short_description = 'Content Preview'


@admin.register(EmbeddingIndex)
class EmbeddingIndexAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'dimension', 'total_vectors', 'is_active']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "user", "created_at")
    search_fields = ("name", "email", "message")
    list_filter = ("created_at",)


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ("user", "ease_of_use", "relevance", "trust", "created_at")
    list_filter = ("ease_of_use", "relevance", "trust", "citations_helpfulness", "likelihood_of_use", "created_at")
    search_fields = ("user__email", "user__name", "additional_sources", "open_feedback")
    readonly_fields = ("created_at",)


@admin.register(AboutContent)
class AboutContentAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    list_filter = ("is_active", "created_at", "updated_at")
    search_fields = ("title", "content")
    readonly_fields = ("created_at", "updated_at")
    
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget()},
    }
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-updated_at')


@admin.register(HowItWorksContent)
class HowItWorksContentAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    list_filter = ("is_active", "created_at", "updated_at")
    search_fields = ("title", "content")
    readonly_fields = ("created_at", "updated_at")
    
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget()},
    }
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-updated_at')
