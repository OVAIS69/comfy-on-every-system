# Models

Six files, ~9 GB. Everything is a quantised repack of an Apache-2.0 Wan checkpoint, plus one
upscaler. Nothing in this repo requires gated access or an API key.

## What to download

| Local filename | Folder under `ComfyUI/models/` | Size | Role | Source |
| --- | --- | --- | --- | --- |
| `Wan22-Turbo-Q4_K_M.gguf` | `diffusion_models` | 3.28 GiB | main video model (Wan 2.2 TI2V-5B Turbo, Q4_K_M) | [hum-ma/Wan2.2-TI2V-5B-Turbo-GGUF](https://huggingface.co/hum-ma/Wan2.2-TI2V-5B-Turbo-GGUF) |
| `Wan21-VACE-1.3B-Q8_0.gguf` | `diffusion_models` | 2.14 GiB | character swap (Wan 2.1 VACE 1.3B, Q8_0) | [calcuis/wan-gguf](https://huggingface.co/calcuis/wan-gguf) file `wan2.1-v4-vace-1.3b-q8_0.gguf` |
| `umt5-xxl-encoder-Q4_K_M.gguf` | `text_encoders` | 3.40 GiB | text encoder | [city96/umt5-xxl-encoder-gguf](https://huggingface.co/city96/umt5-xxl-encoder-gguf) |
| `wan2.2_vae.safetensors` | `vae` | 1.31 GiB | VAE for Wan 2.2 | [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged) |
| `wan_2.1_vae.safetensors` | `vae` | 242 MiB | VAE for Wan 2.1 VACE | [Comfy-Org/Wan_2.1_ComfyUI_repackaged](https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged) |
| `4x-UltraSharp.safetensors` | `upscale_models` | 64 MiB | 4x ESRGAN upscaler for the 1080p path | [lokCX/4x-Ultrasharp](https://huggingface.co/lokCX/4x-Ultrasharp) (`.pth`) |

### Direct URLs

```
https://huggingface.co/hum-ma/Wan2.2-TI2V-5B-Turbo-GGUF/resolve/main/Wan2_2-TI2V-5B-Turbo-Q4_K_M.gguf
https://huggingface.co/calcuis/wan-gguf/resolve/main/wan2.1-v4-vace-1.3b-q8_0.gguf
https://huggingface.co/city96/umt5-xxl-encoder-gguf/resolve/main/umt5-xxl-encoder-Q4_K_M.gguf
https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors
https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors
https://huggingface.co/lokCX/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth
```

The two GGUF files are renamed locally. The workflows reference the short names above; if you keep
the upstream names, either rename them or re-point the loader nodes (`UnetLoaderGGUF` is a dropdown,
so it is one click per graph).

`4x-UltraSharp` ships as `.pth`. ComfyUI can load `.pth` directly, but the bundled workflows use
`.safetensors`. `scripts/download_models.ps1` converts it for you:

```python
from safetensors.torch import load_file, save_file
save_file(load_file("4x-UltraSharp.pth"), "4x-UltraSharp.safetensors")
```

## Why these quants

The unquantised 5B model is ~10 GB and does not fit. The quantisation trade here is simple:

| File | Disk | Dequantised on GPU | Verdict |
| --- | --- | --- | --- |
| `Q4_K_M` 5B | 3.28 GiB | ~3.4 GB | fits with latents and VAE headroom; this is the build |
| `Q5_K_M` 5B | ~3.9 GiB | ~4.0 GB | only with the encoder already off the GPU; ~10-15% better detail |
| `Q8_0` 5B | ~5.4 GiB | ~5.5 GB | does not fit on 6 GB once activations and VAE are counted |
| `Q3_K_M` 5B | ~2.7 GiB | ~2.8 GB | for 4 GB cards; visibly softer |

For the encoder, `Q4_K_M` is deliberate: the dequantised umt5-xxl is ~4.66 GB in fp16, and on a
6 GB card it cannot live next to the UNet. `Q4_K_M` keeps the CPU pass at 60-120 s.
`Q3_K_M` (~2.7 GiB) is the next step down if you want to try putting it on the GPU.

The VACE model is 1.3B, so `Q8_0` is affordable (2.14 GiB) and preserves the conditioning quality
that makes the swap work. Do not go below Q5 for VACE.

## Where the VRAM goes (measured)

At 704x480 / 81 frames / Q4_K_M on a 6 GB 4050:

```
UNet weights (Q4_K_M, resident)          ~3.4 GB
Attention + activations during sampling  ~1.5 GB
Latents (81 frames -> 21 latent frames)  ~0.01 GB
VAE decode spike                         ~0.5-0.8 GB
display / Windows compositor             ~0.3 GB
--------------------------------------------------
peak observed                            ~5.7 GB of 6.0 GB
```

The text encoder is *not* in this budget: it runs on the CPU and its peak RSS is ~4.66 GB of
system RAM. That is also why 16 GB of RAM is the practical minimum.

## Alternate model sets by VRAM

Estimates unless marked measured. See [hardware.md](hardware.md) for the full table.

| VRAM | Diffusion model | Encoder | Practical resolution |
| --- | --- | --- | --- |
| 4 GB | 5B `Q3_K_M` | `Q3_K_M` | 512x288, 49 frames |
| **6 GB** | **5B `Q4_K_M`** | **`Q4_K_M` on CPU** | **704x480, 81 frames (this repo)** |
| 8 GB | 5B `Q5_K_M` / `Q6_K` | `Q4_K_M`, may fit on GPU | 704x480-832x480 |
| 12 GB | 5B `Q8_0` | `Q8_0` | 832x480 with room for 121 frames |
| 16 GB+ | Wan 2.2 14B `Q4_K_M` | `Q8_0` | 720p, still with offload |

## Licenses

- **Wan 2.1 / 2.2 weights**: Apache-2.0, © Alibaba.
- **umt5-xxl encoder**: Apache-2.0 (Google); GGUF conversion © city96.
- **VAE repacks**: derived from the Apache-2.0 Wan checkpoints; repackaging by Comfy-Org.
- **4x-UltraSharp**: by Kim2091; check the model card before commercial use.
- **Face-swap ONNX models**: see [faceswap.md](faceswap.md). `inswapper_128` is research-use only.

Nothing here grants rights to likenesses or voices of real people. Do not use the face-swap path
on someone who has not consented.
