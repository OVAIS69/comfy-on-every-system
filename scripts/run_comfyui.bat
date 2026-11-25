@echo off
REM Fast mode: lets ComfyUI keep the UNet fully on the GPU.
REM Peak observed on a 6 GB RTX 4050 laptop: ~5.7 GB of 6.1 GB at 704x480 / 81 frames.
REM
REM Expects a ComfyUI portable install in .\ComfyUI_windows_portable next to this file.
REM Override with:  set COMFY_DIR=C:\some\other\ComfyUI_windows_portable

setlocal
if not defined COMFY_DIR set "COMFY_DIR=%~dp0..\ComfyUI_windows_portable"

if not exist "%COMFY_DIR%\python_embeded\python.exe" (
    echo [ERROR] ComfyUI portable not found at "%COMFY_DIR%"
    echo Download it from https://github.com/comfyanonymous/ComfyUI/releases and extract it
    echo into the repo root as ComfyUI_windows_portable, or set COMFY_DIR.
    pause
    exit /b 1
)

cd /d "%COMFY_DIR%"
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --reserve-vram 0.2 --preview-method none %*
pause
