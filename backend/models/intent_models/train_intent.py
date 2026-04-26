import os
import json
import torch
from torch.nn import CrossEntropyLoss
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_NAME = "microsoft/deberta-v3-base"
DATA_PATH = os.path.join(BASE_DIR, "intent_data.jsonl")
OUTPUT_DIR = os.path.join(BASE_DIR, "intent_model_output")
FINAL_DIR = os.path.join(BASE_DIR, "intent_model_output", "final")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


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
        prev = item.get("previous", "")
        curr = item["current"]

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


class_weights = torch.tensor([1.0, 1.0, 1.2]).to(DEVICE)

class WeightedTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        loss = CrossEntropyLoss(weight=class_weights)(logits, labels)
        return (loss, outputs) if return_outputs else loss


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
        per_device_train_batch_size=16,
        num_train_epochs=6,
        learning_rate=3e-5,
        weight_decay=0.01,
        fp16=torch.cuda.is_available(),
        logging_steps=50,
        save_strategy="epoch",
        save_total_limit=2,
        report_to="none",
        warmup_steps=100,
    )

    trainer = WeightedTrainer(
        model=model,
        args=args,
        train_dataset=dataset,
        tokenizer=tokenizer
    )

    print("🚀 Starting training...")
    trainer.train()

    os.makedirs(FINAL_DIR, exist_ok=True)
    trainer.save_model(FINAL_DIR)
    tokenizer.save_pretrained(FINAL_DIR)

    print("✅ FINAL INTENT MODEL SAVED TO:", FINAL_DIR)


if __name__ == "__main__":
    main()