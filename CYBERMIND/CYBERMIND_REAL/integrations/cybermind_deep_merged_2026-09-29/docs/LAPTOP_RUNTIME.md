# Laptop Runtime

CYBERMIND uses one compact model. There is no teacher/student split. The same final model artifact is intended to run on the RTX 5050/5060 8 GB laptops and on larger rented GPUs.

Target runtime:
- CUDA GPU memory budget: <= 6 GB target
- FP16 for PyTorch execution where supported
- CPU fallback
- ONNX export available for portable CPU/CUDA inference

The 6 GB value is a deployment target/guardrail, not a mathematical guarantee of peak memory on every provider. Benchmark the final artifact on the actual laptop before demos.
