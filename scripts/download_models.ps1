# Download every model this project needs into a ComfyUI portable install.
#
# Usage (from the repo root, PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts\download_models.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\download_models.ps1 -IncludeFaceswap
#   powershell -ExecutionPolicy Bypass -File scripts\download_models.ps1 -ComfyDir D:\ComfyUI_windows_portable
#
# Resumable: re-running skips files that already have the expected size and
# continues partial downloads (curl -C -).

param(
    [string]$ComfyDir = "",
    [switch]$IncludeFaceswap
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if (-not $ComfyDir) { $ComfyDir = Join-Path $repo "ComfyUI_windows_portable" }
$comfy = Join-Path $ComfyDir "ComfyUI"
if (-not (Test-Path $comfy)) {
    throw "ComfyUI not found at $comfy. Extract the portable build there first, or pass -ComfyDir."
}

$py = Join-Path $ComfyDir "python_embeded\python.exe"
$curl = Join-Path $env:SystemRoot "System32\curl.exe"
if (-not (Test-Path $curl)) { $curl = "curl.exe" }

$dirs = @(
    (Join-Path $comfy "models\diffusion_models"),
    (Join-Path $comfy "models\text_encoders"),
    (Join-Path $comfy "models\vae"),
    (Join-Path $comfy "models\upscale_models")
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

# name -> @(url, local directory, expected bytes)
$models = [ordered]@{
    "Wan22-Turbo-Q4_K_M.gguf" = @(
        "https://huggingface.co/hum-ma/Wan2.2-TI2V-5B-Turbo-GGUF/resolve/main/Wan2_2-TI2V-5B-Turbo-Q4_K_M.gguf",
        "diffusion_models", 3437927136)
    "Wan21-VACE-1.3B-Q8_0.gguf" = @(
        "https://huggingface.co/calcuis/wan-gguf/resolve/main/wan2.1-v4-vace-1.3b-q8_0.gguf",
        "diffusion_models", 2296280864)
    "umt5-xxl-encoder-Q4_K_M.gguf" = @(
        "https://huggingface.co/city96/umt5-xxl-encoder-gguf/resolve/main/umt5-xxl-encoder-Q4_K_M.gguf",
        "text_encoders", 3655145312)
    "wan2.2_vae.safetensors" = @(
        "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors",
        "vae", 1409400960)
    "wan_2.1_vae.safetensors" = @(
        "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors",
        "vae", 253815318)
}

foreach ($name in $models.Keys) {
    $url, $sub, $size = $models[$name]
    $dest = Join-Path (Join-Path $comfy "models\$sub") $name
    if (Test-Path $dest) {
        $have = (Get-Item $dest).Length
        if ($have -ge [int64]($size * 0.9)) {
            Write-Host "skip   $name (already present, $([math]::Round($have/1MB)) MiB)" -ForegroundColor DarkGray
            continue
        }
        Write-Host "resume $name ($([math]::Round($have/1MB)) of $([math]::Round($size/1MB)) MiB)" -ForegroundColor Yellow
    } else {
        Write-Host "fetch  $name  -> models\$sub" -ForegroundColor Cyan
    }
    & $curl -L --fail --retry 5 --retry-delay 3 -C - -o $dest $url
    if ($LASTEXITCODE -ne 0) { throw "download failed: $name" }
}

# 4x-UltraSharp is published as a .pth; the workflows expect .safetensors.
$upPth = Join-Path $comfy "models\upscale_models\4x-UltraSharp.pth"
$upSft = Join-Path $comfy "models\upscale_models\4x-UltraSharp.safetensors"
if (-not (Test-Path $upSft)) {
    if (-not (Test-Path $upPth)) {
        Write-Host "fetch  4x-UltraSharp.pth" -ForegroundColor Cyan
        & $curl -L --fail --retry 5 -C - -o $upPth `
            "https://huggingface.co/lokCX/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth"
        if ($LASTEXITCODE -ne 0) { throw "download failed: 4x-UltraSharp.pth" }
    }
    Write-Host "convert 4x-UltraSharp.pth -> .safetensors" -ForegroundColor Cyan
    & $py (Join-Path $PSScriptRoot "convert_upscaler.py") $upPth $upSft
    if ($LASTEXITCODE -ne 0) { throw "safetensors conversion failed" }
}

if ($IncludeFaceswap) {
    $fs = Join-Path $repo "models\faceswap"
    New-Item -ItemType Directory -Force -Path $fs | Out-Null
    $extra = [ordered]@{
        "inswapper_128.onnx" = "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx"
        "w600k_r50.onnx" = "https://huggingface.co/WePrompt/buffalo_l/resolve/main/w600k_r50.onnx"
        "face_detection_yunet_2023mar.onnx" = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
    }
    foreach ($name in $extra.Keys) {
        $dest = Join-Path $fs $name
        if (Test-Path $dest) { Write-Host "skip   $name" -ForegroundColor DarkGray; continue }
        Write-Host "fetch  $name -> models\faceswap" -ForegroundColor Cyan
        & $curl -L --fail --retry 5 -C - -o $dest $extra[$name]
        if ($LASTEXITCODE -ne 0) { throw "download failed: $name" }
    }
    Write-Host "installing python deps for faceswap ..." -ForegroundColor Cyan
    & $py -m pip install --no-warn-script-location opencv-python-headless onnxruntime onnx av
}

Write-Host ""
Write-Host "Models ready in $comfy\models" -ForegroundColor Green
Write-Host "Next: install ComfyUI-GGUF, then start ComfyUI with scripts\run_comfyui.bat"
