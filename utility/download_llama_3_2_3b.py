from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import login
import os

def download_llama_3_2_3b():
    """Download Llama-3.2-3B model - Meta's excellent 3B model"""

    # Authenticate with Hugging Face
    hf_token = ""
    print("Authenticating with Hugging Face...")
    login(token=hf_token)
    print("✓ Authentication successful")

    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'llama-3-2-3b')
    print(f"\nDownloading Llama-3.2-3B model to {model_path}")
    print("\n" + "="*60)
    print("Llama-3.2-3B-Instruct Info:")
    print("="*60)
    print("✓ Size: 3B parameters (~6GB download)")
    print("✓ Excellent performance for its size")
    print("✓ Similar hardware requirements as Phi-2")
    print("✓ Context length: 128K tokens")
    print("✓ One of the best 3B models available")
    print("="*60)
    print()

    # Download tokenizer
    print("Step 1/2: Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        "meta-llama/Llama-3.2-3B-Instruct",
        token=hf_token,
        trust_remote_code=True
    )
    tokenizer.save_pretrained(model_path)
    print("✓ Tokenizer downloaded successfully")

    # Download model
    print("\nStep 2/2: Downloading model (this may take 5-15 minutes, ~6GB)...")
    model = AutoModelForCausalLM.from_pretrained(
        "meta-llama/Llama-3.2-3B-Instruct",
        token=hf_token,
        trust_remote_code=True,
        torch_dtype="auto",
        low_cpu_mem_usage=True
    )
    model.save_pretrained(model_path)
    print("✓ Model downloaded successfully!")
    print(f"\nModel saved to: {model_path}")
    print("\n" + "="*60)
    print("✅ DOWNLOAD COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Rebuild embeddings: python manage.py rebuild_index_optimized")
    print("2. Restart your Django application")
    print("3. Test the new model")

if __name__ == "__main__":
    download_llama_3_2_3b()

