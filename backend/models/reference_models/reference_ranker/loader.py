import torch
from torch import nn
from transformers import AutoTokenizer, AutoModel
from pathlib import Path

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

class Ranker(nn.Module):
    def __init__(self, base_model):
        super().__init__()
        self.encoder = base_model
        self.scorer = nn.Linear(base_model.config.hidden_size, 1)

    def forward(self, input_ids, attention_mask):
        out = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        cls = out.last_hidden_state[:, 0, :]
        return self.scorer(cls).squeeze(-1)


class ReferenceRanker:
    def __init__(self, model_dir: str):
        model_dir = Path(model_dir)

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_dir / "tokenizer"
        )

        base = AutoModel.from_pretrained(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        self.model = Ranker(base)
        self.model.load_state_dict(
            torch.load(model_dir / "model.pt", map_location=DEVICE, weights_only=True)
        )
        self.model.to(DEVICE)
        self.model.eval()

    def score(self, query: str, context: str) -> float:
        inputs = self.tokenizer(
            query,
            context,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=128
        ).to(DEVICE)

        with torch.no_grad():
            return self.model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"]
            ).item()
