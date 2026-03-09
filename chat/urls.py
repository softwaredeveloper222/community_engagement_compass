from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # Chat URLs
    path('', views.chat_home, name='chat_home'),
    path('session/new/', views.create_chat_session, name='create_chat_session'),
    path('session/<uuid:session_id>/', views.chat_session, name='chat_session'),
    path('session/<uuid:session_id>/clear/', views.clear_chat, name='clear_chat'),
    path('session/<uuid:session_id>/export/', views.export_chat, name='export_chat'),
    path('session/<uuid:session_id>/rename/', views.rename_session, name='rename_session'),
    path('session/<uuid:session_id>/delete/', views.delete_session, name='delete_session'),
    path('send-message/', views.send_message, name='send_message'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('user/upload/', views.user_upload_pdf, name='user_upload_pdf'),

    # Admin URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/upload/', views.upload_pdf, name='upload_pdf'),
    path('admin/document/<uuid:doc_id>/delete/', views.delete_document, name='delete_document'),
    path('admin/document/<uuid:doc_id>/reprocess/', views.reprocess_document, name='reprocess_document'),
    path('admin/document/<uuid:doc_id>/', views.document_details, name='document_details'),
    
    # Content URLs
    path('api/about/', views.about_content, name='about_content'),
    path('api/how-it-works/', views.how_it_works_content, name='how_it_works_content'),

]
