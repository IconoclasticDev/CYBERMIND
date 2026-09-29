from __future__ import annotations
import torch
from torch import nn

class StudentGraphModel(nn.Module):
    """Laptop-sized graph-state surrogate.

    Input is a fixed-size graph summary rather than raw variable-size graphs, making ONNX
    deployment straightforward. Distillation learns teacher risk/stage behaviour from these summaries.
    """
    def __init__(self, input_dim: int, hidden: int = 128, num_stages: int = 7):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(input_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU()
        )
        self.infiltration = nn.Linear(hidden, 1)
        self.stage = nn.Linear(hidden, num_stages)
        self.latent = nn.Linear(hidden, hidden)
    def forward(self, x):
        h = self.backbone(x)
        return self.infiltration(h).squeeze(-1), self.stage(h), self.latent(h)
