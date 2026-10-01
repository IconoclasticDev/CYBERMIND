#!/usr/bin/env python3
"""Export the trained CYBERMIND model and verify the ONNX artifact."""
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
    model_cfg = dict(cfg.get('model', {}))
    # Older checkpoints may not have stored graph_heads. When using the pure
    # PyTorch fallback, infer the head count from the first projection shape.
    graph_heads = model_cfg.get('graph_heads')
    if graph_heads is None:
        w = state.get('graph.conv1.lin.weight')
        hidden = int(model_cfg.get('graph_hidden', 128))
        if w is not None and w.ndim == 2 and w.shape[0] % hidden == 0:
            graph_heads = max(1, int(w.shape[0] // hidden))
        else:
            graph_heads = 1
    m = WorldModel(
        node_dim,
        graph_hidden=model_cfg['graph_hidden'],
        graph_out=model_cfg['graph_out'],
        temporal_dim=model_cfg['temporal_dim'],
        nhead=model_cfg['nhead'],
        temporal_layers=model_cfg['temporal_layers'],
        num_stages=model_cfg['num_stages'],
        dropout=model_cfg['dropout'],
        graph_heads=graph_heads,
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
        z1 = self.dynamic(z)
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
    ap.add_argument('--output', default='export/cybermind_compact.onnx')
    args = ap.parse_args()
    cfg = load_yaml(ROOT / args.config)
    ckpt = torch.load(ROOT / args.checkpoint, map_location='cpu', weights_only=False)
    # Prefer the architecture stored with the checkpoint so an old/new config file
    # cannot accidentally instantiate a shape-incompatible model.
    ckpt_cfg = ckpt.get('config') or cfg
    model = build_model(ckpt_cfg, ckpt['node_dim'], ckpt['model_state'])
    cfg = ckpt_cfg
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
