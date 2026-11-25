# Hardware

## TL;DR

| VRAM | Verdict | Configuration |
| --- | --- | --- |
| 4 GB | works, slow | 5B `Q3_K_M`, `Q3_K_M` encoder, 512x288, `--lowvram` |
| **6 GB** | **this repo, measured** | 5B `Q4_K_M`, `Q4_K_M` encoder on CPU, 704x480 |
| 8 GB | comfortable | 5B `Q5_K_M`/`Q6_K`, 704-832x480, maybe encoder on GPU |
| 12 GB | good | 5B `Q8_0`, 832x480, 121 frames, encoder on GPU |
| 16 GB | no compromises at 480p | 5B `Q8_0`, encoder on GPU, ~45-70 s/clip |
| 24 GB | different class | 14B `Q4_K_M`/fp8, 720p, VACE 14B |

Only the 6 GB row is measured. The rest are extrapolations from the VRAM math below; treat them
as a starting point, not a benchmark.

---

## What actually consumes VRAM

```
UNet weights                 Q4_K_M 5B  -> 3.36 GB resident
sampling activations         704x480    -> 1.3-1.6 GB
VAE decode (fp16, tiled)                -> 0.5-0.8 GB
latents (81 frames)                     -> ~0.01 GB
desktop / driver reserve                -> 0.3 GB
```

Peak measured: **5.7 GB of 6.0 GB**. The rule of thumb for this model family is:

> **VRAM needed ≈ 1.6-1.7x the on-disk quant size at 480p**, before the text encoder.

The text encoder is a separate problem. umt5-xxl dequantises to ~4.66 GB. It *can* run on the GPU
when free VRAM allows, but on 6 GB it never does, so it streams from system RAM. That is why RAM
matters as much as VRAM for this workload.

Resolution scales the activation term roughly quadratically. 832x480 does not fit the 6 GB budget,
which is exactly why it is 1.8x slower rather than 1.18x.

---

## By VRAM tier

### 4 GB — GTX 1650, RTX 3050 laptop 4 GB, RX 6400

Use the smallest viable quants:

- `Wan22-Turbo-Q3_K_M.gguf` (~2.7 GiB) or Q3_K_S
- `umt5-xxl-encoder-Q3_K_M.gguf` (~2.7 GiB)
- 512x288, 33-49 frames
- `--lowvram --reserve-vram 0.3`

Expect several minutes per clip. VACE 1.3B Q5 will run; 480p will not.

### 6 GB — the reference machine

The configuration in this repo: Q4_K_M 5B, Q4_K_M encoder on CPU, 704x480, 81 frames, ~2.5 min.
Full details in [performance.md](performance.md).

Laptop-specific notes that made a measurable difference here:

- **Plug in the charger.** On battery the GPU clocks drop and sampling roughly doubles.
- Set the vendor control panel to the performance profile and raise the TGP if the model allows it.
- Close Chrome/Discord/Steam/Spotify. Hardware-accelerated browsers hold 0.5-1.5 GB of VRAM, which
  is the difference between the fast and the `--lowvram` path.
- 16 GB RAM is the practical floor. If the machine has 16 GB, keep the pagefile on an SSD at
  system-managed size; ComfyUI will touch it during the encoder pass.

### 8 GB — RTX 3060 Ti, 4060, 3070 laptop

- `Q5_K_M` or `Q6_K` 5B, `Q4_K_M` encoder.
- 704x480 is comfortable; 832x480 becomes viable.
- Try the encoder on the GPU only if you see the log line about it loading fully. If not, leave it
  on the CPU; a partial offload is slower than a clean CPU pass.
- VACE 1.3B Q8 at 704x480 with 49-81 frames is fine.

### 12 GB — RTX 3060 12 GB, 4070, 4070 Ti

- 5B `Q8_0` for the model, `Q8_0` encoder on the GPU.
- 832x480, 121 frames.
- Expect the encoder pass to stop being the bottleneck: sampling becomes the majority of the time.
- Wan 2.1 VACE 1.3B is fully comfortable; the 14B VACE is still out of reach.

### 16 GB — RTX 4060 Ti 16 GB, 4070 Ti Super, 4080

- Everything at 480p is fast (~45-70 s/clip), including 832x480 and longer clips.
- Wan 2.2 14B at Q4_K_M starts to be possible with ComfyUI's block offload, at 480p. Not tested
  here; budget 2-4x the 5B time and expect to tune `--reserve-vram`.

### 24 GB — RTX 3090, 4090

- Wan 2.2 14B fp8/GGUF at 720p, VACE 14B, Wan Animate 14B.
- This is where the "character swap that actually looks like the person" tier begins.
- The 5B setup still wins on iteration speed.

---

## Non-NVIDIA GPUs

### AMD (Windows)

ComfyUI does not ship ROCm for Windows. The working options are:

- **ComfyUI-Zluda** (a fork with a ZLUDA CUDA shim). GGUF nodes work; expect 20-50% lower
  throughput than an equivalent NVIDIA card and occasional kernel fallbacks.
- **DirectML** (`torch-directml`). Works, but fp16 support is patchy and GGUF dequantisation in
  ComfyUI-GGUF may fall back to CPU. Slower than Zluda in most reports.

### AMD (Linux)

ROCm works with recent torch builds (`--index-url https://download.pytorch.org/whl/rocm6.x`).
The launcher flags are the same; `--reserve-vram` behaves differently because the allocator is not
CUDA's. Start with `--lowvram` on 8 GB AMD cards.

### Intel Arc

IPEX-LLM and the Vulkan backend both run ComfyUI. Untested with this model set. The GGUF loader
requires the dequant kernels to be available for the backend; if they are not, the model loads but
sampling crawls.

### Apple Silicon

MPS works. Allocate more unified memory to the GPU in recent macOS, use 512x288 and 49 frames.
Expect 5-10x the sampling time of a 6 GB RTX 4050. VACE is possible; the face-swap ONNX path runs
on CPU via onnxruntime and is fine.

### CPU only

Technically possible, practically not. Sampling a 5B video model on a desktop CPU is 50-100x
slower than a 6 GB GPU. Use a cloud GPU instead.

---

## RAM and storage

| RAM | Experience |
| --- | --- |
| 8 GB | will thrash; the encoder alone needs 4.66 GB |
| 16 GB | works, encoder pass touches the pagefile |
| 32 GB | smooth; the encoder stops competing with Windows |
| 64 GB | no benefit for this model |

Storage: ~9 GB of models, ~1.5 GB ComfyUI, plus outputs. An NVMe SSD mainly helps the first load
of a model after a restart; sampling reads from VRAM.

---

## Cloud, if you need 1080p or 14B

A single 24 GB GPU rents for roughly 0.3-0.8 USD per hour, and a 480p clip takes ~1 minute there.
That is cheaper than upgrading hardware if you only need occasional 1080p or a proper VACE 14B
character swap. The same workflows and model files work unchanged; only the launch flags change
(no `--reserve-vram` needed).

Do not rent a 6 GB instance: you would reproduce this repo's constraints with worse disk I/O.
