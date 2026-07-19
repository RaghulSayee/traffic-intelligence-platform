import torch


def resolve_inference_device(
    requested_device: str,
) -> str:
    """
    Resolve the best available inference device.

    Resolution order for "auto":
    1. Apple Metal Performance Shaders
    2. NVIDIA CUDA
    3. CPU
    """

    normalized_device = requested_device.strip().lower()

    if normalized_device != "auto":
        return normalized_device

    if torch.backends.mps.is_built() and torch.backends.mps.is_available():
        return "mps"

    if torch.cuda.is_available():
        return "0"

    return "cpu"
