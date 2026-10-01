# Colab T4 final output

The canonical trained model is `models/cybermind_final.pt`. It contains the compact single-model weights and architecture metadata, without optimizer state.

`checkpoints/cybermind_compact.pt` is the resumable training checkpoint.

`export/cybermind_compact.onnx` is optional deployment output. The training pipeline does not discard the `.pt` model if ONNX export cannot be performed in the current runtime.
