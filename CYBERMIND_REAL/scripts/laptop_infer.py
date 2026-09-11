#!/usr/bin/env python3
"""Portable CYBERMIND student runtime with CPU/CUDA selection and a 6-GB VRAM guard."""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import numpy as np

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--model', default='models/cybermind_student_quant.onnx')
    ap.add_argument('--provider', choices=['auto','cpu','cuda'], default='auto')
    ap.add_argument('--input-dim', type=int, default=None)
    ap.add_argument('--allow-over-6gb', action='store_true')
    args=ap.parse_args()
    import onnxruntime as ort
    model=Path(args.model)
    if not model.exists(): raise FileNotFoundError(model)
    providers=ort.get_available_providers()
    use_cuda = args.provider=='cuda' or (args.provider=='auto' and 'CUDAExecutionProvider' in providers)
    if use_cuda and 'CUDAExecutionProvider' not in providers:
        raise RuntimeError('CUDAExecutionProvider is unavailable; use --provider cpu or install the CUDA ONNX Runtime build.')
    if use_cuda:
        try:
            import torch
            if torch.cuda.is_available():
                free,total=torch.cuda.mem_get_info(); total_gb=total/(1024**3)
                if total_gb>6.0 and not args.allow_over_6gb:
                    raise RuntimeError(f'CUDA device reports {total_gb:.2f} GB total VRAM; portable runtime is capped at 6 GB. Use --provider cpu or --allow-over-6gb.')
        except ImportError:
            pass
    selected=['CUDAExecutionProvider','CPUExecutionProvider'] if use_cuda else ['CPUExecutionProvider']
    sess=ort.InferenceSession(str(model), providers=selected)
    inp=sess.get_inputs()[0]
    dim=args.input_dim or (inp.shape[1] if isinstance(inp.shape[1],int) else None)
    if dim is None: raise RuntimeError('Input dimension is dynamic; provide --input-dim.')
    x=np.zeros((1,int(dim)),dtype=np.float32)
    for _ in range(3): sess.run(None,{inp.name:x})
    t=time.perf_counter(); out=sess.run(None,{inp.name:x}); ms=(time.perf_counter()-t)*1000
    print(json.dumps({'model':str(model),'providers':sess.get_providers(),'latency_ms':round(ms,3),'outputs':[list(o.shape) for o in out]},indent=2))
if __name__=='__main__': main()
