import torch

print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
