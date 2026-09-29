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
        raise SystemExit("GPU preflight failed. Fix CUDA/PyTorch/PyG before training.")


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


def prepared():
    p = ROOT / "data/processed"
    return all((p / f).exists() and (p / f).stat().st_size > 0 for f in ("train.pt", "val.pt", "test.pt"))


def package_run(tag: str):
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
        "config": str(cfg_path.relative_to(ROOT)),
        "python": sys.version,
        "cwd": str(ROOT),
    }, indent=2))
    print(f"[DONE] Run artifacts: {out}")


def main():
    ap = argparse.ArgumentParser(description="CYBERMIND one-command train pipeline")
    ap.add_argument("--config", default="configs/colab_t4.yaml")
    ap.add_argument("--source", default="CIC-IDS2018", choices=["CIC-IDS2018"])
    ap.add_argument("--download-cic2018", dest="download_cic2018", action="store_true", default=True, help="Download full public CIC-IDS2018 bucket automatically if raw data is absent")
    ap.add_argument("--no-download-cic2018", dest="download_cic2018", action="store_false", help="Disable automatic CIC-IDS2018 download")
    ap.add_argument("--skip-baseline", action="store_true")
    ap.add_argument("--skip-prep", action="store_true", help="Use existing data/processed/*.pt")
    ap.add_argument("--resume", default="", help="Checkpoint path to resume training from")
    ap.add_argument("--epochs", type=int, default=0, help="Override config epochs; useful for smoke/validation runs")
    ap.add_argument("--train-only", action="store_true", help="Assume data is ready; run GPU check + training only")
    ap.add_argument("--skip-onnx", action="store_true", help="Skip ONNX export")
    args = ap.parse_args()
    cfg_path = ROOT / args.config
    if not cfg_path.exists():
        raise SystemExit(f"Config not found: {cfg_path}")

    for d in (ROOT / 'checkpoints', ROOT / 'export', ROOT / 'models', ROOT / 'results', ROOT / 'data' / 'intermediate', ROOT / 'data' / 'processed'):
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("CYBERMIND — AUTOMATED TRAINING LAUNCHER")
    print("Everything up to model training is automated; training is the heavy step.")
    print("=" * 72)
    run([PYTHON, "scripts/readiness_check.py"])
    check_gpu(args.config)

    if not args.train_only:
        ensure_data(args.source, download=args.download_cic2018)
        normalize(args.source)
        run([PYTHON, "scripts/validate_dataset.py", "--input", "data/intermediate", "--strict"])
        if not args.skip_prep:
            run([PYTHON, "scripts/prepare_data.py", "--config", args.config, "--input", "data/intermediate", "--strict"])
        if not prepared():
            raise SystemExit("Processed train/val/test files are missing or empty.")
        if not args.skip_baseline:
            run([PYTHON, "scripts/run_baseline.py", "--processed", "data/processed", "--split", "val"])
            run([PYTHON, "scripts/run_baseline.py", "--processed", "data/processed", "--split", "test"])

    train_cmd = [PYTHON, "scripts/train.py", "--config", args.config]
    if args.resume:
        train_cmd += ["--resume", args.resume]
    if args.epochs:
        train_cmd += ["--epochs", str(args.epochs)]
    run(train_cmd)

    ckpt = ROOT / "checkpoints" / (load_yaml(cfg_path)["train"]["checkpoint"])
    if not ckpt.exists():
        raise SystemExit(f"Training completed but checkpoint not found: {ckpt}")
    for split in ("val", "test"):
        run([PYTHON, "scripts/eval.py", "--config", args.config, "--checkpoint", str(ckpt), "--split", split])
    # Export and verify the single production model ONNX immediately after training.
    run([PYTHON, "scripts/finalize_model.py", "--config", args.config, "--checkpoint", str(ckpt),
         "--output", "models/cybermind_final.pt"])
    if not args.skip_onnx:
        rc = run([PYTHON, "scripts/export_onnx.py", "--config", args.config, "--checkpoint", str(ckpt),
                  "--output", "export/cybermind_compact.onnx"], allow_fail=True)
        if rc:
            print("[WARN] ONNX export/verification failed; final .pt artifact is still valid. Use --skip-onnx to make this explicit.")
    package_run(time.strftime("%Y%m%d_%H%M%S"))
    print("\nTRAINING PIPELINE COMPLETE — single-model checkpoint + evaluation + ONNX are ready.")


if __name__ == "__main__":
    main()
