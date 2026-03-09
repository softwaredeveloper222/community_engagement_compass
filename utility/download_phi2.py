from transformers import AutoTokenizer, AutoModelForCausalLM
import os

def download_phi2():
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'phi-2')
    print(f"Downloading Phi-2 model to {model_path}")

    # Download tokenizer
    print("Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2", trust_remote_code=True)
    tokenizer.save_pretrained(model_path)

    # Download model
    print("Downloading model...")
    model = AutoModelForCausalLM.from_pretrained(
        "microsoft/phi-2",
        trust_remote_code=True,
        torch_dtype="auto",
        low_cpu_mem_usage=True
    )
    model.save_pretrained(model_path)
    print("Download complete!")

if __name__ == "__main__":
    download_phi2()
