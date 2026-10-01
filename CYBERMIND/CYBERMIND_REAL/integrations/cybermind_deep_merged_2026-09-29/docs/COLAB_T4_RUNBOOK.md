# CYBERMIND Colab T4 Runbook

Use `notebooks/08_colab_t4_train.ipynb`. Upload the project ZIP, select an NVIDIA T4 runtime, run the cells, and keep Google Drive persistence enabled for long runs.

The notebook trains one compact CYBERMIND model. It produces:
- `checkpoints/cybermind_compact.pt` — resume checkpoint
- `models/cybermind_final.pt` — final weights-only model artifact
- `export/cybermind_compact.onnx` — deployment/export artifact
- evaluation JSON/history under `results/`

After training, the notebook copies important outputs to `MyDrive/CYBERMIND_FINAL` and downloads `CYBERMIND_FINAL_ARTIFACTS.zip`.

For a disconnect, restore the project and checkpoint from Drive and resume with:

```bash
python scripts/one_click_train.py --config configs/colab_t4.yaml --resume checkpoints/cybermind_compact.pt
```
