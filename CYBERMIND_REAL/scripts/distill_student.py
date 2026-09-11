#!/usr/bin/env python3
"""Train/export a laptop student and immediately verify the INT8 ONNX artifact."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from torch import optim

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.models.student import StudentGraphModel


def ensure_dirs(*paths: Path):
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def make_student_dataset(train_pt):
    from cybermind.data.dataset import GraphSequenceDataset
    ds = GraphSequenceDataset(train_pt)
    rows, risk, stages = [], [], []
    for s in ds:
        g = s.states[-1]
        x = g.x.float()
        feat = torch.cat([x.mean(0), x.max(0).values], 0)
        rows.append(feat)
        risk.append(float(g.y_infiltration))
        stages.append(int(g.y_stage))
    return torch.stack(rows), torch.tensor(risk), torch.tensor(stages)


def export_and_verify(model, out_fp32: Path, quant_out: Path):
    import onnx
    import onnxruntime as ort
    from onnxruntime.quantization import QuantType, quantize_dynamic
    ensure_dirs(out_fp32.parent, quant_out.parent, ROOT / 'models', ROOT / 'export')
    model.eval()
    dummy = torch.zeros((2, model.backbone[0].in_features), dtype=torch.float32)
    torch.onnx.export(model, dummy, str(out_fp32), input_names=['graph_summary'],
                      output_names=['infiltration_logit', 'stage_logits', 'student_latent'],
                      dynamic_axes={'graph_summary': {0: 'batch'}, 'infiltration_logit': {0: 'batch'},
                                    'stage_logits': {0: 'batch'}, 'student_latent': {0: 'batch'}},
                      opset_version=17)
    quantize_dynamic(str(out_fp32), str(quant_out), weight_type=QuantType.QInt8)
    m = onnx.load(str(quant_out)); onnx.checker.check_model(m)
    sess = ort.InferenceSession(str(quant_out), providers=['CPUExecutionProvider'])
    inp = sess.get_inputs()[0]
    shape = int(inp.shape[1]) if isinstance(inp.shape[1], int) else dummy.shape[1]
    x = np.zeros((1, shape), dtype=np.float32)
    t0 = time.perf_counter(); outputs = sess.run(None, {inp.name: x}); ms = (time.perf_counter()-t0)*1000
    if not outputs: raise RuntimeError('Student ONNX returned no outputs.')
    size_mb = quant_out.stat().st_size / (1024*1024)
    if size_mb >= 100: raise RuntimeError(f'Student ONNX is {size_mb:.2f} MB; target is <100 MB.')
    print(json.dumps({'path': str(quant_out), 'size_mb': round(size_mb, 2), 'cpu_latency_ms_1_run': round(ms, 2)}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--train-data', required=True)
    ap.add_argument('--output', default='models/cybermind_student_quant.onnx')
    ap.add_argument('--epochs', type=int, default=20)
    ap.add_argument('--hidden', type=int, default=128)
    ap.add_argument('--stages', type=int, default=7)
    args = ap.parse_args()
    X, y, st = make_student_dataset(ROOT / args.train_data)
    model = StudentGraphModel(X.size(1), args.hidden, args.stages)
    opt = optim.AdamW(model.parameters(), lr=3e-4)
    for ep in range(args.epochs):
        opt.zero_grad()
        risk, stage, z = model(X)
        loss = F.binary_cross_entropy_with_logits(risk, y) + 0.5*F.cross_entropy(stage, st)
        loss.backward(); opt.step()
        print(f'epoch={ep+1} loss={loss.item():.6f}')
    out = ROOT / args.output
    fp32 = ROOT / 'export/cybermind_student_fp32.onnx'
    ensure_dirs(out.parent, fp32.parent, ROOT / 'checkpoints', ROOT / 'models', ROOT / 'export')
    torch.save({'state_dict': model.state_dict(), 'input_dim': X.size(1), 'hidden': args.hidden, 'stages': args.stages}, ROOT / 'export/student.pt')
    export_and_verify(model, fp32, out)
    print(f'[SAVED] {out}')


if __name__ == '__main__':
    main()
