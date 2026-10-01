from __future__ import annotations
from pathlib import Path
import pickle, json
from typing import List
import torch
from torch.utils.data import Dataset
from .types import GraphSequenceSample

class GraphSequenceDataset(Dataset):
    def __init__(self, path: str|Path):
        self.path = Path(path)
        self.samples: List[GraphSequenceSample] = torch.load(self.path, map_location='cpu', weights_only=False)
    def __len__(self): return len(self.samples)
    def __getitem__(self, i): return self.samples[i]

def save_dataset(samples: List[GraphSequenceSample], path: str|Path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    torch.save(samples,path)

def collate_identity(batch):
    return batch
