#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.utils.config import load_config
from cybermind.data.dataset import GraphSequenceDataset
from train import assert_split_disjoint, training_class_weight, validate_training_provenance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/gb10_full.yaml')
    args = parser.parse_args()
    cfg = load_config(ROOT / args.config)
    failures = []
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
    if failures:
        for failure in failures:
            print('STOP:', failure)
        return 1
    print('Preflight passed. Profile real graph memory on GB10 before the full run.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
