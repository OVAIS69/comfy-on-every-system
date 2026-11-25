# FAQ

**Why 704x480 and not 720p?**

480p is what Wan 2.2 TI2V-5B was trained on. 720p means 2.25x the pixels, which on 6 GB pushes the
activations past the VRAM limit: per-step time goes from ~4.5 s to 35-40 s and quality does not
improve. 704x480 is the largest size that stays inside the budget.

**Why 81 frames?**

81 frames at 24 fps is 3.4 s, the length the model handles without temporal drift. It is also 4n+1,
which the VAE's 4x temporal compression requires. 121 frames works if you need 5 s; beyond that,
quality degrades and VRAM gets tight.

**Why 4 steps and CFG 1?**

That is what "Turbo" means: the model is distilled to produce a usable frame in 4 sampling steps
with no classifier-free guidance. More steps give marginal polish at linear cost. CFG above 1
burns contrast and doubles the model passes.

**Then why does the VACE graph use 20 steps and CFG 6?**

Because VACE 1.3B is **not** distilled. Different model, different recipe. Copying Turbo settings
onto VACE produces mush.

**Why is there no negative prompt in the text-to-video graph?**

At CFG 1.0 the negative conditioning is multiplied by zero. It is mathematically ignored, so the
node only costs a second umt5 pass (~1 minute here). The image-to-video template still has one;
bypass it with Ctrl+B.

**Why does the text encoder take longer than the sampling?**

umt5-xxl is 4.66 GB dequantised. The UNet takes 3.4 GB and stays on the GPU, so the encoder cannot
join it and streams from system RAM. On a 3.4 s clip this fixed cost is 75-80% of the run.

**Can I put the encoder on the GPU?**

Only if you free ~1.5 GB of VRAM (close browsers and overlays) or switch to
`umt5-xxl-encoder-Q3_K_M.gguf` (~2.7 GiB). On a 6 GB card the Q4 encoder never fits next to the
UNet.

**Can I sample at 1080p?**

No. 1920x1080 needs roughly 20 GB of VRAM for this model. The 1080p workflow generates at 864x480
and upscales 4x. The file is 1920x1080; the detail is interpolated.

**Why does the ComfyUI template browser want 50 GB of models?**

The templates reference full-precision safetensors. The 5B fp16 model is ~10 GB and the 14B models
are 28-60 GB. Those never fit on 6 GB. Ignore the "Install missing models" button and use the GGUF
graphs in `workflows/`.

**What is the difference between the VACE workflow and the face-swap scripts?**

- VACE **generates a new video** from a prompt and a reference photo. Motion is invented.
- The scripts **edit an existing video**, one frame at a time, keeping the original motion exactly.

VACE gives "a character like this in a new scene". The scripts give "this video, different face".

**Can VACE put a specific real person into a video, recognisably?**

Not reliably. VACE 1.3B carries face shape, hair and clothing style, not identity. For real
identity transfer you want Wan 2.2 Animate 14B or a dedicated face swap, and the 14B model does not
fit in 6 GB.

**Does this work on AMD / Intel / Apple?**

See [hardware.md](hardware.md). Short version: AMD via ComfyUI-Zluda or ROCm on Linux, Intel via
IPEX-LLM/Vulkan, Apple via MPS but 5-10x slower. Only NVIDIA was measured here.

**How much disk do I need?**

~9 GB of models, ~1.5 GB ComfyUI, plus outputs. Budget 30-35 GB total.

**Where do the videos go?**

`ComfyUI_windows_portable\ComfyUI\output\video\`. The `SaveVideo` node's `filename_prefix`
controls the subfolder and name.

**Why is my first run much slower than later ones?**

The first run loads 3.4 GB of GGUF weights and warms the CUDA allocator. Later runs in the same
server session are faster. Restarting ComfyUI pays the load cost again.

**Can I use SageAttention?**

Yes on RTX 30/40 series: `pip install sageattention`, then add `--use-sage-attention` to the
launcher. It speeds up attention and usually saves a little VRAM. It is not required.

**Can I run the 14B models on 12-16 GB?**

Wan 2.2 14B at Q4_K_M is ~8.5 GB of weights, so it needs offloading on 12 GB and is borderline on
16 GB. It is untested here. The 5B setup remains faster to iterate on at 480p.

**Is this legal to use?**

The Wan weights are Apache-2.0, the encoder is Apache-2.0, ComfyUI is GPL-3.0. Check the upscaler
and `inswapper_128` licenses before commercial use; the latter is research-only. And do not swap
faces onto people who have not consented.

**Why does the video have no sound?**

`CreateVideo` writes a silent stream. Mux the original audio back with ffmpeg if you need it
(command in [troubleshooting.md](troubleshooting.md#video-has-no-audio)).
