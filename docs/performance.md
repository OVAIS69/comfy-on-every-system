# Performance

Everything below was measured on one machine. Treat the absolute numbers as a reference point and
the **ratios** as the transferable part.

Reference machine:

```
GPU   RTX 4050 Laptop, 6.0 GB VRAM, sm_89
CPU   AMD Ryzen 7 7435HS
RAM   15.8 GB
OS    Windows 11 Home
ComfyUI 0.46.0 · torch 2.14.1+cu130 · Python 3.13
```

Method: wall-clock from `POST /prompt` to a successful `/history` entry, GPU idle before the run,
`--reserve-vram 0.2`, `--preview-method none`. Sampling time comes from the per-step timestamps in
the ComfyUI log. One run per configuration, not averaged.

---

## Resolution

Wan 2.2 TI2V-5B Turbo, **81 frames**, **4 steps**, CFG 1.

| Resolution | Pixels | Total (measured) | Ratio |
| --- | --- | --- | --- |
| 512x288 | 147k | **88 s** | 0.52x |
| **704x480** | **338k** | **152-174 s** | **1.00x** |
| 832x480 | 399k | 293-296 s | 1.8x |

Two things stand out:

- 512x288 is ~40% faster than 704x480 and still coherent. Good for prompt iteration; too soft for
  a deliverable.
- 832x480 costs **1.8x** the time of 704x480 for only **+18%** pixels. That is not a smooth
  curve: at 832x480 the activation footprint plus the resident UNet crosses the 6 GB line, so
  per-step time jumps from ~4.5 s to roughly 35-40 s. On 8 GB cards this cliff moves up.

1920x1080 is not on the list because it cannot be sampled here. At 480p the model already uses
5.7 GB; 1080p has 6.4x the pixels, so attention alone needs ~20 GB. Use the two-stage
[1080p graph](workflows.md#4-1080p-output--wan22-turbo-5b-texttovideo-1080p).

Width and height must be multiples of **32**; length should be **4n+1** (81, 49, 33, 17).

---

## Frames

Time scales close to linearly in frame count once the encoder pass is paid:

| Frames | Duration @24 fps | Total | Note |
| --- | --- | --- | --- |
| 49 | 2.0 s | ~60% of 81 | safe on lower VRAM |
| 81 | 3.4 s | 152-174 s | default |
| 121 | 5.0 s | ~1.6x | 6 GB can usually do it at 704x480 |

Above ~121 frames at 480p the latent batch starts to matter; 6 GB is not comfortable there.

---

## Launch flags

Same job: 704x480, 81 frames, 4 steps.

| Flags | Total | Sampling | Peak VRAM |
| --- | --- | --- | --- |
| `--lowvram --reserve-vram 0.4` | 362 s | 98 s (24.7 s/step) | 3.8 GB |
| `--reserve-vram 0.2` | **152 s** | **17 s (4.5 s/step)** | 5.7 GB |

`--lowvram` is the intuitive choice on a small card and it is **2.4x slower** here. It keeps the
UNet partly in system RAM, so every block is copied back and forth over PCIe every step, and the
text-encoder pass also runs slower under memory pressure. The machine is fastest when the UNet is
fully resident and the encoder is the thing that streams.

What not to use:

- `--highvram` / `--gpu-only`: OOM. The UNet (3.4 GB) plus the dequantised encoder (4.66 GB)
  exceed 6 GB.
- `--lowvram` unless you are actually OOMing.
- Preview methods other than `none`: they decode latents every step and steal VRAM.

---

## Where the time goes

At 704x480 / 81 frames / 4 steps, total ~152 s. Sampling is 18 s of that; the rest is almost
entirely the text-encoder pass:

| Stage | Time | Share |
| --- | --- | --- |
| Text encoder (umt5-xxl, CPU) | ~115-125 s (derived) | **75-80%** |
| Sampling (4 steps x 4.5 s) | 18 s | 12% |
| VAE decode + h264 encode | ~10 s | 7% |

The encoder is the bottleneck, not the video model. It is 4.66 GB dequantised and does not fit
next to the UNet, so ComfyUI streams it from RAM on every prompt. On a 3.4 s clip there is no
amortisation: the fixed cost dominates.

That fixed cost is not constant: at 512x288 the same pass runs in roughly 65-75 s because the
UNet leaves more VRAM free for the encoder to stream into. At 704x480 it grows to ~2 minutes.
The number that matters is **VRAM headroom**, not resolution.

Consequences:

- **Reusing a prompt does not help** - ComfyUI re-encodes unless the conditioning is cached as a
  node output.
- **More frames are cheap, more prompts are expensive.** Batching several clips from one prompt
  (batch size > 1) shares the encode.
- **A smaller encoder is the single biggest win.** `umt5-xxl-encoder-Q3_K_M.gguf` is ~2.7 GiB and
  should cut the pass by ~40%, with a small quality cost.

---

## Character swap (VACE 1.3B)

704x480, **33 frames**, **20 steps**, CFG 6, `uni_pc` / `simple`:

| Metric | Value |
| --- | --- |
| Total | **~300 s** |
| Per step | 11.1 s |
| Sampling | ~222 s |
| Peak VRAM | ~4.5 GB |

VACE 1.3B is *slower per step than the 5B Turbo model* (11.1 s vs 4.5 s) despite being smaller.
It carries two extra control latents, is not distilled, and runs at CFG 6 (which doubles the
effective batch through the model). 81 frames will be roughly 2-2.5x this.

Cheap wins:

1. **CausVid LoRA** `Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors` at strength ~0.7,
   4 steps, CFG 1 -> roughly **60-80 s**. Some motion quality loss.
2. **33 frames at 16 fps** is already 2 s of video; do not reach for 81 unless you need it.
3. Drop `strength` to 0.8 if you can: slightly fewer control tokens resolved per step.

---

## Upscaling to 1080p

The 4x RRDBNet pass (UltraSharp) is tiled at 256 px with 24 px overlap. It runs on the GPU in
fp16 and is not part of the model's VRAM budget: it peaks well under 1 GB at 480p input.

It is not benchmarked here end-to-end in the ComfyUI graph. As a rule of thumb, expect the upscale
to cost less than the sampling stage and to be dominated by the h264 encode at 1920x1080. If you
need a number before committing, run `scripts/faceswap/upscale_video.py` on any existing clip: it
prints frames/second.

---

## Tuning cheatsheet

| Goal | Do this |
| --- | --- |
| Faster iteration | 512x288, 49 frames, 4 steps |
| Better motion | 704x480, 6-8 steps, `uni_pc` |
| Longer clip | raise frames to 121, keep 704x480 |
| More detail | 4x upscale instead of raising resolution |
| Less VRAM | `--lowvram` (slow) or 640x384 |
| Faster prompts | smaller encoder quant, close GPU apps |

The recurring mistake is paying for resolution. Two 480p renders and a separate upscale beat one
832x480 render on this hardware, in both time and quality.
