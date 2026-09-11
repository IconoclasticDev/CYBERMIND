from __future__ import annotations
import torch
from torch import nn

class DynamicsModel(nn.Module):
    def __init__(self,latent_dim,hidden_dim=256):
        super().__init__(); self.net=nn.Sequential(nn.Linear(latent_dim,hidden_dim),nn.GELU(),nn.LayerNorm(hidden_dim),nn.Linear(hidden_dim,latent_dim))
        self.gate=nn.Sequential(nn.Linear(latent_dim,latent_dim),nn.Sigmoid())
    def forward(self,z):
        delta=self.net(z); g=self.gate(z); return z + g*delta
    def rollout(self,z0,steps):
        zs=[z0]; z=z0
        for _ in range(steps): z=self.forward(z); zs.append(z)
        return torch.stack(zs,dim=0)
