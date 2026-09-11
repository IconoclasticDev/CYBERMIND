from __future__ import annotations
import torch
import torch.nn.functional as F

def gaussian_transition_loss(pred,target): return F.smooth_l1_loss(pred,target)
def infiltration_loss(logits,target): return F.binary_cross_entropy_with_logits(logits,target.float())
def stage_loss(logits,target): return F.cross_entropy(logits,target.long())
def binary_brier(logits,target):
    p=torch.sigmoid(logits); return torch.mean((p-target.float())**2)
def graph_consistency_loss(z):
    if z.size(1)<2: return z.new_tensor(0.)
    return torch.mean((z[:,1:]-z[:,:-1])**2)
