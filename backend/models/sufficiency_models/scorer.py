# backend/models/sufficiency_models/scorer.py

import torch
from transformers import AutoTokenizer
from .model import SufficiencyModel

class SufficiencyScorer:
    def __init__(self, model_path: str, base_model: str, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model,
            local_files_only=True
        )

        self.model = SufficiencyModel(base_model)
        self.model.load_state_dict(
            torch.load(f"{model_path}/model.pt", map_location=self.device)
        )
        self.model.to(self.device)
        self.model.eval()

    def _format_input(self, question: str, sentences: list[str], intent: str) -> str:
        lines = [
            f"Question: {question}",
            f"Intent: {intent}",
            "Evidence:"
        ]
        for i, s in enumerate(sentences, 1):
            lines.append(f"{i}. {s}")
        return "\n".join(lines)

    @torch.inference_mode()
    def score(self, question: str, sentences: list[str], intent: str) -> float:
        text = self._format_input(question, sentences, intent)

        enc = self.tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt"
        )

        enc = {k: v.to(self.device) for k, v in enc.items()}
        score = self.model(**enc).item()
        return float(score)
