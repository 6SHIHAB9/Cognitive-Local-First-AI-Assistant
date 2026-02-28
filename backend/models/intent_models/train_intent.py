import os
import json
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments
)

# =========================
# PATHS (ABSOLUTE, SAFE)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_NAME = "microsoft/deberta-v3-base"
DATA_PATH = os.path.join(BASE_DIR, "intent_data.jsonl")  # ✅ Combined file
OUTPUT_DIR = os.path.join(BASE_DIR, "intent_model_output")
FINAL_DIR = os.path.join(BASE_DIR, "models", "intent_models", "final")  # ✅ Match router.py path

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# =========================
# Dataset
# =========================
class IntentDataset(Dataset):
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
        
        # Format with previous context
        prev = item.get("previous", "")
        curr = item["current"]
        
        # Simple format - let DeBERTa figure out the pattern
        if prev:
            text = f"Previous: {prev} Current: {curr}"
        else:
            text = f"Current: {curr}"
        
        enc = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=128,
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(int(item["label"]), dtype=torch.long),
        }


# =========================
# Train
# =========================
def main():
    print("📂 DATA PATH:", DATA_PATH)
    print("💾 FINAL MODEL PATH:", FINAL_DIR)
    print("🔥 DEVICE:", DEVICE)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=3
    ).to(DEVICE)

    dataset = IntentDataset(DATA_PATH, tokenizer)
    print(f"📊 Dataset size: {len(dataset)} examples")

    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=16,  # ✅ Reduced from 32 (safer for memory)
        num_train_epochs=5,  # ✅ Reduced from 6 (5k examples is enough)
        learning_rate=3e-5,  # ✅ Standard DeBERTa learning rate
        fp16=torch.cuda.is_available(),
        logging_steps=50,
        save_strategy="epoch",
        save_total_limit=2,  # ✅ Keep only best 2 checkpoints
        report_to="none",
        warmup_steps=100,  # ✅ Warmup for stable training
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
        tokenizer=tokenizer
    )

    print("🚀 Starting training...")
    trainer.train()

    # =========================
    # SAVE FINAL MODEL
    # =========================
    os.makedirs(FINAL_DIR, exist_ok=True)
    trainer.save_model(FINAL_DIR)
    tokenizer.save_pretrained(FINAL_DIR)

    print("✅ FINAL INTENT MODEL SAVED TO:", FINAL_DIR)


if __name__ == "__main__":
    main()