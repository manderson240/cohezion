#!/usr/bin/env python3
"""
Quick Baseline Verification for NVIDIA Nemotron Model Reasoning Challenge
A shortened version to verify the pipeline works end-to-end.
"""

import json
import logging
import os

import pandas as pd
import torch
from peft import LoraConfig, get_peft_model
from torch.utils.data import DataLoader, Dataset
from tqdm.auto import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer, get_linear_schedule_with_warmup


# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Config:
    """Configuration class for quick baseline verification."""

    # Model settings - using a smaller model for CPU feasibility
    MODEL_NAME = "sshleifer/tiny-gpt2"  # Small model for initial pipeline testing
    MAX_LENGTH = 128

    # LoRA settings
    LORA_R = 8
    LORA_ALPHA = 16
    LORA_DROPOUT = 0.05
    LORA_TARGET_MODULES = ["c_attn"]  # GPT-2 specific

    # Training settings - reduced for quick verification
    BATCH_SIZE = 2
    GRADIENT_ACCUMULATION_STEPS = 2
    EFFECTIVE_BATCH_SIZE = BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS
    LEARNING_RATE = 1e-4
    WEIGHT_DECAY = 0.01
    NUM_EPOCHS = 1  # Just one epoch for quick verification
    WARMUP_STEPS = 10
    MAX_GRAD_NORM = 1.0

    # Data settings
    TRAIN_PATH = "data/train.csv"
    TEST_PATH = "data/test.csv"

    # Output settings
    OUTPUT_DIR = "models/quick_baseline"
    LOGGING_STEPS = 5
    EVAL_STEPS = 10
    SAVE_STEPS = 20

    # Device
    DEVICE = "cpu"  # Explicitly set to CPU since CUDA not available

    @classmethod
    def print_config(cls):
        """Print configuration settings."""
        logger.info("\n=== CONFIGURATION ===")
        for attr in dir(cls):
            if not attr.startswith("__"):
                value = getattr(cls, attr)
                if not callable(value):
                    logger.info(f"{attr}: {value}")
        logger.info("")


class ReasoningDataset(Dataset):
    """Dataset for reasoning tasks - text-to-text format."""

    def __init__(self, dataframe, tokenizer, max_length=128):
        self.dataframe = dataframe
        self.tokenizer = tokenizer
        self.max_length = max_length

        # Based on data exploration: id, prompt, answer
        self.text_column = "prompt"
        self.target_column = "answer"

        # Validate columns exist
        if self.text_column not in dataframe.columns:
            raise ValueError(f"Text column '{self.text_column}' not found in data")
        if self.target_column not in dataframe.columns:
            raise ValueError(f"Target column '{self.target_column}' not found in data")

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        row = self.dataframe.iloc[idx]

        # Get input and target text
        input_text = str(row[self.text_column])
        target_text = str(row[self.target_column])

        # Format for sequence-to-sequence: input -> target
        separator = " " + self.tokenizer.eos_token + " "
        full_text = f"{input_text}{separator}{target_text}{self.tokenizer.eos_token}"

        # Tokenize
        encoding = self.tokenizer(
            full_text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].flatten(),
            "attention_mask": encoding["attention_mask"].flatten(),
            "labels": encoding["input_ids"].flatten(),  # For causal LM
        }


def setup_model_and_tokenizer():
    """Initialize tokenizer and model with LoRA configuration."""
    logger.info("=== INITIALIZING MODEL AND TOKENIZER ===")

    logger.info(f"Loading tokenizer for {Config.MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME, trust_remote_code=True)

    # Handle tokenizer padding token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        logger.info("Set pad_token to eos_token")

    logger.info(f"Vocabulary size: {tokenizer.vocab_size}")
    logger.info(f"Model max length: {tokenizer.model_max_length}")

    logger.info(f"Loading model {Config.MODEL_NAME}...")
    try:
        model = AutoModelForCausalLM.from_pretrained(
            Config.MODEL_NAME,
            trust_remote_code=True,
        )
        logger.info("✓ Model loaded successfully!")

        # Print model info
        logger.info(f"Model type: {type(model).__name__}")
        logger.info(f"Model device: {next(model.parameters()).device}")
        logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    except Exception as e:
        logger.error(f"✗ Error loading model: {e}")
        raise

    # Configure LoRA
    logger.info("=== CONFIGURING LORA ===")
    logger.info("LoRA configuration:")
    logger.info(f"  r = {Config.LORA_R}")
    logger.info(f"  lora_alpha = {Config.LORA_ALPHA}")
    logger.info(f"  target_modules = {Config.LORA_TARGET_MODULES}")
    logger.info(f"  lora_dropout = {Config.LORA_DROPOUT}")

    lora_config = LoraConfig(
        r=Config.LORA_R,
        lora_alpha=Config.LORA_ALPHA,
        target_modules=Config.LORA_TARGET_MODULES,
        lora_dropout=Config.LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
    )

    logger.info("Applying LoRA to model...")
    model = get_peft_model(model, lora_config)
    logger.info("✓ LoRA applied successfully!")

    # Print trainable parameters
    model.print_trainable_parameters()

    return model, tokenizer


def prepare_data_loaders(tokenizer):
    """Prepare training and validation data loaders."""
    logger.info("=== PREPARING DATA LOADERS ===")

    # Load data
    logger.info("Loading competition data...")
    df_train = pd.read_csv(Config.TRAIN_PATH)
    df_test = pd.read_csv(Config.TEST_PATH)

    logger.info(f"Training data shape: {df_train.shape}")
    logger.info(f"Test data shape: {df_test.shape}")

    # Create datasets
    logger.info("Creating datasets...")
    full_dataset = ReasoningDataset(df_train, tokenizer, Config.MAX_LENGTH)

    # Use only a small subset for quick verification
    small_size = min(100, len(df_train))  # Just 100 samples for quick test
    small_indices = list(range(small_size))
    small_dataset = torch.utils.data.Subset(full_dataset, small_indices)

    # Split into train and validation (80% train, 20% validation)
    val_size = int(0.2 * len(small_dataset))
    train_size = len(small_dataset) - val_size

    train_dataset = torch.utils.data.Subset(small_dataset, range(train_size))
    val_dataset = torch.utils.data.Subset(small_dataset, range(train_size, len(small_dataset)))

    logger.info(f"Training samples: {len(train_dataset)}")
    logger.info(f"Validation samples: {len(val_dataset)}")

    # Create data loaders
    train_loader = DataLoader(
        train_dataset, batch_size=Config.BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=False
    )

    val_loader = DataLoader(
        val_dataset, batch_size=Config.BATCH_SIZE, shuffle=False, num_workers=0, pin_memory=False
    )

    logger.info("✓ Data loaders created!")

    return train_loader, val_loader, df_test


def setup_optimizer_scheduler(model, train_loader):
    """Set up optimizer and learning rate scheduler."""
    logger.info("=== SETTING UP OPTIMIZER AND SCHEDULER ===")

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=Config.LEARNING_RATE,
        weight_decay=Config.WEIGHT_DECAY,
    )

    total_steps = len(train_loader) * Config.NUM_EPOCHS // Config.GRADIENT_ACCUMULATION_STEPS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=Config.WARMUP_STEPS,
        num_training_steps=total_steps,
    )

    logger.info("✓ Optimizer and scheduler created!")
    logger.info(f"  Total training steps: {total_steps}")
    logger.info(f"  Warmup steps: {Config.WARMUP_STEPS}")

    return optimizer, scheduler, total_steps


def train_epoch(model, train_loader, optimizer, scheduler, device, epoch):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    num_batches = len(train_loader)

    progress_bar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{Config.NUM_EPOCHS}")

    for step, batch in enumerate(progress_bar):
        # Move batch to device
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        # Forward pass
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)

        loss = outputs.loss

        # Backward pass
        loss = loss / Config.GRADIENT_ACCUMULATION_STEPS
        loss.backward()

        total_loss += loss.item()

        # Optimizer step
        if (step + 1) % Config.GRADIENT_ACCUMULATION_STEPS == 0:
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), Config.MAX_GRAD_NORM)

            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            # Update progress bar
            progress_bar.set_postfix(
                {
                    "loss": f"{total_loss / (step + 1):.4f}",
                    "lr": f"{scheduler.get_last_lr()[0]:.2e}",
                }
            )

        # Logging
        if (step + 1) % Config.LOGGING_STEPS == 0:
            logger.info(f"Epoch {epoch + 1}, Step {step + 1}, Loss: {total_loss / (step + 1):.4f}")

    return total_loss / num_batches


def evaluate_model(model, val_loader, device):
    """Evaluate the model on validation set."""
    model.eval()
    total_loss = 0
    num_batches = len(val_loader)

    with torch.no_grad():
        for batch in tqdm(val_loader, desc="Evaluating"):
            # Move batch to device
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            # Forward pass
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)

            loss = outputs.loss
            total_loss += loss.item()

    return total_loss / num_batches


def save_model(model, tokenizer, output_dir, epoch=None):
    """Save model and tokenizer."""
    if epoch is not None:
        save_path = os.path.join(output_dir, f"checkpoint-{epoch}")
    else:
        save_path = output_dir

    os.makedirs(save_path, exist_ok=True)

    # Save the PEFT model
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)

    logger.info(f"✓ Model and tokenizer saved to: {save_path}")


def main():
    """Main training function."""
    logger.info(
        "🚀 Starting Quick Baseline Verification for NVIDIA Nemotron Model Reasoning Challenge"
    )
    logger.info("Building upon existing Gemini session work with LoRA fine-tuning")
    logger.info("(Using small dataset and reduced epochs for quick verification)")

    # Print configuration
    Config.print_config()

    # Set device
    device = torch.device(Config.DEVICE)
    logger.info(f"Using device: {device}")

    # Create output directory
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
    logger.info(f"✓ Output directory created: {Config.OUTPUT_DIR}")

    try:
        # Setup model and tokenizer
        model, tokenizer = setup_model_and_tokenizer()
        model.to(device)

        # Prepare data
        train_loader, val_loader, test_df = prepare_data_loaders(tokenizer)

        # Setup optimizer and scheduler
        optimizer, scheduler, total_steps = setup_optimizer_scheduler(model, train_loader)

        # Training loop
        logger.info("🎯 STARTING TRAINING LOOP")
        best_val_loss = float("inf")

        for epoch in range(Config.NUM_EPOCHS):
            # Train
            train_loss = train_epoch(model, train_loader, optimizer, scheduler, device, epoch)

            # Validate
            val_loss = evaluate_model(model, val_loader, device)

            logger.info(f"Epoch {epoch + 1}/{Config.NUM_EPOCHS}:")
            logger.info(f"  Train Loss: {train_loss:.4f}")
            logger.info(f"  Val Loss: {val_loss:.4f}")

            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                save_model(model, tokenizer, Config.OUTPUT_DIR, f"best_epoch_{epoch + 1}")
                logger.info(f"  💾 New best model saved (val_loss: {val_loss:.4f})")

            # Regular checkpoint
            save_interval = max(1, Config.SAVE_STEPS // len(train_loader))
            if (epoch + 1) % save_interval == 0 or epoch == Config.NUM_EPOCHS - 1:
                save_model(model, tokenizer, Config.OUTPUT_DIR, f"epoch_{epoch + 1}")

        # Final save
        save_model(model, tokenizer, Config.OUTPUT_DIR, "final")

        # Save training metadata
        metadata = {
            "base_model": Config.MODEL_NAME,
            "peft_type": "LORA",
            "task_type": "CAUSAL_LM",
            "trainable_params": sum(p.numel() for p in model.parameters() if p.requires_grad),
            "total_params": sum(p.numel() for p in model.parameters()),
            "config": {
                "lora_r": Config.LORA_R,
                "lora_alpha": Config.LORA_ALPHA,
                "lora_dropout": Config.LORA_DROPOUT,
                "lora_target_modules": Config.LORA_TARGET_MODULES,
                "batch_size": Config.BATCH_SIZE,
                "gradient_accumulation_steps": Config.GRADIENT_ACCUMULATION_STEPS,
                "learning_rate": Config.LEARNING_RATE,
                "num_epochs": Config.NUM_EPOCHS,
                "max_length": Config.MAX_LENGTH,
                "note": "Quick verification run with small dataset",
            },
        }

        metadata_path = os.path.join(Config.OUTPUT_DIR, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"✓ Metadata saved to: {metadata_path}")

        logger.info("🎉 QUICK BASELINE VERIFICATION COMPLETED SUCCESSFULLY!")
        logger.info(f"📁 Model saved to: {Config.OUTPUT_DIR}")
        logger.info(f"📊 Best validation loss: {best_val_loss:.4f}")

    except Exception as e:
        logger.error(f"❌ Training failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
