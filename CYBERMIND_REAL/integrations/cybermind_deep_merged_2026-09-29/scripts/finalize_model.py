#!/usr/bin/env python3
"""Create the clean final single-model CYBERMIND artifact.

The training checkpoint contains optimizer state for resume. This script creates a
portable final .pt bundle containing only model weights + architecture metadata.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--checkpoint', required=True)
    ap.add_argument('--output', default='models/cybermind_final.pt')
    args = ap.parse_args()

    ckpt_path = ROOT / args.checkpoint
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    payload = {
        'format': 'cybermind-single-model-v1',
        'model_state': ckpt['model_state'],
        'node_dim': int(ckpt['node_dim']),
        'config': ckpt.get('config', {}),
        'trained_epoch': int(ckpt.get('epoch', 0)),
        'best_train_loss': float(ckpt.get('best_loss', 0.0)),
    }
    torch.save(payload, out)
    meta = out.with_suffix('.json')
    meta.write_text(json.dumps({
        'format': payload['format'],
        'node_dim': payload['node_dim'],
        'trained_epoch': payload['trained_epoch'],
        'best_train_loss': payload['best_train_loss'],
        'source_checkpoint': str(ckpt_path.relative_to(ROOT)),
        'model_config': payload['config'].get('model', {}),
    }, indent=2))
    print(f'[FINAL MODEL] {out} ({out.stat().st_size / 1024 / 1024:.2f} MB)')
    print(f'[FINAL META]  {meta}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
