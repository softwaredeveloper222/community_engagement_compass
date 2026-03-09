from transformers import AutoTokenizer, AutoModelForCausalLM
import os

def download_phi3_mini():
    """Download Phi-3-mini model - successor to Phi-2 with better performance
    
    NO AUTHENTICATION REQUIRED - This model is open and free to use!
    """
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'phi-3-mini')
    print(f"Downloading Phi-3-mini model to {model_path}")
    print("\n" + "="*60)
    print("Phi-3-mini-4k-instruct Info:")
    print("="*60)
    print("✓ Size: 3.8B parameters (~7.5GB download)")
    print("✓ MUCH better performance than Phi-2")
    print("✓ Same hardware requirements as Phi-2")
    print("✓ Context length: 4K tokens")
    print("✓ NO AUTHENTICATION REQUIRED")
    print("✓ Licensed for commercial use")
    print("="*60)
    print()

    # Download tokenizer
    print("Step 1/2: Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)
    tokenizer.save_pretrained(model_path)
    print("✓ Tokenizer downloaded successfully")

    # Download model
    print("\nStep 2/2: Downloading model (this may take 5-15 minutes, ~7.5GB)...")
    import torch
    model = AutoModelForCausalLM.from_pretrained(
        "microsoft/Phi-3-mini-4k-instruct",
        trust_remote_code=True,
        torch_dtype=torch.float16,  # Use float16 for efficiency
        low_cpu_mem_usage=True,
        attn_implementation="eager"  # Avoid flash-attention warning
    )
    model.save_pretrained(model_path)
    print("✓ Model downloaded successfully!")
    print(f"\nModel saved to: {model_path}")
    print("\n" + "="*60)
    print("✅ DOWNLOAD COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Update services.py to use 'models/phi-3-mini'")
    print("2. Rebuild embeddings: python manage.py rebuild_index_optimized")
    print("3. Restart your Django application")
    print("4. Test the new model")

if __name__ == "__main__":
    download_phi3_mini()
