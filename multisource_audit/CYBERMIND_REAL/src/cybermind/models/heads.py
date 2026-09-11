from __future__ import annotations
import torch
from torch import nn

class FutureStateHead(nn.Module):
    def __init__(self,latent_dim): self.net=nn.Sequential(nn.Linear(latent_dim,latent_dim),nn.GELU(),nn.Linear(latent_dim,latent_dim))
    def __init__(self,latent_dim):
        super().__init__(); self.net=nn.Sequential(nn.Linear(latent_dim,latent_dim),nn.GELU(),nn.Linear(latent_dim,latent_dim))
    def forward(self,z): return self.net(z)

class InfiltrationHead(nn.Module):
    def __init__(self,latent_dim):
        super().__init__(); self.net=nn.Sequential(nn.Linear(latent_dim,128),nn.GELU(),nn.Dropout(.1),nn.Linear(128,1))
    def forward(self,z): return self.net(z).squeeze(-1)

class StageHead(nn.Module):
    def __init__(self,latent_dim,num_stages=4):
        super().__init__(); self.net=nn.Sequential(nn.Linear(latent_dim,128),nn.GELU(),nn.Linear(128,num_stages))
    def forward(self,z): return self.net(z)
