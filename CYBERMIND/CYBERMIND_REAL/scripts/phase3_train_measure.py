#!/usr/bin/env python3
"""Run the real training entrypoint and measure its CUDA allocator peak in-process."""
import argparse
import json
from pathlib import Path
import runpy
import sys
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--device', choices=['cpu', 'cuda'], required=True)
    parser.add_argument('--measurement', required=True)
    args = parser.parse_args()
    if args.device == 'cuda':
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA verification requested but CUDA is unavailable')
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    status = 'failed'
    original_argv = sys.argv
    try:
        sys.argv = ['train.py', '--config', args.config, '--device', args.device]
        runpy.run_path(str(Path(__file__).with_name('train.py')), run_name='__main__')
        status = 'passed'
    finally:
        sys.argv = original_argv
        if args.device == 'cuda':
            torch.cuda.synchronize()
        allocated = torch.cuda.max_memory_allocated() if args.device == 'cuda' else None
        reserved = torch.cuda.max_memory_reserved() if args.device == 'cuda' else None
        ceiling = torch.cuda.get_device_properties(0).total_memory if args.device == 'cuda' else None
        result = {'status': status, 'device': args.device,
                  'measurement_scope': 'PyTorch CUDA allocator in the actual training process; excludes driver and other processes',
                  'peak_allocated_bytes': allocated, 'peak_reserved_bytes': reserved,
                  'ceiling_bytes': ceiling,
                  'below_device_vram': max(allocated, reserved) < ceiling if allocated is not None else None}
        output = Path(args.measurement)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
