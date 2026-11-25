"""Convert an ESRGAN .pth checkpoint to safetensors for ComfyUI's UpscaleModelLoader.

Usage:
    python convert_upscaler.py in.pth out.safetensors
"""
import sys

import torch
from safetensors.torch import save_file


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]

    sd = torch.load(src, map_location="cpu")
    if isinstance(sd, dict) and "state_dict" in sd:
        sd = sd["state_dict"]
    if not isinstance(sd, dict):
        raise SystemExit("unexpected checkpoint format in " + src)

    # ESRGAN checkpoints often carry a params_ema./params. prefix; strip it so the
    # file looks like a plain state dict, which is what ComfyUI expects.
    for prefix in ("params_ema.", "params."):
        if any(k.startswith(prefix) for k in sd):
            sd = {k[len(prefix):] if k.startswith(prefix) else k: v for k, v in sd.items()}
            break

    out = {k: v.detach().contiguous().float() for k, v in sd.items()
           if isinstance(v, torch.Tensor)}
    save_file(out, dst)
    print(f"wrote {dst}: {len(out)} tensors")


if __name__ == "__main__":
    main()
