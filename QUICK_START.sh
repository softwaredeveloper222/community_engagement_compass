#!/bin/bash
# Quick Start Script for Migrating to Phi-3-mini + Best Embeddings

set -e  # Exit on error

echo "=================================================="
echo "Migration: Phi-2 → Phi-3-mini + Best Embeddings"
echo "=================================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Please run: source venv/bin/activate"
    exit 1
fi

echo "✓ Virtual environment activated"
echo ""

# Step 1: Download Phi-3-mini
echo "Step 1: Downloading Phi-3-mini model..."
echo "This will download ~7.5GB of data. Please wait..."
python utility/download_phi3_mini.py
echo "✓ Model downloaded successfully"
echo ""

# Step 2: Backup existing embeddings (optional)
echo "Step 2: Creating backup of existing embeddings..."
if [ -f "knowledgeassistant/media/faiss_index.bin" ]; then
    cp knowledgeassistant/media/faiss_index.bin knowledgeassistant/media/faiss_index_phi2.bin.backup
    cp knowledgeassistant/media/chunk_mapping.pkl knowledgeassistant/media/chunk_mapping_phi2.pkl.backup
    echo "✓ Backup created"
else
    echo "ℹ️  No existing embeddings found (this is fine for new setups)"
fi
echo ""

# Step 3: Rebuild embeddings index
echo "Step 3: Rebuilding embeddings index with new model..."
echo "This will download BAAI/bge-large-en-v1.5 (~1.3GB) and re-embed your documents"
echo "Time depends on number of documents..."
python manage.py rebuild_index_optimized
echo "✓ Embeddings index rebuilt"
echo ""

# Step 4: Test the setup
echo "Step 4: Testing new model setup..."
python test_model_loading.py
echo "✓ Model test completed"
echo ""

echo "=================================================="
echo "✅ Migration completed successfully!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Start your Django server: python manage.py runserver"
echo "2. Test with your knowledge base questions"
echo "3. Monitor response quality and accuracy"
echo ""
echo "Expected improvements:"
echo "• Much better accuracy in answering from knowledge base"
echo "• Better instruction following"
echo "• More comprehensive and natural responses"
echo "• ~10-15% better document retrieval"
echo ""
echo "See MIGRATION_GUIDE.md for detailed information"
echo "=================================================="
