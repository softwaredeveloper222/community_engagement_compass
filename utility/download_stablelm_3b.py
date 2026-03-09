from transformers import AutoTokenizer, AutoModelForCausalLM
import os

def download_stablelm_3b():
    """Download StableLM-3B model - Stability AI's efficient model"""
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'stablelm-3b')
    print(f"Downloading StableLM-3B model to {model_path}")
    print("\nStableLM-3B Info:")
    print("- Size: 3B parameters (~6GB)")
    print("- Good performance for its size")
    print("- Efficient and fast")
    print("- Context length: 4K tokens")
    print()

    # Download tokenizer
    print("Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("stabilityai/stablelm-3b-4e1t", trust_remote_code=True)
    tokenizer.save_pretrained(model_path)
    print("✓ Tokenizer downloaded")

    # Download model
    print("\nDownloading model (this may take a while, ~6GB)...")
    model = AutoModelForCausalLM.from_pretrained(
        "stabilityai/stablelm-3b-4e1t",
        trust_remote_code=True,
        torch_dtype="auto",
        low_cpu_mem_usage=True
    )
    model.save_pretrained(model_path)
    print("✓ Model downloaded successfully!")
    print(f"\nModel saved to: {model_path}")
    print("\nNext steps:")
    print("1. Update the model path in services.py to 'models/stablelm-3b'")
    print("2. Restart your Django application")
    print("3. Test the new model")

if __name__ == "__main__":
    download_stablelm_3b()

