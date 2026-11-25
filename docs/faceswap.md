# Face swap + upscale (outside ComfyUI)

The VACE workflow generates *new* video from a reference photo. This pipeline is the other
problem: you already have a video and want the face in it replaced, frame by frame, with the
original motion, timing and framing intact.

No diffusion model is involved. It is three small ONNX networks on the CPU:

```
frame -> YuNet (detect face + 5 landmarks)
      -> Umeyama similarity transform -> 128x128 aligned crop
      -> ArcFace w600k_r50 -> 512-d identity vector
      -> inswapper_128 (target crop + source vector) -> swapped 128x128 face
      -> LAB colour match to the target crop
      -> inverse transform + feathered ellipse mask -> composited frame
      -> mp4
```

---

## Why each step exists

**YuNet** (`face_detection_yunet_2023mar.onnx`, 230 KiB) returns a bounding box plus five
landmarks (eyes, nose, mouth corners) per face. Only the largest face per frame is used.

**Umeyama similarity transform** maps those five points onto the ArcFace template:

```
[38.29, 51.70] [73.53, 51.50] [56.03, 71.74] [41.55, 92.37] [70.73, 92.20]   # 112x112
```

scaled by `size/112` for the 128 px crop. A closed-form least-squares similarity transform is used
rather than RANSAC: with exactly five points, RANSAC can pick a degenerate pair and produce a
shifted crop. That failure looks like a face pasted half off the head.

**ArcFace** (`w600k_r50.onnx`, 166 MiB) turns the aligned 112x112 crop into a 512-d embedding,
normalised to unit length. Input is RGB, `(x/255 - 0.5) / 0.5`, NCHW.

**The `emap` projection** is the step most reimplementations get wrong. `inswapper_128.onnx`
expects a *projected* latent, not the raw embedding:

```python
emap = numpy_helper.to_array(onnx.load(SWAP).graph.initializer[-1])  # 512x512
latent = e @ emap
latent /= np.linalg.norm(latent)
```

Skip it and the swap still runs, but the likeness collapses into a generic face. The matrix is the
last initializer in the ONNX graph.

**inswapper_128** takes `target` (1,3,128,128, BGR, /255) and `source` (1,512, the projected
latent) and returns (1,3,128,128) in **0..1**. Multiply by 255; do not assume 0..255 output.

**Colour matching** is not optional in practice. The model transfers some of the source image's
lighting, so a blue-lit reference produces a blue face in a warm scene. The script converts both
the fake and the target crop to CIELAB and matches statistics inside the face mask:

- **a/b (chroma)**: full mean and standard deviation match - this fixes the hue.
- **L (luminance)**: mean match plus a gentler contrast match (exponent 0.35), so skin texture and
  shadow detail survive.

`--color` controls the strength (default 0.85; `0` disables it).

**Paste-back** uses the inverse affine transform and a feathered ellipse mask (`--blend` scales
the alpha). The mask is deliberately larger than the face and blurred, because a hard edge is the
most obvious tell.

---

## Models

| File | Size | Source |
| --- | --- | --- |
| `inswapper_128.onnx` | 529 MiB | [ezioruan/inswapper_128.onnx](https://huggingface.co/ezioruan/inswapper_128.onnx) |
| `w600k_r50.onnx` | 166 MiB | [WePrompt/buffalo_l](https://huggingface.co/WePrompt/buffalo_l) |
| `face_detection_yunet_2023mar.onnx` | 230 KiB | [opencv_zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) |

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_models.ps1 -IncludeFaceswap
```

That also installs `opencv-python-headless`, `onnxruntime` and `onnx` into the portable Python.
`inswapper_128` is **research-use only**; it is not licensed for commercial deployment.

---

## Usage

```powershell
$py = ".\ComfyUI_windows_portable\python_embeded\python.exe"
$fs = ".\scripts\faceswap"

# test on 8 frames first - always do this
& $py "$fs\swap_video.py" --src hush_ref.png --video in.mp4 --out test.mp4 --count 8

# full clip
& $py "$fs\swap_video.py" --src hush_ref.png --video in.mp4 --out swapped.mp4

# 4x upscale + resize to 1080x1920
& $py "$fs\upscale_video.py" --video swapped.mp4 --out final.mp4 --width 1080 --height 1920
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--src` | required | reference face image (frontal, well lit, one face) |
| `--video` / `--out` | required | input / output mp4 |
| `--count` | 0 (all) | stop after N frames; use 8-16 for a test |
| `--start` | 0 | skip the first N frames |
| `--size` | 128 | inswapper input size; 128 is the only trained size |
| `--blend` | 1.0 | alpha of the paste-back; 0.85 softens the seam |
| `--color` | 0.85 | LAB colour-match strength; 0 disables |
| `--models` | auto | folder holding the three ONNX files |

`upscale_video.py` flags: `--width`, `--height` (target, default 1080x1920), `--ckpt` (default
`ComfyUI/models/upscale_models/4x-UltraSharp.safetensors`), `--crf` (default 18).

---

## Measured speed

Reference machine, onnxruntime **CPU** (no CUDA provider installed), 576x1024 input:

| Stage | Rate |
| --- | --- |
| swap (detect + embed + inswapper + composite) | ~0.96 fps |
| 385-frame clip | ~6.7 min |
| 4x upscale | GPU, tiled 256 px, dominated by the 1080p h264 encode |

The swap is CPU-bound and single-threaded-ish. If you need it faster:

- `pip install onnxruntime-gpu` and change `providers=["CPUExecutionProvider"]` to
  `["CUDAExecutionProvider"]` in `swap_video.py` (about 3-5x faster).
- Run `--start`/`--count` in parallel chunks and concatenate.
- Swap at the source resolution, then upscale once at the end - never upscale first.

---

## Limits

- **128 pixels.** `inswapper_128` generates a 128x128 face. On a 1000 px face in a 4K frame that
  is a visible softness even after the upscale. There is no cheap fix; the model is what it is.
- **Photographs only.** It was trained on real faces. Stylised 3D renders, anime, heavy beauty
  filters and paintings produce weak or wrong likeness.
- **No temporal smoothing.** Each frame is independent, so a bad detection on one frame produces a
  one-frame glitch. A simple fix is to detect every frame, then median-filter the landmark
  trajectories before applying; the script does not do that yet.
- **Profiles and occlusion fail.** YuNet needs both eyes and the mouth. Extreme side views,
  hands on the face, and sunglasses drop the detection below threshold and the frame is passed
  through untouched (`missed` in the summary line).
- **One face per frame.** The largest face wins. Crowds need per-face tracking.
- **No audio.** The output is a silent `mp4v` stream. Mux the original audio back with ffmpeg.

## Ethics

This is a face-swap tool. Use it on people who have consented - yourself, actors you have hired,
characters you own. Publishing someone's likeness without permission is illegal in many
jurisdictions and is not what this repo is for.
