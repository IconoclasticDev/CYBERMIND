from __future__ import annotations
import torch
import torch.nn.functional as F

def gaussian_transition_loss(pred, target, logvar=None):
    if logvar is None:
        return F.smooth_l1_loss(pred.float(), target.float())
    # Compute the likelihood in fp32 even inside bf16 autocast.
    logvar = logvar.float().clamp(-10., 5.)
    return .5 * (logvar + (target.float()-pred.float()).square() * torch.exp(-logvar)).mean()

def infiltration_loss(logits, target, pos_weight=None):
    weight = None if pos_weight is None else torch.as_tensor(pos_weight, device=logits.device, dtype=torch.float32)
    return F.binary_cross_entropy_with_logits(logits.float(), target.float(), pos_weight=weight)
def stage_loss(logits,target): return F.cross_entropy(logits,target.long())
def binary_brier(logits,target):
    p=torch.sigmoid(logits.float()); return torch.mean((p-target.float())**2)
def graph_consistency_loss(z):
    if z.size(1)<2: return z.new_tensor(0.)
    return torch.mean((z[:,1:].float()-z[:,:-1].float())**2)
