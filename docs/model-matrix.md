# The model matrix

One table per tier, for image and for video. Every row answers the same four questions:
**what runs, what does it cost on disk, what does the text encoder eat, and what do you get out.**

Only the 6 GB video row is measured on real hardware (the RTX 4050 in this repo). Everything else
is built from published file sizes, official minimum-VRAM statements and the VRAM model below.
Rows that are estimates say so.

> **Read this before the tables.** "Runs on 8 GB" always means *with ComfyUI's native weight
> streaming and a quantised file*. It never means "the fp16 checkpoint fits". A 20 GB model will
> start on a 8 GB card — it will also take an hour per clip.

---

## The three numbers that decide everything

```
VRAM needed  ≈  weights on disk × 1.6     (video, at 480p, after offload)
VRAM needed  ≈  weights on disk + 1.5 GB  (image, at 1 MP)
RAM needed   ≈  dequantised text encoder + 6 GB
```

The multiplier is not a fudge factor. A 4-bit file has to be dequantised into 16-bit tiles as it is
used, and attention on top of that scales with pixels and frames. The `× 1.6` is the measured
ratio for Wan 2.2 5B on 6 GB; smaller models land closer to `× 1.4`, bigger ones closer to `× 1.8`.

**The text encoder is the trap.** It is not counted in that budget because it usually runs from
system RAM. It is also frequently larger than the model you are excited about:

| Encoder | Used by | fp16 size | Dequantised RAM |
| --- | --- | --- | --- |
| CLIP-L / CLIP-G | SD 1.5, SDXL, FLUX.1 | 0.25 / 1.4 GB | 0.25 / 1.4 GB |
| T5-XXL | FLUX.1, SD 3.5, Chroma | 9.5 GB | 9.5 GB |
| UMT5-XXL | Wan 2.1 / 2.2 | 11 GB | 4.7 GB (encoder-only weights) |
| Qwen2.5-VL 7B | Qwen-Image, HunyuanVideo 1.5, LongCat, Kandinsky 5 | 16 GB | ~8 GB fp8 |
| Qwen3 4B | Z-Image, FLUX.2 Klein 4B, Anima | 8 GB | ~4 GB |
| Mistral Small 3.1 | FLUX.2 dev | ~24 GB | ~12 GB fp8 |
| Gemma 3 12B | LTX-2 / 2.3 | ~24 GB | ~12 GB |

Rule of thumb: **if the encoder is bigger than the diffusion model, plan for 16 GB of RAM minimum**
and expect the first 60–120 s of every prompt to be nothing but text.

---

## Image models by tier

| VRAM | Pick | File | Disk | Encoder | Tokens | Output | Steps | Est. per image |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **4 GB** | SD 1.5 | `v1-5-pruned-emaonly-fp16` | 2.1 GB | CLIP-L | 77 | 512×512 | 20–25, CFG 7 | 20–60 s |
| 4 GB | Anima (turbo) | `anima` Q4/Q8 | 1.2–2.2 GB | Qwen3 0.6B | 512 | 1024×1024 | 8–12, CFG 1 | 40–90 s |
| **6 GB** | FLUX.2 Klein 4B (distilled) | `flux-2-klein-4b-fp8` | 4.4 GB | Qwen3 4B fp8 | 512 | 1024×1024 | 4 | 40–90 s |
| 6 GB | SDXL | `sd_xl_base_1.0` Q8 | 3.5 GB | CLIP-L + G | 77 | 1024×1024 | 25, CFG 7 | 45–120 s |
| **8 GB** | FLUX.2 Klein 4B base | `flux-2-klein-base-4b-fp8` | 4.4 GB | Qwen3 4B fp8 | 512 | up to 2 MP | 20–28 | 60–150 s |
| 8 GB | Z-Image Turbo | `z_image_turbo` Q8 | 6.5 GB | Qwen3 4B Q8 | 512 | 1024×1024 | 8, CFG 1 | 45–90 s |
| **12 GB** | Z-Image Turbo | `z_image_turbo` fp8 | 6.5 GB | Qwen3 4B fp8 (GPU) | 512 | 1024–1440 | 8, CFG 1 | 25–50 s |
| 12 GB | FLUX.1 dev | `flux1-dev` Q8 | 12 GB | T5-XXL Q8 + CLIP-L | 512 + 77 | 1024×1024 | 20, CFG 1 (distilled) | 60–120 s |
| **16 GB** | HiDream I1 dev | `hidream_i1_dev_fp8` | 17.1 GB | CLIP-L + G + T5 + Llama 3.1 8B | 128–512 | 1024×1024 | 28, CFG 1 | 90–180 s |
| 16 GB | Z-Image (base) | `z_image` fp8 | 6.5 GB | Qwen3 4B fp8 (GPU) | 512 | 1024–1536 | 30–50, CFG 3–5 | 60–150 s |
| **24 GB** | Qwen-Image | `qwen_image_fp8_e4m3fn` | 20.4 GB | Qwen2.5-VL 7B fp8 | 512 | 1328×1328 | 50, CFG 4 (8 with Lightning LoRA) | 90–180 s |
| 24 GB | FLUX.2 dev | `flux2_dev_fp8mixed` | ~34 GB | Mistral Small 3.1 fp8 | 512 | up to 4 MP | 20–30 | 2–4 min |
| **32–48 GB** | Qwen-Image BF16 | `qwen_image_bf16` | 40.9 GB | Qwen2.5-VL 7B bf16 | 512 | 1664×928 | 50, CFG 4 | 60–120 s |
| 48 GB+ | FLUX.2 dev BF16 | `flux2_dev_bf16` | ~64 GB | Mistral Small 3.1 bf16 | 512 | up to 4 MP | 20–30 | 1–2 min |
| 48 GB+ | HiDream I1 full | `hidream_i1_full` | 34.2 GB | 4 encoders, fp16 | 128–512 | 1024×1024 | 50, CFG 5 | 2–3 min |

### What each pick is actually good at

- **SD 1.5 (4 GB)** — the only model that is genuinely fast on 4 GB. 512 px, huge LoRA/ControlNet
  ecosystem, weak at hands and text. Still the best "does my GPU work at all" test.
- **Anima (4–8 GB)** — 4.2 GB BF16, Qwen3 0.6B encoder, 512–1536 px. The cheapest route to
  modern-quality 1024 px output, and the encoder is small enough to keep on the GPU.
- **FLUX.2 Klein 4B (6–8 GB)** — 4-step distilled, Qwen3 4B encoder, edits from reference images.
  ComfyUI reports 8.4 GB peak for the distilled 4B and 9.2 GB for the base on an RTX 5090; on 6 GB
  you are on the offload path and it is slower, not impossible.
- **SDXL (6–8 GB)** — the mature workhorse. 77-token prompts, thousands of community checkpoints,
  no LLM encoder, no surprises.
- **Z-Image Turbo (8–16 GB)** — 8 steps at CFG 1, Qwen3 4B encoder, strong prompt following and
  readable text. ComfyUI's own figure is 16 GB; fp8/Q8 builds run lower with offload.
- **FLUX.1 dev (12 GB)** — the best-understood 12B model. T5-XXL at 512 tokens is what makes its
  prompt adherence good, and what makes its encoder pass expensive.
- **HiDream I1 (16 GB fp8, 27 GB+ full)** — four text encoders including Llama 3.1 8B. Best
  prompt adherence per step in this list, worst memory profile.
- **Qwen-Image (24 GB)** — 20B MMDiT, the strongest text rendering in any open model, 50 steps at
  CFG 4, or 8 steps with the Lightning LoRA. ComfyUI measured 86% of a 24 GB card with the fp8 build.
- **FLUX.2 dev (24–48 GB)** — 32B, Mistral Small encoder, up to 4 MP, multi-reference editing.
  This is the current quality ceiling and it costs like one.

---

## Video models by tier

| VRAM | Pick | File | Disk | Encoder | Tokens | Output | Steps | Est. per clip |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **4 GB** | Wan 2.1 1.3B | `wan2.1_t2v_1.3B` Q4 + CausVid LoRA | 1.1 GB | UMT5-XXL Q3 | 512 | 512×288, 33–49 f | 4 | 3–8 min |
| **6 GB** | **Wan 2.2 TI2V-5B Turbo** | `Wan22-Turbo-Q4_K_M.gguf` | 3.3 GB | UMT5 Q4 on CPU | 512 | 704×480, 81 f | 4, CFG 1 | **2.5 min (measured)** |
| **8 GB** | Wan 2.2 TI2V-5B | `Wan22-Turbo-Q5_K_M.gguf` | 4.1 GB | UMT5 Q4/Q8 | 512 | 832×480, 81–121 f | 4, CFG 1 | 2–4 min |
| **12 GB** | Wan 2.2 TI2V-5B | Q8_0 | 5.4 GB | UMT5 Q8 on GPU | 512 | 832×480, 121 f | 4, CFG 1 | 70–120 s |
| 12 GB | Kandinsky 5 Video Lite | `kandinsky5_video_lite` | 4.3 GB | Qwen2.5-VL 7B fp8 + CLIP-L | 512 | 768×512, 121 f | 16 (distilled) | 3–6 min |
| **16 GB** | HunyuanVideo 1.5 | `hunyuanvideo1.5_480p_t2v` fp8 | 8.3 GB | Qwen2.5-VL 7B fp8 + ByT5 | 512 | 720p, 5–10 s | 8–12 (distilled) | 2–5 min |
| 16 GB | Wan 2.2 A14B | two experts Q4 | 18 GB | UMT5 Q8 | 512 | 480p, 81 f | 4–20 | 6–12 min |
| **24 GB** | Wan 2.2 A14B | two experts fp8 | 28.6 GB | UMT5 Q8 on GPU | 512 | 720p, 81 f | 4–20 | 3–6 min |
| 24 GB | HunyuanVideo 1.5 | `720p_t2v` fp8 | 8.3 GB | Qwen2.5-VL 7B + ByT5 | 512 | 720p, 5–10 s | 20 (50 for quality) | 2–4 min |
| 24 GB | Mochi 1 | `mochi_preview_fp8` | 10 GB | T5-XXL | 256 | 848×480, 31 f | 64 | 4–8 min |
| **32 GB+** | LTX-2 | `ltx2_dev_fp8` / distilled | 20–27 GB | Gemma 3 12B | 512 | 720p + audio, 8n+1 f | 8 (distilled) | 1–3 min |
| 32 GB+ | LTX-2.3 | `ltx2.3_dev_fp8` | 27.1 GB | Gemma 3 12B | 512 | 720p + audio | 20 | 2–5 min |
| 32 GB+ | Wan 2.2 A14B BF16 | two experts | 57 GB | UMT5 fp16 | 512 | 720p | 20 | 2–4 min |
| 48 GB+ | LTX-2.3 BF16 | full precision | ~44 GB | Gemma 3 12B bf16 | 512 | 1080p + audio | 20–30 | 1–2 min |

### What each pick is actually good at

- **Wan 2.1 1.3B (4 GB)** — 2.84 GB fp16, so even a 4 GB card holds it. Native 480p, but 1.3B has
  no idea what hands are. Pair it with CausVid at 4 steps or it is unusably slow at 50.
- **Wan 2.2 TI2V-5B (6–12 GB)** — the sweet spot of the whole ecosystem: one model for text-to-video
  and image-to-video, native 720p/24 fps, 121 frames, and it fits on 8 GB by ComfyUI's own claim.
  The Turbo build at 4 steps is what makes a laptop viable.
- **Kandinsky 5 Video Lite (12 GB)** — 2B, 5 s or 10 s clips, distilled at 16 steps. Cheaper than
  HunyuanVideo 1.5 at 12 GB and needs the HunyuanVideo VAE plus both text encoders.
- **HunyuanVideo 1.5 (14–24 GB)** — 8.3B, 720p native, 5–10 s, image-to-video, and Tencent's own
  figure is 14 GB with offloading. The 480p CFG-distilled build is 8.33 GB and runs in 8–12 steps.
  The best quality-per-GB on 16 GB.
- **Wan 2.2 A14B (16–24 GB)** — MoE, two noise experts, 14.29 GB each in fp8. Faces, hands and
  motion are a real step up. On 16 GB you are offloading one expert and paying for it.
- **Mochi 1 (24 GB)** — 10B, beautiful motion, 31 frames, 64 steps. Slow and short, but nothing
  else at 848×480 looks like it.
- **LTX-2 / LTX-2.3 (32 GB+)** — the only models here that generate **video and audio together**,
  at 720p, in 8 steps for the distilled builds. 8n+1 frame rule, Gemma 3 12B encoder.
  LTX-2.3 dev fp8 is 27.1 GB before the encoder.
- **Cosmos Predict2 2B (16 GB)** — image-to-video world model, 480p/16 fps, needs the Wan 2.1 VAE.
  ComfyUI's workflow takes about 16 GB.
- **SCAIL-2 / Bernini-R** — Wan 2.1-based video editing and reference-guided generation, 81 frames
  at 512–704p. They need the Wan VAE, UMT5, a LightX2V LoRA and (for SCAIL-2) SAM 3.1 masks.

---

## Everything else ComfyUI supports natively

These are in the same release as the models above. They are worth knowing about, but their
memory profiles move with the templates, so treat the encoder column as the useful part.

| Model | Kind | Encoder | Note |
| --- | --- | --- | --- |
| Krea 2 | image | Qwen3-VL 4B / 8B | newer, strong aesthetics |
| FLUX 3 image klein | image + edit | Qwen3-VL 4B | succeeds FLUX.2 Klein |
| Ideogram 4 | image | Qwen3-VL 8B | text rendering |
| Qwen-Image 2.1 | image + edit | Qwen3-VL 8B | 8B encoder, cheaper than Qwen-Image 1 |
| MOSS-Image | image | Qwen3.5 9B | 9B encoder, big |
| ERNIE-Image | image | Ministral 3B | smaller encoder than most |
| MageFlow / MageFlow Edit | image | — | template defaults |
| Microsoft Lens | image | gpt-oss-20b | 20B encoder, RAM-hungry |
| PixelDiT | image | Gemma 2 2B | pixel-space diffusion |
| LongCat Image / Edit | image | Qwen2.5-VL 7B | 12.5 GB BF16, ~17 GB with offload |
| Lumina Image 2.0 | image | Gemma 2 2B | 10.6 GB all-in-one |
| Chroma | image | T5-XXL | 17.8 GB, distilled FLUX.1 family |
| Fibo 2.0 / JoyImage Edit / Boogu / OmniGen2 | edit | Qwen3-VL 4B / Qwen VL 2.5 3B | edit-specialised |
| CogVideoX 2B / 5B | video | T5 (226 tokens) | 3.4 / 11.1 GB, 720×480 |
| Wan 2.2 Animate 14B | video | UMT5 | 14B, identity transfer, 24 GB+ |
| MiniMax H3 / LTX-AV | audio + video | Qwen3-VL 32B / Gemma 3 | joint audio-video |
| ACE-Step 1.5 / Stable Audio 3 / MiniMax Music 3 / Yue 2 | audio | — | music and SFX |
| Hunyuan3D 2.1 / TripoSplat | 3D | — | image to mesh |
| SeedVR2 / SUPIR | upscale / restore | — | video restoration |

If a model is missing from this page, it is because it has no stable published memory figure —
not because it does not work. The ComfyUI template browser ships a workflow for each one.

---

## Laptops, AMD, Intel, Apple, CPU

| Hardware | What works | What to expect |
| --- | --- | --- |
| **NVIDIA laptop 4–8 GB** | everything in the 4/6/8 GB rows | plug in the charger; on battery clocks halve. Close the browser: it holds 0.5–1.5 GB of VRAM |
| **NVIDIA laptop 12–16 GB** | 12/16 GB rows | the 16 GB laptop cards are the best value tier — 8 GB models run fully resident |
| **AMD Windows** | ComfyUI-Zluda, or DirectML | no official ROCm on Windows; 20–50% slower than an equivalent NVIDIA card, GGUF dequant may fall back to CPU |
| **AMD Linux** | ROCm torch builds | flags are the same, `--reserve-vram` behaves differently; start with `--lowvram` under 8 GB |
| **Intel Arc** | IPEX-LLM or Vulkan | works; GGUF kernels are the weak point, expect slow sampling rather than a crash |
| **Apple Silicon** | MPS, unified memory | allocate more GPU memory in macOS; a 16 GB Mac behaves like an 8 GB card, a 64 GB Mac like a 24 GB one — but 5–10× slower per step |
| **CPU only** | SD 1.5 at 512 px | 50–100× slower than a 6 GB GPU. Fine for a test, not for work |

---

## Disk and RAM planning

| Use | Models on disk | System RAM |
| --- | --- | --- |
| Image only, one family | 5–15 GB | 16 GB |
| Image + one video family | 20–35 GB | 16–32 GB |
| The 6 GB video build in this repo | ~9 GB | 16 GB |
| 24 GB tier with Qwen-Image + Wan 2.2 A14B | 60–90 GB | 32 GB |
| 48 GB tier with FLUX.2 dev + LTX-2.3 | 150 GB+ | 64 GB |

Quantised files are the only reason any of this fits. The ladder is the same everywhere:
`fp16/bf16 → fp8 → Q8 → Q6 → Q5_K_M → Q4_K_M → Q3_K_M`. **Q4_K_M is the last stop before quality
falls off a cliff.** Below Q4 you are looking at a different model's output, not a cheaper one.

---

## How much of this is verified

| Claim | Status |
| --- | --- |
| 6 GB Wan 2.2 5B timings, VRAM peak, flags | **measured** on the RTX 4050 in this repo |
| Wan 2.2 5B fits 8 GB | ComfyUI documentation |
| HunyuanVideo 1.5 14 GB minimum | Tencent model card |
| Qwen-Image 86% of 24 GB, 40.9 GB BF16 | ComfyUI documentation + file listing |
| HiDream 16 GB fp8 / 27 GB full | ComfyUI documentation |
| LTX-2 32 GB+ | Lightricks ComfyUI-LTXVideo requirements |
| FLUX.2 Klein 8.4 / 9.2 GB peak | ComfyUI measurement on RTX 5090 |
| Z-Image Turbo 16 GB | ComfyUI documentation |
| Kandinsky 5 Lite 12 GB | Kandinsky project |
| File sizes, token limits | model cards and ComfyUI file listings |
| Every "est. per clip/image" column | **extrapolated** — not benchmarked |

Seconds do not transfer between cards. The ratios do.
