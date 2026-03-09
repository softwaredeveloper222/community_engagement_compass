#!/usr/bin/env python3
"""
Migrate to new embeddings model (768-dim → 1024-dim)
This script:
1. Clears old embedding vectors from database
2. Re-embeds all document chunks with new BGE model
3. Rebuilds FAISS index with new embeddings
"""
import os
import sys
import django

# Setup Django
sys.path.append('/home/conovo-ai/Documents/knowledgeassistant')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from chat.models import PDFDocument, DocumentChunk
from chat.services import EmbeddingService
import pickle

def migrate_embeddings():
    print("="*60)
    print("Migrating to New Embeddings Model")
    print("="*60)
    
    # Step 1: Clear old embeddings
    print("\nStep 1: Clearing old embeddings from database...")
    chunk_count = DocumentChunk.objects.count()
    print(f"Found {chunk_count} document chunks")
    
    DocumentChunk.objects.all().update(embedding_vector=None)
    print("✓ Old embeddings cleared")
    
    # Step 2: Initialize new embedding service
    print("\nStep 2: Initializing new BGE embeddings model...")
    embedding_service = EmbeddingService()
    print(f"✓ Using BAAI/bge-large-en-v1.5 ({embedding_service.dimension} dimensions)")
    
    # Step 3: Re-embed all chunks
    print("\nStep 3: Re-embedding all document chunks...")
    chunks = DocumentChunk.objects.all()
    total = chunks.count()
    
    if total == 0:
        print("⚠️  No chunks found. Please upload and process documents first.")
        return
    
    print(f"Re-embedding {total} chunks...")
    
    # Process in batches for efficiency
    batch_size = 50
    chunk_list = list(chunks)
    chunk_embeddings = []
    
    for i in range(0, total, batch_size):
        batch = chunk_list[i:i + batch_size]
        batch_contents = [chunk.content for chunk in batch]
        
        # Create new embeddings
        embeddings = embedding_service.create_embeddings_batch(batch_contents)
        
        # Save to database
        for chunk, embedding in zip(batch, embeddings):
            chunk.embedding_vector = pickle.dumps(embedding)
            chunk.save()
            chunk_embeddings.append((chunk.id, embedding))
        
        progress = min(i + batch_size, total)
        print(f"  Progress: {progress}/{total} chunks ({100*progress//total}%)")
    
    print("✓ All chunks re-embedded successfully")
    
    # Step 4: Rebuild FAISS index
    print("\nStep 4: Rebuilding FAISS index...")
    
    # Delete old index files
    import os
    media_root = '/home/conovo-ai/Documents/knowledgeassistant/knowledgeassistant/media'
    index_path = os.path.join(media_root, 'faiss_index.bin')
    mapping_path = os.path.join(media_root, 'chunk_mapping.pkl')
    
    if os.path.exists(index_path):
        os.remove(index_path)
    if os.path.exists(mapping_path):
        os.remove(mapping_path)
    
    # Rebuild with new embeddings
    embedding_service.update_faiss_index()
    print("✓ FAISS index rebuilt successfully")
    
    print("\n" + "="*60)
    print("✅ Migration Complete!")
    print("="*60)
    print(f"\nMigrated {total} chunks to new embeddings model")
    print(f"Embeddings dimension: 768 → {embedding_service.dimension}")
    print("\nNext steps:")
    print("1. python manage.py runserver")
    print("2. Test your knowledge base queries")

if __name__ == "__main__":
    try:
        migrate_embeddings()
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

