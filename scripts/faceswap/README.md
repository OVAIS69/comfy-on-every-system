# Face-swap pipeline (outside ComfyUI)

Two scripts:

| Script | What it does |
| --- | --- |
| `swap_video.py` | YuNet detect -> ArcFace embed -> inswapper_128 per frame, with LAB colour matching |
| `upscale_video.py` | tiled 4x RRDBNet (4x-UltraSharp) -> Lanczos to the target size -> h264 |

They are independent: you can upscale any clip, and you can swap without upscaling.

## Install

Use the ComfyUI portable Python so `torch` and `av` are already available:

```powershell
..\..\ComfyUI_windows_portable\python_embeded\python.exe -m pip install -r requirements.txt
```

Models (in `models/faceswap/` after `download_models.ps1 -IncludeFaceswap`, or next to the scripts):

```
inswapper_128.onnx                 ~529 MiB
w600k_r50.onnx                     ~166 MiB
face_detection_yunet_2023mar.onnx  ~230 KiB
```

## Run

```powershell
$py = "..\..\ComfyUI_windows_portable\python_embeded\python.exe"

# quick test: first 8 frames only
& $py swap_video.py --src ref.png --video in.mp4 --out test.mp4 --count 8

# full clip
& $py swap_video.py --src ref.png --video in.mp4 --out swapped.mp4

# upscale to 1080x1920
& $py upscale_video.py --video swapped.mp4 --out final.mp4 --width 1080 --height 1920
```

The first swapped frame is written next to the output as `last_src_crop.png` so you can check the
source alignment without watching the video.

Full documentation: [../../docs/faceswap.md](../../docs/faceswap.md).
