# backend/models/sufficiency_models/model.py

import torch
import torch.nn as nn
from transformers import AutoModel


class SufficiencyModel(nn.Module):
    def __init__(self, base_model: str):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(
            base_model,
            local_files_only=True
        )
        hidden = self.encoder.config.hidden_size
        self.regressor = nn.Linear(hidden, 1)

    def forward(self, input_ids, attention_mask, **kwargs):
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        pooled = outputs.last_hidden_state[:, 0]  # [CLS]
        score = self.regressor(pooled)
        return torch.sigmoid(score).squeeze(-1)
