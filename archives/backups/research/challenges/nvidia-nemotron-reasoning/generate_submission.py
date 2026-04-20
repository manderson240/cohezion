#!/usr/bin/env python3
"""
Generate submission file for NVIDIA Nemotron Model Reasoning Challenge
Loads trained model and creates predictions for test data.
"""

import logging
import os

import pandas as pd
import torch
from peft import PeftModel
from tqdm.auto import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer


# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Config:
    """Configuration for submission generation."""

    # Model settings
    BASE_MODEL_NAME = "sshleifer/tiny-gpt2"  # This matches what we trained
    # For the actual challenge, we would use: "nvidia/Nemotron-3-Nano-30B-A3B"

    # LoRA settings (should match training)
    LORA_R = 8
    LORA_ALPHA = 16

    # Data settings
    TEST_PATH = "data/test.csv"

    # Output settings
    SUBMISSION_PATH = "submissions/submission.csv"

    # Generation settings
    MAX_LENGTH = 128
    TEMPERATURE = 0.7
    DO_SAMPLE = True

    # Device
    DEVICE = "cpu"  # Explicitly set to CPU since CUDA not available

    @classmethod
    def print_config(cls):
        """Print configuration settings."""
        logger.info("\n=== SUBMISSION GENERATION CONFIGURATION ===")
        for attr in dir(cls):
            if not attr.startswith("__"):
                value = getattr(cls, attr)
                if not callable(value):
                    logger.info(f"{attr}: {value}")
        logger.info("")


def load_trained_model():
    """Load the base model and apply the trained LoRA adapter."""
    logger.info("=== LOADING TRAINED MODEL ===")

    logger.info(f"Loading base model: {Config.BASE_MODEL_NAME}")
    base_model = AutoModelForCausalLM.from_pretrained(
        Config.BASE_MODEL_NAME,
        trust_remote_code=True,
    )

    # Handle tokenizer padding token
    tokenizer = AutoTokenizer.from_pretrained(Config.BASE_MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    logger.info(f"Loading LoRA adapter from: models/quick_baseline/checkpoint-best_epoch_1")
    # Load the LoRA adapter
    model = PeftModel.from_pretrained(
        base_model, "models/quick_baseline/checkpoint-best_epoch_1", is_trainable=False
    )

    model.to(Config.DEVICE)
    model.eval()

    logger.info("✓ Model loaded and ready for inference!")
    return model, tokenizer


def prepare_test_data():
    """Load and prepare test data for inference."""
    logger.info("=== PREPARING TEST DATA ===")

    df_test = pd.read_csv(Config.TEST_PATH)
    logger.info(f"Loaded test data with shape: {df_test.shape}")
    logger.info(f"Columns: {list(df_test.columns)}")

    return df_test


def generate_predictions(model, tokenizer, test_df):
    """Generate predictions for test data."""
    logger.info("=== GENERATING PREDICTIONS ===")

    predictions = []

    # Process each test example
    for idx, row in tqdm(test_df.iterrows(), total=len(test_df), desc="Generating predictions"):
        prompt = str(row["prompt"])
        test_id = str(row["id"])

        # Format input for generation (same format as training)
        separator = " " + tokenizer.eos_token + " "
        input_text = f"{prompt}{separator}"

        # Tokenize
        encoding = tokenizer(
            input_text, truncation=True, max_length=Config.MAX_LENGTH, return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(Config.DEVICE)
        attention_mask = encoding["attention_mask"].to(Config.DEVICE)

        # Generate
        with torch.no_grad():
            generated_ids = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_length=input_ids.shape[1] + 50,  # Input length + room for generation
                temperature=Config.TEMPERATURE,
                do_sample=Config.DO_SAMPLE,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        # Decode
        generated_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)

        # Extract just the answer part (after the separator)
        if separator in generated_text:
            predicted_answer = generated_text.split(separator)[-1].strip()
        else:
            predicted_answer = generated_text.strip()

        # Clean up the answer - take only the first line if multiline
        predicted_answer = predicted_answer.split("\n")[0].strip()

        predictions.append({"id": test_id, "answer": predicted_answer})

        # Log first few examples for verification
        if idx < 3:
            logger.info(f"Example {idx}:")
            logger.info(f"  ID: {test_id}")
            logger.info(f"  Prompt: {prompt[:80]}...")
            logger.info(f"  Predicted Answer: {predicted_answer}")

    return pd.DataFrame(predictions)


def save_submission(submission_df):
    """Save submission file in required format."""
    logger.info("=== SAVING SUBMISSION ===")

    # Create submissions directory if it doesn't exist
    os.makedirs(os.path.dirname(Config.SUBMISSION_PATH), exist_ok=True)

    # Save submission file
    submission_df.to_csv(Config.SUBMISSION_PATH, index=False)

    logger.info(f"✓ Submission saved to: {Config.SUBMISSION_PATH}")
    logger.info(f"Submission shape: {submission_df.shape}")
    logger.info(f"Submission columns: {list(submission_df.columns)}")

    # Show first few rows
    logger.info("First 5 rows of submission:")
    for i, row in submission_df.head().iterrows():
        logger.info(f"  {row['id']}: {row['answer']}")


def main():
    """Main submission generation function."""
    logger.info("🚀 Starting Submission Generation for NVIDIA Nemotron Model Reasoning Challenge")

    # Print configuration
    Config.print_config()

    try:
        # Load trained model
        model, tokenizer = load_trained_model()

        # Prepare test data
        test_df = prepare_test_data()

        # Generate predictions
        predictions_df = generate_predictions(model, tokenizer, test_df)

        # Save submission
        save_submission(predictions_df)

        logger.info("🎉 SUBMISSION GENERATION COMPLETED SUCCESSFULLY!")
        logger.info(f"📁 Submission file: {Config.SUBMISSION_PATH}")

    except Exception as e:
        logger.error(f"❌ Submission generation failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
