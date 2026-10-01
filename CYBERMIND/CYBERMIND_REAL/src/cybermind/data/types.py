from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import torch

@dataclass
class GraphState:
    x: torch.Tensor
    edge_index: torch.Tensor
    edge_attr: torch.Tensor
    node_ids: List[str]
    timestamp: float
    y_infiltration: float
    y_stage: int
    scenario_id: str
    attack_label: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphSequenceSample:
    states: List[GraphState]
    scenario_id: str
    start_time: float
    window_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.states)

    def __len__(self) -> int:
        return len(self.states)
