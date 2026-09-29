#!/usr/bin/env python3
from __future__ import annotations
import argparse, time
from pathlib import Path
import numpy as np
import onnx
import onnxruntime as ort


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('model'); ap.add_argument('--max-ms', type=float, default=50.0); ap.add_argument('--max-mb', type=float, default=1024.0); args=ap.parse_args()
    p=Path(args.model); assert p.exists(), p
    mb=p.stat().st_size/(1024*1024)
    onnx.checker.check_model(onnx.load(str(p)))
    sess=ort.InferenceSession(str(p), providers=['CPUExecutionProvider'])
    inp=sess.get_inputs()[0]
    dim=int(inp.shape[-1]) if isinstance(inp.shape[-1], int) else 512
    dt=np.float32
    x=np.zeros((1,dim),dtype=dt)
    for _ in range(5): sess.run(None,{inp.name:x})
    t0=time.perf_counter()
    for _ in range(20): sess.run(None,{inp.name:x})
    ms=(time.perf_counter()-t0)*1000/20
    print(f'valid_cpu=true size_mb={mb:.2f} latency_ms={ms:.2f}')
    if mb>=args.max_mb: raise SystemExit(f'FAILED size >= {args.max_mb} MB')
    if ms>=args.max_ms: raise SystemExit(f'WARNING/FAIL latency >= {args.max_ms} ms')

if __name__=='__main__': main()
