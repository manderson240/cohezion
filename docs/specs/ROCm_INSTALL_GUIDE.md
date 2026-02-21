# ROCm Installation Guide - Run These Commands

## Step 1: Install ROCm 7.2 (needs sudo password)

```bash
cd ~/dev/cohezion
sudo apt install ./amdgpu-install_7.2.70200-1_all.deb -y
sudo apt update
sudo apt install python3-setuptools python3-wheel
sudo usermod -a -G render,video $LOGNAME
sudo apt install rocm
```

## Step 2: Reboot

```bash
sudo reboot
```

## Step 3: After Reboot, Install PyTorch with ROCm

```bash
cd ~/LlamaFactory
rm -rf .venv && uv venv --python 3.12
source .venv/bin/activate

# Install with ROCm support
uv pip install torch --index-url https://download.pytorch.org/whl/rocm6.0

# Verify
python -c "import torch; print(f'ROCm: {torch.version.hip}')"
```

## Step 4: Train

```bash
cd ~/LlamaFactory
source .venv/bin/activate

llamafactory-cli train examples/training/qwen3_cohezion_qlora.yaml
```

## Verification After Install

```bash
rocminfo
# Should show GPU info
```
