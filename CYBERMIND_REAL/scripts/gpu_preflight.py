#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys
import copy
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.utils.config import load_config, edge_model_kwargs, stage_model_kwargs
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.data.types import GraphState, GraphSequenceSample
from cybermind.data.graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
from cybermind.models.world_model import WorldModel
from cybermind.utils.checkpoint_selection import CheckpointSelection
from train import (assert_split_disjoint, training_class_weight, validate_training_provenance,
                   batch_loss, autocast_context, configure_stage_class_weights)


def synthetic_model_probe(config, device='cuda'):
    """Full configured architecture, one tiny synthetic batch; never corpus approval."""
    cfg = copy.deepcopy(config)
    CheckpointSelection(cfg['train'])
    device = torch.device(device)
    torch.manual_seed(cfg.get('seed', 42))
    if device.type == 'cuda':
        torch.cuda.manual_seed_all(cfg.get('seed', 42))
        torch.cuda.reset_peak_memory_stats(device)
    history = max(2, int(cfg['data'].get('history', 4)))
    node_dim, edge_dim = len(NODE_FEATURE_NAMES), len(EDGE_FEATURE_NAMES)
    states = []
    for step in range(history):
        stage = min(step, cfg['model']['num_stages'] - 2)
        states.append(GraphState(torch.randn(3, node_dim),
            torch.tensor([[0,1,2,0],[1,2,0,2]]), torch.randn(4, edge_dim),
            ['synthetic-a','synthetic-b','synthetic-c'], float(step), float(step % 2),
            stage, 'synthetic-preflight', 'synthetic-only', {'campaign_reset': False}))
    batch = [GraphSequenceSample(states, 'synthetic-preflight', 0., 1., {'source':'synthetic'})]
    configure_stage_class_weights(cfg, batch)
    mc = cfg['model']
    model = WorldModel(node_dim, **{key: mc[key] for key in
        ('graph_hidden','graph_out','temporal_dim','nhead','temporal_layers','num_stages','dropout')},
        graph_heads=mc.get('graph_heads',8), **edge_model_kwargs(mc, observed_edge_dim=edge_dim),
        **stage_model_kwargs(cfg)).to(device)
    model.train()
    precision = cfg['train'].get('precision','fp32')
    with autocast_context(device, precision):
        loss, components = batch_loss(model, batch, cfg, device)
    if not torch.isfinite(loss):
        raise ValueError('Synthetic full-model loss is nonfinite')
    loss.backward()
    gradients = {}
    for name, parameter in model.named_parameters():
        if parameter.grad is not None:
            gradients[name] = {'finite': bool(torch.isfinite(parameter.grad).all()),
                               'norm': float(parameter.grad.float().norm())}
    groups = {'graph': 'graph.', 'temporal':'temporal.', 'dynamics':'dynamics.',
              'latent':'to_latent.', 'infiltration':'infiltration_head.', 'stage':'stage_head.'}
    if model.use_crf_stage:
        groups['crf'] = 'stage_decoder.'
    active = {group: any(row['finite'] and row['norm'] > 0 for name,row in gradients.items()
                         if name.startswith(prefix)) for group,prefix in groups.items()}
    if mc.get('use_edge_features', False):
        for layer in ('conv1', 'conv2'):
            active[f'{layer}_edge_projection'] = any(row['finite'] and row['norm'] > 0
                for name,row in gradients.items() if name.startswith(f'graph.{layer}.') and ('edge_proj' in name or 'lin_edge' in name))
    if device.type == 'cuda':
        torch.cuda.synchronize(device)
        total_memory = torch.cuda.get_device_properties(device).total_memory
        active['memory_within_device_capacity'] = torch.cuda.max_memory_reserved(device) < total_memory
    else:
        total_memory = None
    return {'mode':'synthetic', 'device':str(device), 'precision':precision,
            'full_model_config':mc, 'parameter_count':sum(p.numel() for p in model.parameters()),
            'batch_size':1, 'history':history, 'nodes_per_window':3, 'edges_per_window':4,
            'node_dim':node_dim, 'edge_dim':edge_dim, 'loss':float(loss.detach()),
            'gpu_name':torch.cuda.get_device_name(device) if device.type == 'cuda' else None,
            'device_total_memory_bytes':total_memory,
            'selection_policy':{key: cfg['train'].get(key) for key in ('selection_metric','selection_f1_tolerance','selection_stage_metric','min_delta')},
            'components':components, 'active_gradient_groups':active, 'gradients':gradients,
            'peak_allocated_bytes':torch.cuda.max_memory_allocated(device) if device.type == 'cuda' else None,
            'peak_reserved_bytes':torch.cuda.max_memory_reserved(device) if device.type == 'cuda' else None,
            'passed':all(active.values()) and all(row['finite'] for row in gradients.values()),
            'scope':'Architecture forward/backward only; does not verify real corpus, production batch memory or GB10 readiness.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/gb10_full.yaml')
    parser.add_argument('--synthetic', action='store_true', help='Test full architecture on synthetic graphs; skip real-data approval checks explicitly.')
    parser.add_argument('--output', help='Write machine-readable preflight evidence.')
    args = parser.parse_args()
    cfg = load_config(ROOT / args.config)
    failures = []
    report = {'mode':'synthetic' if args.synthetic else 'production', 'config':str(ROOT / args.config)}
    print('Python', sys.version.split()[0], 'PyTorch', torch.__version__)
    if not torch.cuda.is_available():
        failures.append('CUDA is unavailable on this runtime.')
    else:
        prop = torch.cuda.get_device_properties(0)
        print(f'GPU: {prop.name}; memory: {prop.total_memory / 1024**3:.1f} GiB')
        precision = cfg['train'].get('precision', 'fp32')
        if precision == 'bf16' and not torch.cuda.is_bf16_supported():
            failures.append('Configured bf16 is unsupported by this CUDA runtime.')
        else:
            try:
                dtype = {'bf16': torch.bfloat16, 'fp16': torch.float16, 'fp32': torch.float32}[precision]
                x = torch.randn(256, 256, device='cuda', dtype=dtype)
                assert torch.isfinite(x @ x).all()
                torch.cuda.synchronize()
                print(precision, 'CUDA matmul: PASS')
            except Exception as error:
                failures.append(f'CUDA kernel check failed: {error}')
    try:
        import torch_geometric
        print('PyG', torch_geometric.__version__)
    except ImportError:
        failures.append('Install the target-host PyG runtime before production training.')
    if args.synthetic:
        if not failures:
            try:
                report.update(synthetic_model_probe(cfg))
                if not report['passed']:
                    failures.append('Required synthetic gradients are inactive or nonfinite.')
            except Exception as error:
                failures.append(f'Synthetic full-model check failed: {error}')
        report.update(passed=not failures, failures=failures)
        if args.output:
            output = ROOT / args.output
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
        print(json.dumps({key:value for key,value in report.items() if key != 'gradients'},indent=2))
        return 1 if failures else 0
    processed = ROOT / cfg['data']['processed_dir']
    required = ['train.pt', 'val.pt', 'test.pt']
    if cfg['data'].get('require_normalization'):
        required += ['normalization.json', 'metadata.json']
    missing = [str(processed / name) for name in required if not (processed / name).is_file()]
    failures.extend(f'Missing: {path}' for path in missing)
    if not missing:
        try:
            datasets = [GraphSequenceDataset(processed / f'{split}.pt') for split in ('train', 'val', 'test')]
            if any(not len(ds) for ds in datasets):
                raise ValueError('Every split must be nonempty.')
            for left, right in ((0, 1), (0, 2), (1, 2)):
                assert_split_disjoint(datasets[left], datasets[right])
            for dataset in datasets[:2]:
                training_class_weight(dataset)
            constants = json.loads((processed / 'normalization.json').read_text()) if cfg['data'].get('require_normalization') else None
            validate_training_provenance(processed, cfg, datasets, constants)
            print('Dataset split, class and normalization checks: PASS')
        except Exception as error:
            failures.append(f'Dataset validation failed: {error}')
    if args.output:
        output = ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        report.update(passed=not failures, failures=failures)
        output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    if failures:
        for failure in failures:
            print('STOP:', failure)
        return 1
    print('Preflight passed. Profile real graph memory on GB10 before the full run.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
