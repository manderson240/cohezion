#!/usr/bin/env python3
"""
Baseline Evaluation for NVIDIA Nemotron Model Reasoning Challenge
Building upon the existing Gemini session work with LoRA fine-tuning.
Adapted for CPU-only environment.
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
    """Configuration class for baseline evaluation."""

    # Model settings - using a smaller model for CPU feasibility
    # We'll start with a smaller model to establish the pipeline, then consider approaches for the 30B model
    MODEL_NAME = "sshleifer/tiny-gpt2"  # Small model for initial pipeline testing
    # For the actual challenge, we would use: "nvidia/Nemotron-3-Nano-30B-A3B"
    MAX_LENGTH = 128  # Reduced for smaller model

    # LoRA settings (from Gemini session work, adapted)
    LORA_R = 8
    LORA_ALPHA = 16
    LORA_DROPOUT = 0.05
    # For tiny-gpt2, we target different modules
    LORA_TARGET_MODULES = ["c_attn"]  # GPT-2 specific

    # Training settings
    BATCH_SIZE = 4
    GRADIENT_ACCUMULATION_STEPS = 4
    EFFECTIVE_BATCH_SIZE = BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS
    LEARNING_RATE = 1e-4
    WEIGHT_DECAY = 0.01
    NUM_EPOCHS = 3
    WARMUP_STEPS = 50
    MAX_GRAD_NORM = 1.0

    # Data settings
    TRAIN_PATH = "data/train.csv"
    TEST_PATH = "data/test.csv"

    # Output settings
    OUTPUT_DIR = "models/baseline_lora"
    LOGGING_STEPS = 25
    EVAL_STEPS = 50
    SAVE_STEPS = 100

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
        # We'll use the format: input + separator + target + EOS
        separator = " " + self.tokenizer.eos_token + " "  # Using EOS as separator
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

    # Split into train and validation (90% train, 10% validation)
    val_size = int(0.1 * len(df_train))
    train_size = len(df_train) - val_size

    train_dataset = torch.utils.data.Subset(full_dataset, range(train_size))
    val_dataset = torch.utils.data.Subset(full_dataset, range(train_size, len(df_train)))

    logger.info(f"Training samples: {len(train_dataset)}")
    logger.info(f"Validation samples: {len(val_dataset)}")

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=Config.BATCH_SIZE,
        shuffle=True,
        num_workers=0,  # Set to 0 for CPU to avoid multiprocessing issues
        pin_memory=False,
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


def generate_sample_predictions(model, tokenizer, test_df, device, num_samples=3):
    """Generate sample predictions to verify the model works."""
    logger.info("=== GENERATING SAMPLE PREDICTIONS ===")

    model.eval()
    samples_to_show = min(num_samples, len(test_df))

    for i in range(samples_to_show):
        row = test_df.iloc[i]
        prompt = str(row["prompt"])
        true_answer = str(row["answer"])

        # Format input
        separator = " " + tokenizer.eos_token + " "
        input_text = f"{prompt}{separator}"

        # Tokenize
        encoding = tokenizer(
            input_text, truncation=True, max_length=Config.MAX_LENGTH, return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(device)
        attention_mask = encoding["attention_mask"].to(device)

        # Generate
        with torch.no_grad():
            generated_ids = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_length=Config.MAX_LENGTH,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        # Decode
        generated_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)

        # Extract just the answer part (after the separator)
        if separator in generated_text:
            predicted_answer = generated_text.split(separator)[-1].strip()
        else:
            predicted_answer = generated_text.strip()

        logger.info(f"Sample {i + 1}:")
        logger.info(f"  Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        logger.info(f"  True Answer: {true_answer}")
        logger.info(f"  Predicted Answer: {predicted_answer}")
        logger.info("")


def main():
    """Main training function."""
    logger.info("🚀 Starting Baseline Evaluation for NVIDIA Nemotron Model Reasoning Challenge")
    logger.info("Building upon existing Gemini session work with LoRA fine-tuning")
    logger.info("(Adapted for CPU-only environment with smaller model for pipeline validation)")

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

        # Generate sample predictions
        generate_sample_predictions(model, tokenizer, test_df, device)

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
                "note": "Used smaller model (sshleifer/tiny-gpt2) for CPU feasibility in baseline",
            },
        }

        metadata_path = os.path.join(Config.OUTPUT_DIR, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"✓ Metadata saved to: {metadata_path}")

        logger.info("🎉 BASELINE EVALUATION COMPLETED SUCCESSFULLY!")
        logger.info(f"📁 Model saved to: {Config.OUTPUT_DIR}")
        logger.info(f"📊 Best validation loss: {best_val_loss:.4f}")
        logger.info("")
        logger.info("🔧 NEXT STEPS FOR FULL 30B MODEL:")
        logger.info("1. Consider quantization techniques (8-bit/4-bit) for memory efficiency")
        logger.info("2. Use gradient checkpointing to reduce memory usage")
        logger.info("3. Explore CPU-optimized training strategies")
        logger.info("4. Alternatively, access GPU-enabled environment for full model training")

    except Exception as e:
        logger.error(f"❌ Training failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
