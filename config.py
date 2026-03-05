import torch

SAMPLE_RATE = 44100

# Detect CUDA properly
if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
    MODEL_NAME = "htdemucs_ft"   # Heavy, high quality
else:
    DEVICE = torch.device("cpu")
    MODEL_NAME = "mdx_extra"     # Lightweight, CPU friendly

print(f"Using device: {DEVICE}")
print(f"Using model: {MODEL_NAME}")
