@echo off
REM Fallback mode: only use this if the fast launcher runs out of VRAM
REM (another app is holding GPU memory, or you push above 480p).
REM It is roughly 2x slower but peaks around 3.8 GB instead of 5.7 GB.

setlocal
if not defined COMFY_DIR set "COMFY_DIR=%~dp0..\ComfyUI_windows_portable"

if not exist "%COMFY_DIR%\python_embeded\python.exe" (
    echo [ERROR] ComfyUI portable not found at "%COMFY_DIR%"
    echo See scripts\run_comfyui.bat for instructions.
    pause
    exit /b 1
)

cd /d "%COMFY_DIR%"
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --lowvram --reserve-vram 0.2 --preview-method none %*
pause
