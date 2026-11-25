# The workflows

Four graphs live in `workflows/`. They are plain ComfyUI UI-format JSON: copy them into
`ComfyUI/user/default/workflows/`, or drag one onto the canvas.

All four are the same skeleton with different loaders and sampling settings:

```
checkpoint -> model patch -> sampler -> VAE decode -> mp4
prompt -> text encoder --^
optional image / reference -> latent --^
```

The parts that matter are at the edges: which model file, how many frames, how many steps.

---

## 1. Text to video — `Wan2.2-Turbo-5B-TextToVideo`

Status: verified on the 6 GB reference machine (`Wan22_T2V_00002_.mp4`, 704x480, 81 frames).

| Node | Type | Settings |
| --- | --- | --- |
| 37 | `UnetLoaderGGUF` | `Wan22-Turbo-Q4_K_M.gguf` |
| 38 | `CLIPLoaderGGUF` | `umt5-xxl-encoder-Q4_K_M.gguf`, type `wan` |
| 39 | `VAELoader` | `wan2.2_vae.safetensors` |
| 6 | `CLIPTextEncode` | your prompt (positive only) |
| 55 | `Wan22ImageToVideoLatent` | 704 x 480, 81 frames, batch 1 |
| 48 | `ModelSamplingSD3` | shift 8.0 |
| 3 | `KSampler` | 4 steps, CFG 1.0, `euler` / `simple`, denoise 1.0, random seed |
| 8 | `VAEDecode` | - |
| 57 | `CreateVideo` | 24 fps |
| 58 | `SaveVideo` | `video/Wan22_T2V` |

Why it is put together this way:

- **No negative prompt.** With CFG 1.0 the negative conditioning is mathematically ignored, so
  wiring one in only costs a second text-encoder pass (~60 s here). The template ships both;
  this graph drops the negative node.
- **`Wan22ImageToVideoLatent` is used even for text-only.** Wan 2.2 TI2V is a single model for both
  modes; an empty latent with no image is text-to-video.
- **`ModelSamplingSD3` shift 8.0** is what the Turbo recipe expects. Raising it pushes more
  sampling into low noise; 8.0 is a safe default.

### Tweaking

| Knob | Effect |
| --- | --- |
| `length` | frames. Keep it **4n+1** (81, 49, 33) because the VAE compresses time 4x. Time scales almost linearly. |
| `width` / `height` | multiples of **32**. 704x480 is native; 512x288 is the fast draft; 832x480 is a trap on 6 GB. |
| `steps` | 4 for Turbo. 6-8 gives marginal polish at 1.5-2x cost. |
| `cfg` | keep 1.0. Turbo is distilled for CFG 1; higher values burn contrast. |
| sampler | `euler` fastest. `uni_pc` and `sa_solver` are slightly better at equal steps. |
| fps in `CreateVideo` | the graph samples 81 frames then plays them at 24 fps = 3.4 s. Render at 16 fps for a slower, "cinematic" motion. |

---

## 2. Image to video — `Wan2.2-Turbo-5B-GGUF`

Same graph plus a `LoadImage` node (id 56) wired into `Wan22ImageToVideoLatent`, which uses it as
the first frame. Un-bypass the node (Ctrl+B) and pick a file from `ComfyUI/input/`.

This graph is the official ComfyUI template with the GGUF loaders swapped in, so
`build_workflows.py` does not regenerate it; it is shipped as-is.

Differences from graph 1:

- The template's negative `CLIPTextEncode` (id 7) is still present. With CFG 1.0 it changes
  nothing but costs an encode pass. Select it and press **Ctrl+B** to bypass, then re-run; that is
  roughly a minute saved per prompt on a 6 GB card.
- The image is resized to the latent resolution, so a portrait photo in a 704x480 graph is
  cropped/stretched. Match the aspect ratio in the node if it matters.

Prompt it as camera motion, not as a scene description: *"slow dolly in, the subject turns to
camera, wind moves the hair"*. The image supplies the content.

---

## 3. Character swap — `Wan2.1-VACE-1.3B-CharacterSwap`

Status: verified (`vace_test_00001_.mp4`, 33 frames, 704x480, 20 steps, ~300 s).

Wan 2.1 **VACE** (Video All-in-one Conditional Engine) takes a reference image and a prompt and
generates a new clip that keeps the reference subject. It is not a face swap; it is conditioned
generation.

| Node | Type | Settings |
| --- | --- | --- |
| 1 | `UnetLoaderGGUF` | `Wan21-VACE-1.3B-Q8_0.gguf` |
| 2 | `CLIPLoaderGGUF` | `umt5-xxl-encoder-Q4_K_M.gguf`, type `wan` |
| 3 | `VAELoader` | `wan_2.1_vae.safetensors` (2.1, **not** 2.2) |
| 4 | `LoadImage` | your character photo |
| 5 / 6 | `CLIPTextEncode` | scene prompt / negative |
| 7 | `WanVaceToVideo` | 704 x 480, 81 frames, batch 1, **strength 1.0** |
| 8 | `ModelSamplingSD3` | shift 8.0 |
| 9 | `KSampler` | **20 steps, CFG 6.0**, `uni_pc` / `simple` |
| 10 | `TrimVideoLatent` | 0 |
| 11 | `VAEDecode` | - |
| 12 | `CreateVideo` | **16 fps** |
| 13 | `SaveVideo` | `video/VACE_CharacterSwap` |

Wiring worth knowing: `WanVaceToVideo` outputs `positive, negative, latent, trim_latent`. The
reference photo goes into input slot **5** (`reference_image`); `control_video` stays empty, which
means a flat gray control clip, i.e. pure reference conditioning. `trim_latent` feeds
`TrimVideoLatent` so the decoded frame count matches what was requested.

Differences from the Turbo graphs:

- **Not distilled.** It needs real CFG (6.0) and ~20 steps. Do not copy the Turbo settings here.
- **Two extra control latents** make it slower per step than the 5B model: 11.1 s/step vs ~4.5.
- **16 fps output**, so 81 frames = 5.1 s. 33 frames = 2.1 s.
- **Lower `strength`** (0.7-0.9) if the face is copied too rigidly or the pose is frozen.

Speed it up: add the CausVid LoRA
(`Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors`, strength ~0.7, 4 steps, CFG 1) to cut
~300 s to ~60-80 s, at some cost in motion quality.

---

## 4. 1080p output — `Wan2.2-Turbo-5B-TextToVideo-1080p`

Status: **experimental**. The graph is sound but has not been benchmarked end-to-end on the
reference machine.

Native 1920x1080 sampling needs roughly 20 GB VRAM, so this graph never samples at 1080p:

```
generate 864x480 (81 frames, 4 steps)
  -> UpscaleModelLoader (4x-UltraSharp)
  -> ImageUpscaleWithModel  (3456x1920)
  -> ImageScale (lanczos, 1920x1080)
  -> mp4
```

What to expect: a genuine 1920x1080 h264 file whose detail is interpolated. It looks like good
480p footage through a sharp lens, not like native 1080p. Motion and composition are identical to
the 480p render.

If the upscale stage OOMs: select `UpscaleModelLoader` and press **Ctrl+B** to bypass. The graph
then resizes 864x480 straight to 1920x1080 with Lanczos, which uses a fraction of the VRAM and
looks slightly softer.

The 4x upscale also works for clips you already rendered: `scripts/faceswap/upscale_video.py` does
the same RRDBNet pass tiled, outside ComfyUI.

---

## Command line / API

Each graph maps to an API prompt where nodes are addressed by the ids shown above. The scripts in
`scripts/` are complete examples.

```powershell
# text to video
powershell -File .\scripts\test_wan.ps1 -Prompt "..." -Width 704 -Height 480 -Length 81 -Steps 4

# character swap (image must exist in ComfyUI/input)
powershell -File .\scripts\test_vace.ps1 -Image character.png -Steps 20 -Cfg 6

# 480p -> 1920x1080
powershell -File .\scripts\test_1080p.ps1 -Prompt "..."
```

They POST to `http://127.0.0.1:8188/prompt`, poll `/history/<id>`, and print node errors verbatim.
The server must already be running.

If you change filenames or defaults and want the JSONs regenerated:

```powershell
.\ComfyUI_windows_portable\python_embeded\python.exe .\scripts\build_workflows.py
```

The script writes into `ComfyUI_windows_portable/ComfyUI/user/default/workflows/` by default and
verifies every link before finishing (`OK` per file).
