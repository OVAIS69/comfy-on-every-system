# Contributing

The most useful contribution is a **hardware report**: run one 704x480 / 81 frame / 4 step clip and
one VACE 33 frame clip, then open an issue with:

- GPU model, VRAM, driver version
- RAM, CPU
- OS, ComfyUI version, torch version (`python -c "import torch; print(torch.__version__)"`)
- launch flags
- wall-clock for both clips, and the per-step time from the log
- whether the encoder logged `loaded completely` or `loaded partially`

That turns [hardware.md](docs/hardware.md) from extrapolation into data.

## Fixes

- Keep the four graphs loadable in the stock ComfyUI UI format (links validated by
  `scripts/build_workflows.py`).
- Keep scripts ASCII-only: PowerShell 5.1 misparses UTF-8 source without a BOM.
- Do not add model files, videos, or screenshots of real people to the repo.
- Document measured numbers as measured and estimates as estimates. Do not present a guess as a
  benchmark.

## Regenerating workflows

```powershell
.\ComfyUI_windows_portable\python_embeded\python.exe .\scripts\build_workflows.py
```

It writes all four JSONs and prints `OK <file>` after verifying every link endpoint.
