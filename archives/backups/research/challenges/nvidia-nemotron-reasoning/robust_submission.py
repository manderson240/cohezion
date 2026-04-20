#!/usr/bin/env python3
"""
Robust submission file generation for NVIDIA Nemotron Model Reasoning Challenge
Includes error handling, fallback mechanisms, and validation.
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
    """Configuration for robust submission generation."""

    # Model settings
    BASE_MODEL_NAME = "sshleifer/tiny-gpt2"

    # Data settings
    TEST_PATH = "data/test.csv"

    # Output settings
    SUBMISSION_PATH = "submissions/robust_submission.csv"
    BACKUP_SUBMISSION_PATH = "submissions/backup_submission.csv"

    # Generation settings
    MAX_LENGTH = 128
    TEMPERATURE = 0.7
    DO_SAMPLE = True
    TOP_P = 0.9

    # Device
    DEVICE = "cpu"

    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    @classmethod
    def print_config(cls):
        """Print configuration settings."""
        logger.info("\n=== ROBUST SUBMISSION GENERATION CONFIGURATION ===")
        for attr in dir(cls):
            if not attr.startswith("__"):
                value = getattr(cls, attr)
                if not callable(value):
                    logger.info(f"{attr}: {value}")
        logger.info("")


def load_model_with_fallback():
    """Load model with multiple fallback options."""
    logger.info("=== LOADING MODEL WITH FALLBACK ===")

    # Try primary model path
    model_paths = [
        "models/baseline_lora",  # Our main trained model
        "models/quick_baseline/checkpoint-best_epoch_1",  # Backup model
    ]

    tokenizer = None
    model = None

    for i, model_path in enumerate(model_paths):
        try:
            logger.info(f"Attempting to load model from: {model_path}")

            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                Config.BASE_MODEL_NAME, trust_remote_code=True
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # Load base model
            base_model = AutoModelForCausalLM.from_pretrained(
                Config.BASE_MODEL_NAME,
                trust_remote_code=True,
            )

            # Try to load PEFT adapter
            try:
                model = PeftModel.from_pretrained(base_model, model_path, is_trainable=False)
                logger.info(f"✓ Successfully loaded PEFT model from: {model_path}")
                break  # Success!
            except Exception as peft_error:
                logger.warning(f"⚠️ Failed to load PEFT adapter from {model_path}: {peft_error}")
                logger.info("Falling back to base model only")
                model = base_model
                break  # Base model is still useful

        except Exception as e:
            logger.error(f"❌ Failed to load model from {model_path}: {e}")
            if i == len(model_paths) - 1:  # Last attempt
                raise
            continue  # Try next model path

    if model is None:
        raise RuntimeError("Failed to load any model")

    model.to(Config.DEVICE)
    model.eval()

    logger.info("✓ Model loaded and ready for inference!")
    return model, tokenizer


def prepare_test_data():
    """Load and validate test data."""
    logger.info("=== PREPARING AND VALIDATING TEST DATA ===")

    if not os.path.exists(Config.TEST_PATH):
        raise FileNotFoundError(f"Test data not found: {Config.TEST_PATH}")

    df_test = pd.read_csv(Config.TEST_PATH)
    logger.info(f"Loaded test data with shape: {df_test.shape}")

    # Validate required columns
    required_columns = ["id", "prompt"]
    missing_columns = [col for col in required_columns if col not in df_test.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns in test data: {missing_columns}")

    logger.info(f"Test data columns: {list(df_test.columns)}")
    logger.info(f"Number of test samples: {len(df_test)}")

    return df_test


def generate_predictions_robust(model, tokenizer, test_df):
    """Generate predictions with error handling and retry logic."""
    logger.info("=== GENERATING PREDICTIONS WITH ROBUST ERROR HANDLING ===")

    predictions = []
    failed_generations = 0

    # Process each test example
    for idx, row in tqdm(test_df.iterrows(), total=len(test_df), desc="Generating predictions"):
        prompt = str(row["prompt"])
        test_id = str(row["id"])

        # Format input for generation
        separator = " " + tokenizer.eos_token + " "
        input_text = f"{prompt}{separator}"

        # Tokenize with error handling
        try:
            encoding = tokenizer(
                input_text, truncation=True, max_length=Config.MAX_LENGTH, return_tensors="pt"
            )
        except Exception as e:
            logger.warning(f"Tokenization failed for ID {test_id}: {e}")
            # Use a simple fallback
            encoding = tokenizer(
                " ",  # Minimal input
                truncation=True,
                max_length=Config.MAX_LENGTH,
                return_tensors="pt",
            )

        input_ids = encoding["input_ids"].to(Config.DEVICE)
        attention_mask = encoding["attention_mask"].to(Config.DEVICE)

        # Generate with retry logic
        generated_text = ""
        generation_success = False

        for attempt in range(Config.MAX_RETRIES):
            try:
                with torch.no_grad():
                    generated_ids = model.generate(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        max_length=input_ids.shape[1] + 50,  # Dynamic max length
                        temperature=Config.TEMPERATURE,
                        do_sample=Config.DO_SAMPLE,
                        top_p=Config.TOP_P,
                        pad_token_id=tokenizer.eos_token_id,
                        eos_token_id=tokenizer.eos_token_id,
                    )

                # Decode
                generated_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)

                # Extract answer part
                if separator in generated_text:
                    predicted_answer = generated_text.split(separator)[-1].strip()
                else:
                    predicted_answer = generated_text.strip()

                # Clean up answer
                predicted_answer = predicted_answer.split("\n")[0].strip()

                # Validate we got something meaningful
                if predicted_answer and len(predicted_answer.strip()) > 0:
                    generation_success = True
                    break  # Success!
                else:
                    logger.warning(f"Attempt {attempt + 1} generated empty answer for ID {test_id}")

            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed for ID {test_id}: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    import time

                    time.sleep(Config.RETRY_DELAY)  # Wait before retry

        if not generation_success:
            logger.error(f"All generation attempts failed for ID {test_id}, using fallback")
            failed_generations += 1
            predicted_answer = "ERROR: Generation failed"  # Fallback answer

        predictions.append({"id": test_id, "answer": predicted_answer})

        # Log progress
        if idx < 3:
            logger.info(f"Example {idx}:")
            logger.info(f"  ID: {test_id}")
            logger.info(f"  Prompt: {prompt[:60]}...")
            logger.info(f"  Predicted Answer: {predicted_answer}")

    logger.info(f"Total failed generations: {failed_generations}")
    return pd.DataFrame(predictions)


def save_submission_robust(submission_df):
    """Save submission file with backup."""
    logger.info("=== SAVING SUBMISSION WITH BACKUP ===")

    # Create submissions directory
    os.makedirs(os.path.dirname(Config.SUBMISSION_PATH), exist_ok=True)

    try:
        # Try primary save path
        submission_df.to_csv(Config.SUBMISSION_PATH, index=False)
        logger.info(f"✓ Submission saved to: {Config.SUBMISSION_PATH}")

        # Also save backup
        submission_df.to_csv(Config.BACKUP_SUBMISSION_PATH, index=False)
        logger.info(f"✓ Backup submission saved to: {Config.BACKUP_SUBMISSION_PATH}")

    except Exception as e:
        logger.error(f"❌ Failed to save submission: {e}")
        # Try backup location as primary
        try:
            submission_df.to_csv(Config.BACKUP_SUBMISSION_PATH, index=False)
            logger.info(f"✓ Submission saved to backup location: {Config.BACKUP_SUBMISSION_PATH}")
        except Exception as e2:
            logger.error(f"❌ Failed to save to backup location: {e2}")
            raise

    # Show submission info
    logger.info(f"Submission shape: {submission_df.shape}")
    logger.info(f"Submission columns: {list(submission_df.columns)}")

    # Show first few rows
    logger.info("First 3 rows of submission:")
    for i, row in submission_df.head(3).iterrows():
        logger.info(
            f"  {row['id']}: {row['answer'][:100]}{'...' if len(row['answer']) > 100 else ''}"
        )


def validate_submission_format(submission_df):
    """Validate submission file format."""
    logger.info("=== VALIDATING SUBMISSION FORMAT ===")

    # Check required columns
    required_columns = ["id", "answer"]
    actual_columns = list(submission_df.columns)

    missing_columns = [col for col in required_columns if col not in actual_columns]
    extra_columns = [col for col in actual_columns if col not in required_columns]

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    if extra_columns:
        logger.warning(f"Extra columns found (will be ignored): {extra_columns}")

    # Check for empty values
    empty_ids = submission_df[submission_df["id"].isna() | (submission_df["id"] == "")]
    empty_answers = submission_df[submission_df["answer"].isna() | (submission_df["answer"] == "")]

    if len(empty_ids) > 0:
        logger.warning(f"Found {len(empty_ids)} rows with empty IDs")
    if len(empty_answers) > 0:
        logger.warning(f"Found {len(empty_answers)} rows with empty answers")

    # Check answer lengths
    answer_lengths = submission_df["answer"].str.len()
    very_short_answers = submission_df[answer_lengths < 10]
    if len(very_short_answers) > 0:
        logger.warning(f"Found {len(very_short_answers)} rows with very short answers (<10 chars)")

    logger.info("✓ Submission format validation completed")
    return True


def main():
    """Main robust submission generation function."""
    logger.info(
        "🚀 Starting Robust Submission Generation for NVIDIA Nemotron Model Reasoning Challenge"
    )

    # Print configuration
    Config.print_config()

    try:
        # Load model with fallback
        model, tokenizer = load_model_with_fallback()

        # Prepare and validate test data
        test_df = prepare_test_data()

        # Generate predictions with robust error handling
        predictions_df = generate_predictions_robust(model, tokenizer, test_df)

        # Validate submission format
        is_valid = validate_submission_format(predictions_df)
        if not is_valid:
            raise ValueError("Submission format validation failed")

        # Save submission with backup
        save_submission_robust(predictions_df)

        logger.info("🎉 ROBUST SUBMISSION GENERATION COMPLETED SUCCESSFULLY!")
        logger.info(f"📁 Submission file: {Config.SUBMISSION_PATH}")
        logger.info(f"📁 Backup file: {Config.BACKUP_SUBMISSION_PATH}")

    except Exception as e:
        logger.error(f"❌ Robust submission generation failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
