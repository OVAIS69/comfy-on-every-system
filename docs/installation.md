# Installation

Two paths: the **Windows portable** install (what this repo was built and measured on) and a
**manual Python** install for Linux/macOS. Both end at the same place: ComfyUI with the GGUF
loader node and the six model files in the right folders.

Total download: ~9 GB of models + ~1.5 GB ComfyUI. Budget 30-35 GB of disk for outputs and
temporary files.

---

## 1. Prerequisites

| Item | Minimum | Notes |
| --- | --- | --- |
| GPU | NVIDIA, 6 GB VRAM | 8 GB+ gives headroom; see [hardware.md](hardware.md) |
| RAM | 16 GB | the text encoder streams from system RAM; 32 GB is noticeably smoother |
| Disk | 35 GB free | models 9 GB, ComfyUI 1.5 GB, videos and temp files the rest |
| OS | Windows 10/11, or Linux | macOS works on Apple Silicon but much slower (MPS) |
| Python | 3.11-3.13 | only needed for the manual install |
| Driver | recent NVIDIA driver | CUDA 12.x runtime is bundled with the torch wheel |

You do **not** need a CUDA toolkit, Visual Studio, or a Hugging Face account. All model files are
public.

---

## 2. Install ComfyUI (Windows portable)

1. Open <https://github.com/comfyanonymous/ComfyUI/releases> and download the latest
   `ComfyUI_windows_portable_nvidia.7z`.
2. Extract it into the repo root so that this exists:

   ```
   comfyui-wan-6gb\
     ComfyUI_windows_portable\
       python_embeded\python.exe
       ComfyUI\main.py
   ```

   Windows 11 (24H2+) can open `.7z` in Explorer. Otherwise use 7-Zip.

3. Confirm the GPU is visible:

   ```powershell
   .\ComfyUI_windows_portable\python_embeded\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```

   Expect something like `2.x.x+cu12x True NVIDIA GeForce RTX 4050 Laptop GPU`.
   If `cuda.is_available()` is `False`, stop here: the GPU driver is the problem, not the models.

---

## 3. Install the GGUF loader node

ComfyUI cannot read `.gguf` model files without this custom node.

```powershell
git clone --depth 1 https://github.com/city96/ComfyUI-GGUF.git `
    .\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-GGUF

.\ComfyUI_windows_portable\python_embeded\python.exe -m pip install `
    -r .\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-GGUF\requirements.txt
```

Start ComfyUI once and check the log for `Import times for custom nodes` with
`ComfyUI-GGUF ... 0.0 seconds` and no traceback. The new nodes are `UnetLoaderGGUF` and
`CLIPLoaderGGUF`.

> If you get `ModuleNotFoundError: No module named 'gguf'`, the pip step above did not run against
> the portable Python. Re-run it with the full path to `python_embeded\python.exe`.

---

## 4. Download the models

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_models.ps1
```

The script uses `curl.exe` (built into Windows 10+), resumes partial files, skips files that are
already complete, and converts the 4x-UltraSharp `.pth` into the `.safetensors` the workflows
expect.

Add `-IncludeFaceswap` to also fetch the three ONNX models and the Python deps for the face-swap
script. Add `-ComfyDir D:\path\to\ComfyUI_windows_portable` if ComfyUI lives elsewhere.

Manual download table: [models.md](models.md).

Final layout:

```
ComfyUI_windows_portable\ComfyUI\models\
  diffusion_models\Wan22-Turbo-Q4_K_M.gguf
  diffusion_models\Wan21-VACE-1.3B-Q8_0.gguf
  text_encoders\umt5-xxl-encoder-Q4_K_M.gguf
  vae\wan2.2_vae.safetensors
  vae\wan_2.1_vae.safetensors
  upscale_models\4x-UltraSharp.safetensors
```

---

## 5. Add the workflows

Copy the four JSON files into the sidebar folder:

```powershell
Copy-Item .\workflows\*.json .\ComfyUI_windows_portable\ComfyUI\user\default\workflows\
```

They appear under **Workflows** in the left sidebar after a page refresh. Dragging a JSON file
onto the canvas also works and is enough for a one-off run.

---

## 6. Start it

```powershell
.\scripts\run_comfyui.bat
```

which runs:

```
python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build ^
    --reserve-vram 0.2 --preview-method none
```

- `--reserve-vram 0.2` leaves 200 MB for the desktop compositor and stops Windows from spilling
  the model to shared memory (which is what makes it slow).
- `--preview-method none` skips per-step preview decoding; on 6 GB it costs VRAM for no benefit.
- **No `--lowvram`.** Counter-intuitive, but letting the UNet stay fully on the GPU is ~2x faster
  than `--lowvram` here: 4.5 s/step vs 24.7 s/step. Use
  `scripts\run_comfyui_lowvram.bat` only if the fast path OOMs.

Open <http://127.0.0.1:8188>.

---

## 7. First render

1. Open **Workflows -> Wan2.2-Turbo-5B-TextToVideo**.
2. Edit the prompt in the `CLIPTextEncode` node.
3. Press **Run**.
4. First run takes ~2.5 min at 704x480 for 81 frames. The output appears in
   `ComfyUI_windows_portable\ComfyUI\output\video\`.

Or from the command line, with the server running:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_wan.ps1 `
    -Prompt "a red fox walking through a snowy pine forest at sunrise" `
    -Width 704 -Height 480 -Length 81 -Steps 4
```

The script submits to `http://127.0.0.1:8188/prompt`, polls `/history`, and prints the elapsed
time and output filename.

---

## Linux

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python3 -m venv venv && source venv/bin/activate

# pick the CUDA wheel that matches your driver; cu124 is a safe default
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt

git clone --depth 1 https://github.com/city96/ComfyUI-GGUF.git custom_nodes/ComfyUI-GGUF
pip install -r custom_nodes/ComfyUI-GGUF/requirements.txt
```

Download the models from [models.md](models.md) into the matching `models/` subfolders, copy the
workflows into `user/default/workflows/`, then:

```bash
python main.py --reserve-vram 0.2 --preview-method none
```

`--reserve-vram` is a fraction of total VRAM in recent ComfyUI builds. On 6 GB cards it is the
difference between 4.5 and 25 seconds per step.

## macOS

ComfyUI runs on Apple Silicon via MPS, and the same GGUF files work, but expect roughly 5-10x the
sampling time of a 6 GB RTX card. The `--reserve-vram` flag is a no-op. Prefer 512x288 and 49
frames. No CUDA-only extras (SageAttention, fp8) apply.

---

## Verify the install

- [ ] `torch.cuda.is_available()` is `True` and prints the right GPU name.
- [ ] ComfyUI log shows `ComfyUI-GGUF` imported without errors.
- [ ] `UnetLoaderGGUF` dropdown lists `Wan22-Turbo-Q4_K_M.gguf`.
- [ ] `VAELoader` lists `wan2.2_vae.safetensors` **and** `wan_2.1_vae.safetensors`.
- [ ] `UpscaleModelLoader` lists `4x-UltraSharp.safetensors`.
- [ ] A 512x288 / 49-frame run finishes in ~40-60 s.

If a model is missing from a dropdown, the file is in the wrong folder or ComfyUI was started
before you copied it: **model lists are cached at startup**, so restart the server.

Next: [workflows.md](workflows.md) · [performance.md](performance.md) · [troubleshooting.md](troubleshooting.md)
