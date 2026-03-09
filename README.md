# Knowledge Assistant

This README documents the steps to set up and run the Knowledge Assistant application.

---

## 📦 What is this repository for?

- AI-powered document search and Q&A assistant
- Uses embeddings + FAISS for fast retrieval
- Supports Hugging Face models like **Phi-2** for local inference

---

## 🚀 How do I get set up?

### 📁 Project Setup

1. Clone the repository:

```bash
git clone <your-repo-url>
cd knowledgeassistant
python3 -m venv venv
source venv/bin/activate
mkdir -p models/phi-2
huggingface-cli download microsoft/phi-2 --local-dir models/phi-2 --local-dir-use-symlinks False
