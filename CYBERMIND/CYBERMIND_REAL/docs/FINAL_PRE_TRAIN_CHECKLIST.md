# Final pre-training checklist

## Host
- Python/venv ready
- CUDA driver visible
- PyTorch import works
- PyTorch Geometric import works
- GPU has expected VRAM
- FP16/BF16 matrix multiply smoke test passes

## Data
- CIC-IDS2018 raw data present
- source manifest recorded
- normalized corpus present
- endpoint identity available for graph path
- strict validation passes
- train/val/test PT files exist
- scenario/time split recorded
- no random-row leakage

## Model
- GATv2/graph encoder
- temporal Transformer
- latent dynamics
- K-step rollout
- infiltration head
- stage head
- multi-task loss
- mixed precision
- checkpointing

## Evidence
- logistic baseline saved
- 1-epoch real-data sanity run completed
- best checkpoint path known
- evaluation command known
- rollout visualization command known

After these pass, the remaining action is the full production training run.
