import os
import json
import torch
import gc  # Added for garbage collection
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments
)

# =========================
# PATHS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_NAME = "microsoft/deberta-v3-base"
DATA_PATH = os.path.join(BASE_DIR, "grounding_data.jsonl")
OUTPUT_DIR = os.path.join(BASE_DIR, "grounding_model")
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# =========================
# Dataset
# =========================
class GroundingDataset(Dataset):
    def __init__(self, path, tokenizer):
        self.samples = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                self.samples.append(json.loads(line))
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]
        
        # Combine question and sentence
        text = f"Question: {item['question']} Sentence: {item['sentence']}"
        
        enc = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=128,
            return_tensors="pt",
        )
        
        # Label is 0 or 1 (not grounded or grounded)
        label = 1 if item["label"] >= 0.5 else 0
        
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(label, dtype=torch.long),
        }


# =========================
# Train
# =========================
def main():
    print("📂 DATA PATH:", DATA_PATH)
    print("💾 FINAL MODEL PATH:", FINAL_DIR)

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2  # Binary: 0 (not grounded), 1 (grounded)
    ).to(DEVICE)

    # Load dataset
    dataset = GroundingDataset(DATA_PATH, tokenizer)
    print(f"📊 Loaded {len(dataset)} training examples")

    # Training arguments
    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=16,
        num_train_epochs=10,
        learning_rate=3e-5,
        fp16=torch.cuda.is_available(),
        logging_steps=10,
        save_strategy="epoch",
        report_to="none"
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
        tokenizer=tokenizer
    )

    # Train
    print("🚀 Starting training...")
    trainer.train()

    # --- WINDOWS FILE LOCK FIX ---
    # This block forces Python to release the model files from memory
    # so Windows allows us to save them without 'OS Error 1224'.
    print("🧹 Cleaning up memory to release file locks...")
    del trainer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    # -----------------------------

    # Save final model
    print("💾 Saving final model...")
    os.makedirs(FINAL_DIR, exist_ok=True)
    
    # Save model and tokenizer to the FINAL directory
    model.save_pretrained(FINAL_DIR)
    tokenizer.save_pretrained(FINAL_DIR)

    # Verify files
    files = os.listdir(FINAL_DIR)
    print(f"✅ FINAL GROUNDING MODEL SAVED TO: {FINAL_DIR}")
    print(f"📁 Files: {files}")


if __name__ == "__main__":
    main()