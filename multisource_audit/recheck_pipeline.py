"""Audit only: synthetic fixtures and short subprocess checks, no real benchmarks."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parent / "CYBERMIND_REAL"
ARCHIVE = Path(r"C:\Users\as030\Downloads\CYBERMIND_MULTISOURCE_TRAINING_READY.zip")
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
import psutil
import torch
import yaml
from cybermind.data.types import GraphState, GraphSequenceSample
from cybermind.data.dataset import save_dataset


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report = {"synthetic_only": True, "checks": {}}
    with zipfile.ZipFile(ARCHIVE) as z:
        changed = []
        for entry in z.infolist():
            if entry.is_dir() or "__pycache__" in entry.filename:
                continue
            target = ROOT.parent / entry.filename
            if not target.exists() or target.read_bytes() != z.read(entry):
                changed.append(entry.filename)
    report["archive_sha256"] = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    report["extracted_files_differing_from_archive"] = changed
    if changed:
        raise RuntimeError(f"Extracted source differs from archive: {changed}")
    report["hardware"] = {"ram_gib": psutil.virtual_memory().total / 1024**3,
                          "available_ram_gib": psutil.virtual_memory().available / 1024**3,
                          "gpu": torch.cuda.get_device_name(0)}
    cfg = yaml.safe_load((ROOT / "configs/gpu_128gb.yaml").read_text())
    torch.manual_seed(42)
    samples = []
    for i in range(24):
        states = []
        for t in range(16):
            states.append(GraphState(torch.rand(32, 14), torch.randint(32, (2, 128)),
                torch.rand(128, 7), [f"synthetic-{j}" for j in range(32)], float(30*t),
                float(i % 2 == 0 and t >= 8), 2 if i % 2 == 0 and t >= 8 else 0,
                f"synthetic-{i}", "SYNTHETIC", {"synthetic": True}))
        samples.append(GraphSequenceSample(states, f"synthetic-{i}", 0, 60, {"synthetic": True}))
    for split, values in {"train": samples[:16], "val": samples[16:20], "test": samples[20:]}.items():
        save_dataset(values, ROOT / "data/recheck_synthetic" / f"{split}.pt")
    cfg["data"]["processed_dir"] = "data/recheck_synthetic"
    cfg["train"]["checkpoint"] = "recheck_synthetic.pt"
    config_path = ROOT / "configs/recheck_synthetic.yaml"
    config_path.write_text(yaml.safe_dump(cfg))
    raw = ROOT / "data/recheck_raw"
    raw.mkdir(exist_ok=True)
    for scenario in range(6):
        rows = []
        for t in range(32):
            for host in range(8):
                rows.append({"Timestamp": str(pd.Timestamp("2026-01-01") + pd.Timedelta(days=scenario, seconds=t*60)),
                    "Source IP": f"10.0.0.{host+1}", "Destination IP": f"10.0.0.{(host+1)%8+1}",
                    "Source Port": 40000+host, "Destination Port": 443, "Protocol": 6,
                    "Flow Duration": 1000, "Total Fwd Packets": 10, "Total Backward Packets": 5,
                    "Total Length of Fwd Packets": 1000, "Total Length of Bwd Packets": 500,
                    "Label": "Bot" if scenario % 2 == 0 and t >= 16 else "BENIGN"})
        pd.DataFrame(rows).to_csv(raw / f"synthetic_scenario_{scenario}.csv", index=False)
    prep_cfg = yaml.safe_load(config_path.read_text())
    prep_cfg["data"]["processed_dir"] = "data/recheck_from_csv"
    prep_path = ROOT / "configs/recheck_from_csv.yaml"
    prep_path.write_text(yaml.safe_dump(prep_cfg))
    logs = ROOT.parent / "recheck_logs"
    logs.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONUTF8="1", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4")

    def run(name, args, timeout=180):
        print(f"START {name}", flush=True)
        start = time.perf_counter()
        try:
            result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            output, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as exc:
            output = str(exc.stdout or "") + "\nTIMEOUT"
            code = -1
        (logs / f"{name}.log").write_text(output, encoding="utf-8")
        report["checks"][name] = {"exit_code": code, "seconds": time.perf_counter()-start, "log": str(logs / f"{name}.log")}
        print(f"END {name}: exit={code}\n{output[-1800:]}", flush=True)
        (ROOT.parent / "recheck_report.json").write_text(json.dumps(report, indent=2))
        return code

    run("normalize", ["scripts/build_corpus.py", "--source", "CIC-IDS2018", "--input", str(raw), "--output", "data/recheck_intermediate"])
    run("strict_validation", ["scripts/validate_dataset.py", "--input", "data/recheck_intermediate", "--strict"])
    run("prepare_csv", ["scripts/prepare_data.py", "--config", str(prep_path), "--input", "data/recheck_intermediate", "--strict"])
    report["prepared_sequence_counts"] = {}
    for split in ("train", "val", "test"):
        path = ROOT / "data/recheck_from_csv" / f"{split}.pt"
        report["prepared_sequence_counts"][split] = len(torch.load(path, weights_only=False)) if path.exists() else None
    rc = run("train_one_epoch_stock_workers", ["scripts/train.py", "--config", str(config_path), "--epochs", "1"])
    if rc == 0:
        checkpoint = ROOT / "checkpoints/recheck_synthetic.pt"
        report["checkpoint_bytes"] = checkpoint.stat().st_size
        run("evaluate_checkpoint", ["scripts/eval.py", "--config", str(config_path), "--checkpoint", str(checkpoint)])
        run("plot_rollout", ["scripts/visualize_rollout.py", "--config", str(config_path), "--checkpoint", str(checkpoint)])
    (ROOT.parent / "recheck_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
