#!/usr/bin/env python3
"""History-only one-window forecasting baseline; never reads target features."""
from pathlib import Path
import argparse
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.baselines.protocol import evaluate_baseline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--processed', default='data/processed')
    parser.add_argument('--split', default='test', choices=['val', 'test'])
    parser.add_argument('--features', choices=['node', 'node_edge'], default='node_edge')
    parser.add_argument('--threshold', type=float, default=0.5)
    parser.add_argument('--output')
    args = parser.parse_args()
    result = evaluate_baseline(ROOT / args.processed, args.split, args.features, args.threshold)
    output = ROOT / args.output if args.output else ROOT / 'results' / f'baseline_{args.split}.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
