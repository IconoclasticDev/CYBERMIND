"""Serializable explanations of the final ensemble-mean forecast risk."""
from __future__ import annotations
from dataclasses import replace
import torch
from cybermind.data.graph_builder import NODE_FEATURE_NAMES


def _feature_names(width):
    return [NODE_FEATURE_NAMES[i] if i < len(NODE_FEATURE_NAMES) else f'feature_{i}'
            for i in range(width)]


def gradient_feature_attribution(model, state, k=4, topk=10, n_rollouts=16, seed=0):
    states = list(state) if isinstance(state, (list, tuple)) else [state]
    # Also works when the caller wraps inference in no_grad/inference_mode.
    # autograd.grad leaves parameter gradients untouched.
    with torch.inference_mode(False), torch.enable_grad():
        xs = [s.x.detach().clone().requires_grad_(True) for s in states]
        probes = [replace(s, x=x, edge_index=s.edge_index.clone(), edge_attr=s.edge_attr.clone())
                  for s, x in zip(states, xs)]
        result = model.forecast(probes, k, n_rollouts=n_rollouts, seed=seed, explain=False)
        score = result['infiltration_probability'][-1]
        gradients = torch.autograd.grad(score, xs, allow_unused=True)
        products = [torch.zeros_like(x) if g is None else g * x for x, g in zip(xs, gradients)]
        attribution = torch.cat(products).abs().mean(dim=0).detach().float().cpu()
        signed = torch.cat(products).mean(dim=0).detach().float().cpu()
    values = [{'feature': name, 'attribution': float(attribution[i]), 'signed_attribution': float(signed[i])}
              for i, name in enumerate(_feature_names(len(attribution)))]
    return sorted(values, key=lambda item: item['attribution'], reverse=True)[:topk]


def explain_forecast(model, states, forecast, attention, k=4, n_rollouts=16, seed=0, topk=10):
    features = gradient_feature_attribution(model, states, k, topk, n_rollouts, seed)
    # [layers,batch,heads,query,key]: final query averaged across layers/heads.
    weights = attention[:, 0, :, -1, :].mean(dim=(0, 1)).float().cpu()
    temporal = sorted(
        [{'window_index': i, 'timestamp': float(s.timestamp), 'attention': float(weights[i])}
         for i, s in enumerate(states)], key=lambda item: item['attention'], reverse=True)
    baseline = float(forecast['infiltration_probability'][-1].detach().cpu())
    occlusion = []
    with torch.no_grad():
        for i, name in enumerate(_feature_names(states[0].x.size(-1))):
            probes = []
            for state in states:
                x = state.x.detach().clone()
                x[:, i] = 0.0
                probes.append(replace(state, x=x))
            # Common random draws isolate input changes from Monte Carlo noise.
            result = model.forecast(probes, k, n_rollouts=n_rollouts, seed=seed, explain=False)
            risk = float(result['infiltration_probability'][-1].cpu())
            occlusion.append({'feature': name, 'baseline_risk': baseline,
                              'counterfactual_risk': risk, 'risk_reduction': baseline - risk})
    occlusion.sort(key=lambda item: item['risk_reduction'], reverse=True)
    return {
        'target': 'ensemble_mean_infiltration_probability_at_final_step',
        'gradient_x_input': features,
        'temporal_attention': temporal,
        'feature_occlusion': occlusion[:topk],
        'what_would_reduce_risk': [item for item in occlusion if item['risk_reduction'] > 0][:topk],
        'baseline_risk': baseline, 'n_rollouts': n_rollouts, 'seed': seed,
        'occlusion_baseline': 'zero in model feature space (training mean for normalized continuous features)',
        'interpretation': 'Model sensitivity and attention; not proof of causality or calibrated confidence.',
    }
