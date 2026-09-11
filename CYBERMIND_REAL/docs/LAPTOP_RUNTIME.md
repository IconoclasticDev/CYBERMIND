# CYBERMIND Portable Laptop Runtime

The lab teacher is trained on the high-capacity GPU. The exported student is the presentation/runtime model.

## Runtime target
- <= 6 GB VRAM when CUDA is used
- CPU fallback when CUDA is unavailable
- batch size 1 by default
- FP16 PyTorch option and INT8 ONNX option
- no cloud/API dependency during inference
- model file is allowed to be up to 1 GB; the hard requirement is the runtime memory budget, not an artificial file-size cap

## Build on the lab rig
`python scripts/distill_student.py --train-data data/processed/train.pt --output models/cybermind_student_quant.onnx`

## Run on a presentation laptop
`python scripts/laptop_infer.py --model models/cybermind_student_quant.onnx`

The runtime prefers ONNX Runtime CPU for maximum portability. If a CUDA-capable ONNX provider is available, use `--provider cuda`; the script refuses CUDA execution when the reported device VRAM is above the configured 6 GB safety budget unless `--allow-over-6gb` is explicitly supplied.

The portable student is a deployment surrogate, not the research teacher. Report teacher metrics separately from student runtime metrics.
