"""Bounded synthetic training check; does not measure cybersecurity accuracy."""
import argparse
import gc
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "CYBERMIND_REAL"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import psutil
import torch
import yaml
from cybermind.data.types import GraphState, GraphSequenceSample
from cybermind.models.world_model import WorldModel
from cybermind.models.graph_encoder import HAS_PYG
from train import batch_loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=32)
    args = parser.parse_args()
    cfg = yaml.safe_load((ROOT / "configs/gpu_128gb.yaml").read_text())
    torch.manual_seed(42)
    torch.set_num_threads(4)
    device = torch.device("cuda")
    model = WorldModel(14, **cfg["model"]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["train"]["lr"])
    scaler = torch.amp.GradScaler("cuda")
    batch = []
    for i in range(cfg["train"]["batch_size"]):
        states = []
        for t in range(cfg["data"]["history"]):
            edges = torch.randint(args.nodes, (2, args.nodes * 4))
            states.append(GraphState(
                torch.rand(args.nodes, 14), edges, torch.rand(edges.shape[1], 7),
                [f"host-{j}" for j in range(args.nodes)], float(t * 30),
                float(i % 2 == 0 and t >= 8), (2 if i % 2 == 0 and t >= 8 else 0),
                f"synthetic-{i}", "SYNTHETIC", {"synthetic": True},
            ))
        batch.append(GraphSequenceSample(states, f"synthetic-{i}", 0, 60, {"synthetic": True}))
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    losses = []
    try:
        model.train()
        for step in range(cfg["train"]["grad_accumulation"]):
            with torch.amp.autocast("cuda"):
                loss, components = batch_loss(model, batch, cfg, device)
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite training loss")
            losses.append(float(loss.detach()))
            scaler.scale(loss / cfg["train"]["grad_accumulation"]).backward()
        scaler.unscale_(optimizer)
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg["train"]["grad_clip"])
        if not torch.isfinite(grad_norm):
            raise RuntimeError("Non-finite gradients")
        scaler.step(optimizer)
        scaler.update()
        torch.cuda.synchronize()
        status = "passed"
        error = None
    except torch.cuda.OutOfMemoryError as exc:
        status, error = "out_of_memory", str(exc)
    result = {
        "status": status, "error": error, "synthetic_only": True,
        "python": sys.version.split()[0], "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(), "pyg_backend": HAS_PYG,
        "ram_gib": psutil.virtual_memory().total / 1024**3,
        "available_ram_gib": psutil.virtual_memory().available / 1024**3,
        "gpu_vram_gib": torch.cuda.get_device_properties(0).total_memory / 1024**3,
        "nodes_per_graph": args.nodes, "edges_per_graph": args.nodes * 4,
        "history": cfg["data"]["history"], "batch_size": cfg["train"]["batch_size"],
        "gradient_accumulation": cfg["train"]["grad_accumulation"],
        "parameters": sum(p.numel() for p in model.parameters()),
        "peak_allocated_gib": torch.cuda.max_memory_allocated() / 1024**3,
        "peak_reserved_gib": torch.cuda.max_memory_reserved() / 1024**3,
        "elapsed_seconds": time.perf_counter() - start, "losses": losses,
    }
    out = ROOT.parent / f"probe_{args.nodes}_nodes.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
