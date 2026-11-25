# Troubleshooting

## Read the log first

ComfyUI prints the useful part of every run to the console. On the portable build that is the
window opened by `run_comfyui.bat` (and `comfyui.err.log` if you launch it detached). The lines
that matter:

```
Requested to load WanTEModel
loaded completely 4660.0 4660.0 True          <- encoder is on the GPU
loaded partially 5120.0 4999.0 0              <- something is offloading
Using pytorch attention
```

`loaded partially` on the text encoder is normal on 6 GB. `loaded partially` on the UNet is the
slow path: you are in `--lowvram` or another app is holding VRAM.

---

## CUDA out of memory

```
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 1.2 GiB...
```

Work down this list in order; each step costs less quality than the one after it.

1. Close GPU-using apps (browser, Discord, Steam, Spotify, NVIDIA overlay). This alone recovers
   0.5-1.5 GB.
2. Lower resolution: 704x480 -> 640x384 -> 512x288. Keep multiples of 32.
3. Lower frame count: 81 -> 49 -> 33 (keep 4n+1).
4. Add `--reserve-vram 0.3` (it reserves more for the desktop, less for the model).
5. Switch to `scripts\run_comfyui_lowvram.bat`. Expect ~2.4x slower, but it peaks around 3.8 GB.
6. Reduce `batch_size` to 1 (it already is in the bundled graphs).

If it OOMs during **VAE decode**, not sampling, the fix is different: decode in tiles. The bundled
graphs use the default decode. Lowering frames is the quickest workaround; a tiled-decode node is
the proper one.

If it OOMs only at **832x480**, that is expected. See [performance.md](performance.md): that
resolution crosses the 6 GB line and is not worth it.

---

## A model does not appear in the dropdown

ComfyUI scans model folders **once at startup**. After copying files in, restart the server.

If it is still missing:

| Symptom | Cause |
| --- | --- |
| `.gguf` not listed under `UnetLoaderGGUF` | file is in `models/checkpoints` instead of `models/diffusion_models` |
| No `UnetLoaderGGUF` node at all | ComfyUI-GGUF is not installed or failed to import; check the startup traceback |
| `.safetensors` missing from `VAELoader` | wrong subfolder; VAEs go in `models/vae` |
| `4x-UltraSharp` missing | must be in `models/upscale_models`; `.pth` is also accepted |

A workflow that references a missing file opens with a red node and the error
`Value not in list: unet_name: '...'`. That is the same problem: the file name does not match.

---

## Workflow opens with red / missing nodes

The JSON uses `UnetLoaderGGUF` and `CLIPLoaderGGUF`, which come from
[ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF). Install it and its requirements into the
**portable** Python, then restart:

```powershell
git clone --depth 1 https://github.com/city96/ComfyUI-GGUF.git `
    .\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-GGUF
.\ComfyUI_windows_portable\python_embeded\python.exe -m pip install `
    -r .\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-GGUF\requirements.txt
```

`ModuleNotFoundError: No module named 'gguf'` means the pip step ran against a different Python.

---

## "Install missing models" wants 50 GB

Do not click it. The template metadata points at full-precision safetensors (5B fp16 ~10 GB, 14B
fp16 28-60 GB). This repo deliberately replaces those loaders with GGUF nodes. If a template
nags about missing models, close the template browser and open one of the four graphs in
`workflows/` instead.

---

## Video is black, grey, or wildly discoloured

Almost always a **VAE mismatch**:

- Wan 2.2 graphs -> `wan2.2_vae.safetensors`
- Wan 2.1 VACE graph -> `wan_2.1_vae.safetensors`

Using the 2.2 VAE on the 2.1 VACE model (or the reverse) decodes to noise or a flat frame. The
VACE graph intentionally loads the 2.1 VAE.

Other causes:

- **All frames identical / frozen:** the sampler ran with `denoise` below 1 on an empty latent, or
  steps were set to 0. Use 4 steps (Turbo) or 20 (VACE) and denoise 1.0.
- **Oversaturated / crushed contrast:** the model card suggests scaling the latent by ~0.8. Insert
  a `LatentMultiply` (0.8) between `Wan22ImageToVideoLatent` and `KSampler`.
- **One frame of video:** `length` was set to a value that is not 4n+1; the latent trim leaves a
  single frame. Use 81, 49, 33.

---

## It takes forever before sampling starts

Expected on 6 GB. The text encoder is 4.66 GB dequantised, does not fit next to the UNet, and
streams from system RAM. A 704x480 run spends ~2 minutes there before the first sampling step.

What helps:

- Free VRAM (close apps) so ComfyUI can keep more of the encoder resident.
- Use `umt5-xxl-encoder-Q3_K_M.gguf` (~2.7 GiB) for a ~40% shorter pass.
- Reuse one prompt across several seeds rather than editing it every run.

What does not help: `--highvram` or `--gpu-only`. They OOM immediately because 3.4 + 4.66 GB
exceeds 6 GB.

---

## The 1080p graph fails at the upscale step

Select `UpscaleModelLoader` and press **Ctrl+B** to bypass it. The graph falls back to a direct
Lanczos resize to 1920x1080, which uses a fraction of the VRAM. Slightly softer, never fails.

If it fails during **sampling**, you are not running the 1080p graph - check that `ImageScale`
comes after `ImageUpscaleWithModel` and that `Wan22ImageToVideoLatent` is still 864x480. The point
of the graph is that it never samples above 480p.

---

## Character swap: the face is ignored or frozen

- `strength` on `WanVaceToVideo` at 1.0 copies the reference rigidly. Try 0.8-0.9 for motion.
- The reference must be a **single, clear subject**, roughly portrait framing. A wide shot with a
  small face gives the model nothing to condition on.
- `WanVaceToVideo` needs the image in input slot **5** (`reference_image`). A `control_video` is
  optional; empty means a flat gray control clip, which is what the bundled graph relies on.
- 20 steps / CFG 6 is the non-distilled recipe. Turbo settings (4 steps, CFG 1) on VACE produce
  mush.

---

## Face-swap script problems

| Error | Fix |
| --- | --- |
| `cannot read source image` | path has non-ASCII characters, or the file is not a PNG/JPG |
| `no face found in source image` | use a frontal photo, face at least ~150 px wide; YuNet is score-thresholded at 0.5 |
| `ModuleNotFoundError: cv2` | `python_embeded\python.exe -m pip install opencv-python-headless onnxruntime onnx` |
| `onnxruntime` DLL load failed | install the [VC++ 2015-2022 redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe), then reinstall onnxruntime |
| Swap is blurry | `inswapper_128` outputs 128x128; on a 1024 px face that is a hard limit. Upscale after, or accept it |
| Swap does not look like the source | the source is a render/filtered image; inswapper is trained on photographs. Try a real photo |
| Colours look pasted on | lower `--color` (default 0.85) or set 0 |

Details: [faceswap.md](faceswap.md).

---

## PowerShell blocks the scripts

```
... cannot be loaded because running scripts is disabled on this system
```

Run them with an explicit policy, which does not change the machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_models.ps1
```

---

## `--reserve-vram` is not recognised

The flag was added in a 2024 ComfyUI build. Update:

```powershell
cd .\ComfyUI_windows_portable\ComfyUI
..\python_embeded\python.exe -m pip install --upgrade -r requirements.txt
```

or replace the portable install with the current release. Without the flag the 6 GB path still
works, but you lose the protection against Windows spilling VRAM to shared memory.

---

## Video has no audio

`CreateVideo` produces a silent stream. If the source clip had audio, mux it back afterwards:

```powershell
ffmpeg -i video.mp4 -i source.mp4 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest out.mp4
```

`ffmpeg` is bundled inside the portable install under
`ComfyUI_windows_portable\python_embeded\Lib\site-packages\imageio_ffmpeg\binaries\`.

---

## Nothing works: reset the environment

1. Stop ComfyUI.
2. Delete `ComfyUI_windows_portable\ComfyUI\user\default\comfy.settings.json` (UI state only; it
   does not touch models).
3. Restart with `run_comfyui_lowvram.bat` and a minimal graph (512x288, 33 frames, 4 steps).
4. If that fails, check `torch.cuda.is_available()` and the GPU driver before touching the models.
