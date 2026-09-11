#!/usr/bin/env python3
from pathlib import Path
import argparse,sys,torch
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/gpu_128gb.yaml'); args=ap.parse_args()
print('Python',sys.version.split()[0]); print('PyTorch',torch.__version__); print('CUDA available:',torch.cuda.is_available())
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        p=torch.cuda.get_device_properties(i); print(f'GPU {i}: {p.name} | VRAM={p.total_memory/1024**3:.1f} GiB | CC={p.major}.{p.minor}')
        x=torch.randn((4096,4096),device=f'cuda:{i}',dtype=torch.float16); y=x@x; torch.cuda.synchronize(); del x,y; torch.cuda.empty_cache(); print('  FP16 matmul: OK')
else: print('No CUDA: STOP before training on GPU host.')
try:
    import torch_geometric; print('PyG',torch_geometric.__version__)
except Exception as e: print('PyG import failed:',e)
for f in ['data/processed/train.pt','data/processed/val.pt','data/processed/test.pt']:
    print(f, (ROOT/f).exists(), (ROOT/f).stat().st_size if (ROOT/f).exists() else '-')
