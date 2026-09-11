"""Diagonal Gaussian latent transitions with differentiable sampled rollouts."""
from __future__ import annotations
import torch
from torch import nn


class DynamicsModel(nn.Module):
    def __init__(self, latent_dim, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(latent_dim, hidden_dim), nn.GELU(),
                                 nn.LayerNorm(hidden_dim), nn.Linear(hidden_dim, latent_dim))
        self.gate = nn.Sequential(nn.Linear(latent_dim, latent_dim), nn.Sigmoid())
        self.logvar_net = nn.Sequential(nn.Linear(latent_dim, hidden_dim), nn.GELU(),
                                       nn.Linear(hidden_dim, latent_dim))
        nn.init.constant_(self.logvar_net[-1].bias, -4.0)

    def forward(self, z):
        return {'mean': z + self.gate(z) * self.net(z),
                'logvar': self.logvar_net(z).clamp(-10.0, 5.0)}

    @staticmethod
    def sample(mean, logvar, generator=None):
        noise = torch.randn(mean.shape, dtype=mean.dtype, device=mean.device, generator=generator)
        return mean + torch.exp(0.5 * logvar) * noise

    def rollout(self, z0, steps, generator=None, stochastic=True):
        if steps < 0:
            raise ValueError('steps must be nonnegative')
        zs = [z0]
        z = z0
        for _ in range(steps):
            params = self(z)
            z = self.sample(**params, generator=generator) if stochastic else params['mean']
            zs.append(z)
        return torch.stack(zs, dim=0)
