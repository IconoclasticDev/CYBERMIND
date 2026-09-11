#!/usr/bin/env python3
"""End-to-end CYBERMIND training launcher.

The launcher deliberately does everything *except* deciding the scientific training
hyperparameters. It validates the host, optionally downloads/normalizes data, creates
leakage-safe graph sequences, runs baselines, trains/resumes the world model, evaluates,
and packages the run artifacts.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(cmd, *, env=None, allow_fail=False):
    cmd = [str(x) for x in cmd]
    print("\n$", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=ROOT, env=env)
    if p.returncode and not allow_fail:
        raise SystemExit(f"Command failed with exit code {p.returncode}: {' '.join(cmd)}")
    return p.returncode


def exists_nonempty(p: Path) -> bool:
    return p.exists() and (p.stat().st_size > 0 if p.is_file() else any(p.rglob("*")))


def load_yaml(path: Path):
    import yaml
    return yaml.safe_load(path.read_text())


def check_gpu(config: str):
    rc = run([PYTHON, "scripts/gpu_preflight.py", "--config", config], allow_fail=True)
    if rc:
        raise SystemExit("Preflight failed. Fix the reported runtime or dataset prerequisites before training.")


def ensure_data(source: str, *, download: bool):
    raw = ROOT / "data/raw/CIC-IDS-2018"
    if source != "CIC-IDS2018":
        return
    if exists_nonempty(raw):
        print(f"[DATA] raw data present: {raw}")
        return
    if not download:
        raise SystemExit(f"No CIC-IDS2018 data found at {raw}. Automatic download disabled.")
    # Bootstrap AWS CLI when the host does not already have it. This is only used
    # for the public, unsigned CIC-IDS2018 S3 bucket.
    if shutil.which("aws") is None:
        print("[BOOTSTRAP] AWS CLI not found; installing awscli into the active Python environment...")
        run([PYTHON, "-m", "pip", "install", "awscli"], allow_fail=False)
    run(["bash", "scripts/prepare_cic2018_public.sh"])


def normalize(source: str):
    raw = ROOT / "data/raw/CIC-IDS-2018"
    out = ROOT / "data/intermediate/CIC-IDS2018"
    if not any(out.rglob("*.parquet")) and not any(out.rglob("*.csv")):
        run([PYTHON, "scripts/build_corpus.py", "--source", source, "--input", str(raw), "--output", str(out)])
    else:
        print(f"[DATA] normalized corpus already present: {out}")


def prepared(processed):
    p = ROOT / processed
    return all((p / f).exists() and (p / f).stat().st_size > 0 for f in ("train.pt", "val.pt", "test.pt"))


def package_run(tag: str, config: str):
    out = ROOT / "results" / f"run_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    for src in [ROOT / "checkpoints", ROOT / "results"]:
        if src.exists():
            for f in src.glob("*"):
                if f.name == out.name or f.is_dir():
                    continue
                if f.is_file():
                    shutil.copy2(f, out / f.name)
    (out / "run_manifest.json").write_text(json.dumps({
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": config,
        "python": sys.version,
        "cwd": str(ROOT),
    }, indent=2))
    print(f"[DONE] Run artifacts: {out}")


def main():
    ap = argparse.ArgumentParser(description="CYBERMIND one-command train pipeline")
    ap.add_argument("--config", default="configs/gb10_full.yaml")
    ap.add_argument("--source", default="CIC-IDS2018", choices=["CIC-IDS2018"])
    ap.add_argument("--download-cic2018", dest="download_cic2018", action="store_true", default=True, help="Download full public CIC-IDS2018 bucket automatically if raw data is absent")
    ap.add_argument("--no-download-cic2018", dest="download_cic2018", action="store_false", help="Disable automatic CIC-IDS2018 download")
    ap.add_argument("--skip-baseline", action="store_true")
    ap.add_argument("--skip-prep", action="store_true", help="Use existing tensors in the config's processed_dir")
    ap.add_argument("--resume", default="", help="Checkpoint path to resume training from")
    ap.add_argument("--epochs", type=int, default=0, help="Override config epochs; useful for smoke/validation runs")
    ap.add_argument("--train-only", action="store_true", help="Assume data is ready; run GPU check + training only")
    args = ap.parse_args()
    cfg_path = ROOT / args.config
    if not cfg_path.exists():
        raise SystemExit(f"Config not found: {cfg_path}")
    cfg = load_yaml(cfg_path)
    processed = cfg['data']['processed_dir']

    for d in (ROOT / 'checkpoints', ROOT / 'export', ROOT / 'models', ROOT / 'results', ROOT / 'data' / 'intermediate', ROOT / processed):
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("CYBERMIND — AUTOMATED TRAINING LAUNCHER")
    print("Everything up to model training is automated; training is the heavy step.")
    print("=" * 72)

    if not args.train_only:
        ensure_data(args.source, download=args.download_cic2018)
        normalize(args.source)
        run([PYTHON, "scripts/validate_dataset.py", "--input", "data/intermediate/CIC-IDS2018", "--strict"])
        if not args.skip_prep:
            run([PYTHON, "scripts/prepare_data.py", "--config", args.config, "--input", "data/intermediate/CIC-IDS2018", "--strict"])
        if not prepared(processed):
            raise SystemExit("Processed train/val/test files are missing or empty.")
    # Full preflight validates prepared data as well as the GPU, so run it after
    # preparation and before any baseline or model training.
    check_gpu(args.config)
    if not args.train_only:
        if not args.skip_baseline:
            run([PYTHON, "scripts/run_baseline.py", "--processed", processed, "--split", "val"])
            run([PYTHON, "scripts/run_baseline.py", "--processed", processed, "--split", "test"])

    train_cmd = [PYTHON, "scripts/train.py", "--config", args.config]
    if args.resume:
        train_cmd += ["--resume", args.resume]
    if args.epochs:
        train_cmd += ["--epochs", str(args.epochs)]
    run(train_cmd)

    ckpt = ROOT / "checkpoints" / cfg["train"]["checkpoint"]
    if not ckpt.exists():
        raise SystemExit(f"Training completed but checkpoint not found: {ckpt}")
    for split in ("val", "test"):
        run([PYTHON, "scripts/eval.py", "--config", args.config, "--checkpoint", str(ckpt), "--split", split])
    # Export and verify the teacher ONNX immediately after training.
    run([PYTHON, "scripts/export_teacher_onnx.py", "--config", args.config, "--checkpoint", str(ckpt),
         "--output", "export/cybermind_teacher_fp16.onnx"])
    package_run(time.strftime("%Y%m%d_%H%M%S"), args.config)
    print("\nTRAINING PIPELINE COMPLETE — checkpoint + evaluation artifacts are ready.")


if __name__ == "__main__":
    main()
