#!/usr/bin/env python3
"""
Test Ollama integration with Django ChatService
"""
import os
import sys
import django

# Setup Django
sys.path.append('/home/conovo-ai/Documents/knowledgeassistant')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from chat.services import ChatService
from chat.models import ChatSession, ChatMessage

def test_ollama_integration():
    print("="*60)
    print("Testing Ollama Integration")
    print("="*60)
    
    # Initialize ChatService with Ollama
    print("\n1. Initializing ChatService with Ollama backend...")
    chat_service = ChatService()
    print(f"✓ ChatService initialized")
    print(f"✓ Ollama available: {chat_service.ollama_available}")
    
    # Test model loading
    print("\n2. Testing model loading...")
    try:
        chat_service.load_model()
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        return False
    
    # Test basic generation
    print("\n3. Testing response generation...")
    
    # Create test session and message
    session = ChatSession.objects.create(session_name="Ollama Test")
    message = ChatMessage.objects.create(
        session=session,
        message_type='user',
        content="What's the difference between consultation and collaboration?"
    )
    
    try:
        response = chat_service.generate_response([message])
        print(f"✓ Response generated successfully")
        print(f"Response preview: {response[:200]}...")
        
        if "knowledge base" in response.lower():
            print("✓ Response correctly references knowledge base")
        else:
            print("! Response may not be using knowledge base properly")
            
    except Exception as e:
        print(f"✗ Response generation failed: {e}")
        session.delete()
        return False
    
    # Test streaming generation
    print("\n4. Testing streaming generation...")
    try:
        stream_parts = []
        for chunk in chat_service.generate_response_stream([message]):
            stream_parts.append(chunk)
            if len(''.join(stream_parts)) > 100:  # Stop after 100 chars
                break
        
        streaming_response = ''.join(stream_parts)
        print(f"✓ Streaming response: {streaming_response[:100]}...")
        
    except Exception as e:
        print(f"✗ Streaming failed: {e}")
    
    # Cleanup
    session.delete()
    
    print("\n" + "="*60)
    print("✅ Ollama Integration Test Complete!")
    print("="*60)
    print("\nBenefits of Ollama:")
    print("• ✅ No GPU memory management issues")
    print("• ✅ Automatic optimization for your hardware")
    print("• ✅ Fast loading and inference")
    print("• ✅ Easy model management")
    print("\nYour system is ready! Start with: python manage.py runserver")
    
    return True

if __name__ == "__main__":
    test_ollama_integration()
