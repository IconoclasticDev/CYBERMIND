#!/usr/bin/env python3
"""R4 readiness probe: one real batch, forward/backward only, no optimizer step."""
from pathlib import Path
import argparse
import copy
import json
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel
from cybermind.utils.config import load_config, edge_model_kwargs, stage_model_kwargs
from train import batch_loss, autocast_context, configure_stage_class_weights, training_class_weight


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    cfg = copy.deepcopy(load_config(ROOT / args.config))
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is required for the R4 real-batch preflight')
    device = torch.device('cuda')
    torch.manual_seed(cfg.get('seed', 42)); torch.cuda.manual_seed_all(cfg.get('seed', 42))
    torch.cuda.reset_peak_memory_stats(device)
    dataset = GraphSequenceDataset(ROOT / cfg['data']['processed_dir'] / 'train.pt')
    cfg['loss']['pos_weight'], counts = training_class_weight(dataset)
    configure_stage_class_weights(cfg, dataset)
    batch_size = int(cfg['train']['batch_size'])
    batch = dataset.samples[:batch_size]
    first = batch[0].states[0]
    mc = cfg['model']
    model = WorldModel(first.x.shape[1], **{key: mc[key] for key in
        ('graph_hidden', 'graph_out', 'temporal_dim', 'nhead', 'temporal_layers', 'num_stages', 'dropout')},
        graph_heads=mc.get('graph_heads', 8),
        **edge_model_kwargs(mc, observed_edge_dim=first.edge_attr.shape[1]),
        **stage_model_kwargs(cfg)).to(device).train()
    with autocast_context(device, cfg['train']['precision']):
        loss, components = batch_loss(model, batch, cfg, device)
    loss.backward()
    torch.cuda.synchronize(device)
    gradients = {name: {'finite': bool(parameter.grad is not None and torch.isfinite(parameter.grad).all()),
                        'norm': float(parameter.grad.float().norm()) if parameter.grad is not None else 0.0}
                 for name, parameter in model.named_parameters()}
    groups = {'graph': 'graph.', 'temporal': 'temporal.', 'dynamics': 'dynamics.',
              'latent': 'to_latent.', 'infiltration': 'infiltration_head.',
              'stage': 'stage_head.', 'crf': 'stage_decoder.'}
    active = {group: any(row['finite'] and row['norm'] > 0 for name, row in gradients.items()
                         if name.startswith(prefix)) for group, prefix in groups.items()}
    required_groups = ['graph', 'temporal', 'dynamics', 'latent', 'infiltration', 'stage']
    if cfg['loss'].get('use_crf_stage', False):
        required_groups.append('crf')
    report = {
        'passed': bool(torch.isfinite(loss) and all(active[group] for group in required_groups)),
        'scope': 'R4 readiness only: first real training batch forward/backward; no optimizer step and no model update.',
        'config': args.config,
        'gpu': torch.cuda.get_device_name(device),
        'precision': cfg['train']['precision'],
        'batch_size': batch_size,
        'gradient_accumulation': cfg['train']['grad_accumulation'],
        'history': cfg['data']['history'],
        'max_nodes_per_state': max(len(state.node_ids) for sample in batch for state in sample.states),
        'max_edges_per_state': max(state.edge_index.shape[1] for sample in batch for state in sample.states),
        'loss': float(loss.detach()),
        'components': components,
        'class_counts': counts,
        'peak_allocated_bytes': torch.cuda.max_memory_allocated(device),
        'peak_reserved_bytes': torch.cuda.max_memory_reserved(device),
        'device_total_memory_bytes': torch.cuda.get_device_properties(device).total_memory,
        'active_required_gradient_groups': active,
        'required_gradient_groups': required_groups,
        'parameters_without_training_loss_gradient': sorted(name for name, row in gradients.items() if not row['finite']),
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
