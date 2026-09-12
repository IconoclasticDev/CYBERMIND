"""Learned linear-chain CRF with explicit kill-chain transition constraints.

Matrices use [source, destination] indexing. A reset is externally declared
at its destination timestep; emissions and target labels never imply a reset.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import torch
from torch import nn
import yaml


class StageDecoder(nn.Module):
    def __init__(self, num_stages: int = 7, transition_config=None):
        super().__init__()
        if num_stages < 1:
            raise ValueError("num_stages must be positive")
        self.num_stages = num_stages
        if transition_config is None:
            config_path = Path(__file__).resolve().parents[3] / "knowledge" / "stage_mapping.yaml"
            if num_stages == 7 and config_path.exists():
                transition_config = config_path
        if isinstance(transition_config, (str, Path)):
            with Path(transition_config).open(encoding="utf-8") as handle:
                transition_config = yaml.safe_load(handle)
        if transition_config is not None and not isinstance(transition_config, Mapping):
            raise ValueError("transition_config must be a mapping or YAML path")
        config = transition_config or {}
        if int(config.get("num_stages", num_stages)) != num_stages:
            raise ValueError("transition configuration num_stages does not match decoder")
        base = torch.ones(num_stages, num_stages, dtype=torch.bool).triu()
        if num_stages == 7:
            base[6, :] = True
            base[:, 6] = True
        resets = torch.zeros_like(base)
        for source in range(num_stages):
            for destination in range(min(2, num_stages)):
                resets[source, destination] = source > destination and not base[source, destination]
        base = self._matrix(config.get("transition_matrix", base), "transition_matrix")
        resets = self._matrix(config.get("reset_transition_matrix", resets), "reset_transition_matrix")
        source = torch.arange(num_stages)[:, None]
        destination = torch.arange(num_stages)[None, :]
        if (resets & ~((destination < source) & (destination <= 1))).any():
            raise ValueError("reset_transition_matrix may only add backward transitions into stages 0 or 1")
        if not base.any(dim=0).all() or not base.any(dim=1).all():
            raise ValueError("transition_matrix must allow incoming and outgoing transitions for every state")
        self.register_buffer("allowed_transitions", base)
        self.register_buffer("reset_transitions", resets)
        self.transitions = nn.Parameter(torch.zeros(num_stages, num_stages))

    def _matrix(self, value, name):
        matrix = torch.as_tensor(value)
        if matrix.shape != (self.num_stages, self.num_stages):
            raise ValueError(f"{name} must have shape [num_stages, num_stages]")
        if not ((matrix == 0) | (matrix == 1)).all():
            raise ValueError(f"{name} must contain only boolean or 0/1 entries")
        return matrix.bool().clone()

    def _inputs(self, emissions, mask, reset_mask, tags=None):
        unbatched = emissions.ndim == 2
        if unbatched:
            emissions = emissions.unsqueeze(0)
            mask = mask.unsqueeze(0) if mask is not None else None
            reset_mask = reset_mask.unsqueeze(0) if reset_mask is not None else None
            tags = tags.unsqueeze(0) if tags is not None else None
        if emissions.ndim != 3 or emissions.shape[-1] != self.num_stages:
            raise ValueError("emissions must have shape [B,T,num_stages] or [T,num_stages]")
        if emissions.shape[0] == 0 or emissions.shape[1] == 0:
            raise ValueError("emissions must contain nonempty sequences")
        if not emissions.is_floating_point() or not torch.isfinite(emissions).all():
            raise ValueError("emissions must be finite floating-point values")
        if emissions.device != self.transitions.device:
            raise ValueError("decoder and emissions must be on the same device")
        shape = emissions.shape[:2]
        if mask is None:
            mask = torch.ones(shape, dtype=torch.bool, device=emissions.device)
        if reset_mask is None:
            reset_mask = torch.zeros(shape, dtype=torch.bool, device=emissions.device)
        for name, value in (("mask", mask), ("reset_mask", reset_mask)):
            if value.shape != shape or value.dtype != torch.bool or value.device != emissions.device:
                raise ValueError(f"{name} must be a boolean tensor matching sequence shape and device")
        if not mask[:, 0].all() or (mask[:, 1:] & ~mask[:, :-1]).any():
            raise ValueError("mask must describe nonempty contiguous prefixes")
        if tags is not None:
            if tags.shape != shape or tags.device != emissions.device or tags.dtype not in (
                torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8
            ):
                raise ValueError("tags must be integer tensors matching sequence shape and device")
            if ((tags[mask] < 0) | (tags[mask] >= self.num_stages)).any():
                raise ValueError("valid tags must be in [0,num_stages)")
            tags = tags.long().masked_fill(~mask, 0)
        return emissions.float(), mask, reset_mask, tags, unbatched

    def _allowed(self, reset):
        return self.allowed_transitions.unsqueeze(0) | (
            reset[:, None, None] & self.reset_transitions.unsqueeze(0)
        )

    def forward(self, emissions, tags, mask=None, reset_mask=None):
        """Return the batch-mean negative log likelihood, calculated in fp32.

        Padding tags are ignored (including -1). Illegal observed transitions
        raise ValueError instead of introducing infinite losses into training.
        """
        emissions, mask, resets, tags, _ = self._inputs(emissions, mask, reset_mask, tags)
        batch = torch.arange(emissions.shape[0], device=emissions.device)
        alpha = emissions[:, 0]
        score = emissions[batch, 0, tags[:, 0]]
        transitions = self.transitions.float()
        for t in range(1, emissions.shape[1]):
            allowed = self._allowed(resets[:, t])
            legal_targets = allowed[batch, tags[:, t - 1], tags[:, t]]
            if (mask[:, t] & ~legal_targets).any():
                raise ValueError(f"illegal target transition at timestep {t}; declare an explicit reset if appropriate")
            constrained = transitions.unsqueeze(0).masked_fill(~allowed, float("-inf"))
            next_alpha = torch.logsumexp(alpha.unsqueeze(2) + constrained, dim=1) + emissions[:, t]
            alpha = torch.where(mask[:, t, None], next_alpha, alpha)
            step_score = transitions[tags[:, t - 1], tags[:, t]] + emissions[batch, t, tags[:, t]]
            score = score + torch.where(mask[:, t], step_score, torch.zeros_like(step_score))
        return (torch.logsumexp(alpha, dim=1) - score).mean()

    @torch.no_grad()
    def decode(self, emissions, mask=None, reset_mask=None):
        """Return the highest-scoring legal path, with -1 in padded positions."""
        emissions, mask, resets, _, unbatched = self._inputs(emissions, mask, reset_mask)
        scores = emissions[:, 0]
        history = []
        for t in range(1, emissions.shape[1]):
            constrained = self.transitions.float().unsqueeze(0).masked_fill(~self._allowed(resets[:, t]), float("-inf"))
            best, previous = (scores.unsqueeze(2) + constrained).max(dim=1)
            scores = torch.where(mask[:, t, None], best + emissions[:, t], scores)
            history.append(previous)
        paths = torch.full(mask.shape, -1, dtype=torch.long, device=emissions.device)
        lengths = mask.sum(dim=1)
        for b in range(emissions.shape[0]):
            last = int(lengths[b]) - 1
            state = scores[b].argmax()
            paths[b, last] = state
            for t in range(last, 0, -1):
                state = history[t - 1][b, state]
                paths[b, t - 1] = state
        return paths[0] if unbatched else paths
