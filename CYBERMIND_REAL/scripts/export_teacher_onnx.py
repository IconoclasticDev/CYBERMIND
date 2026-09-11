#!/usr/bin/env python3
"""Export the trained CYBERMIND teacher and verify the ONNX artifact."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path):
    import yaml
    return yaml.safe_load(path.read_text())


def build_model(cfg, node_dim, state):
    from cybermind.models.world_model import WorldModel
    m = WorldModel(
        node_dim,
        graph_hidden=cfg['model']['graph_hidden'],
        graph_out=cfg['model']['graph_out'],
        temporal_dim=cfg['model']['temporal_dim'],
        nhead=cfg['model']['nhead'],
        temporal_layers=cfg['model']['temporal_layers'],
        num_stages=cfg['model']['num_stages'],
        dropout=cfg['model']['dropout'],
        graph_heads=cfg['model'].get('graph_heads', 8),
    )
    m.load_state_dict(state)
    return m.eval()


class ExportWrapper(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.dynamic = model.dynamics
        self.risk = model.infiltration_head
        self.stage = model.stage_head

    def forward(self, z):
        # Export the transition mean; stochastic forecasting stays in the teacher runtime.
        z1 = self.dynamic(z)['mean']
        return z1, self.risk(z1), self.stage(z1)


def verify_onnx(path: Path, expected_batch: int = 2) -> None:
    import numpy as np
    import onnx
    import onnxruntime as ort
    size_mb = path.stat().st_size / (1024 * 1024)
    model = onnx.load(str(path))
    onnx.checker.check_model(model)
    sess = ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
    input_name = sess.get_inputs()[0].name
    dim = sess.get_inputs()[0].shape[1]
    dim = int(dim) if isinstance(dim, int) else 512
    x = np.zeros((expected_batch, dim), dtype=np.float16 if 'FLOAT16' in str(sess.get_inputs()[0].type) else np.float32)
    outputs = sess.run(None, {input_name: x})
    if not outputs or any(o is None for o in outputs):
        raise RuntimeError('ONNX CPU verification produced no valid outputs.')
    print(f'[ONNX VERIFY] valid + CPU executable; size={size_mb:.2f} MB; outputs={len(outputs)}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--checkpoint', required=True)
    ap.add_argument('--output', default='export/cybermind_teacher_fp16.onnx')
    args = ap.parse_args()
    cfg = load_yaml(ROOT / args.config)
    ckpt = torch.load(ROOT / args.checkpoint, map_location='cpu', weights_only=False)
    model = build_model(cfg, ckpt['node_dim'], ckpt['model_state'])
    out = ROOT / args.output
    ensure_dirs(out.parent, ROOT / 'checkpoints', ROOT / 'models', ROOT / 'export')
    wrapper = ExportWrapper(model).half()
    dummy = torch.zeros((2, int(cfg['model']['temporal_dim'])), dtype=torch.float16)
    torch.onnx.export(
        wrapper, dummy, str(out),
        input_names=['latent_state'],
        output_names=['next_latent', 'infiltration_logit', 'stage_logits'],
        dynamic_axes={'latent_state': {0: 'batch'}, 'next_latent': {0: 'batch'},
                      'infiltration_logit': {0: 'batch'}, 'stage_logits': {0: 'batch'}},
        opset_version=17,
    )
    print(f'[SAVED] {out}')
    verify_onnx(out)


if __name__ == '__main__':
    main()
