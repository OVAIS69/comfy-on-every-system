# Outputs

What actually lands in `ComfyUI/output/` at each tier, and what it is worth.

> **No renders are committed to this repo.** The `.gitignore` excludes `*.png`, `*.mp4` and every
> weight file, so the repository stays ~100 KB and clones instantly. The tables below are the
> specifications of the files each tier produces, not a gallery of somebody else's clips.

---

## File specs by tier

### Video

| Tier | Settings | File | Duration | Approx. size |
| --- | --- | --- | --- | --- |
| 4 GB | 512×288, 33–49 f, 24 fps | `Wan22_T2V_0000x_.mp4` | 1.4–2.0 s | 0.5–1.5 MB |
| **6 GB (measured)** | 704×480, 81 f, 24 fps | `Wan22_T2V_00002_.mp4` | 3.4 s | 1.5–3 MB |
| 8 GB | 832×480, 81–121 f, 24 fps | `Wan22_T2V_0000x_.mp4` | 3.4–5.0 s | 2–5 MB |
| 12 GB | 832×480, 121 f, 24 fps | `Wan22_T2V_0000x_.mp4` | 5.0 s | 3–6 MB |
| 16 GB | 1280×704, 121 f, 24 fps | `hunyuan15_0000x_.mp4` | 5.0 s | 5–12 MB |
| 24 GB | 1280×720, 81 f, 24 fps | `wan22_14b_0000x_.mp4` | 3.4 s | 4–9 MB |
| 32 GB+ | 1280×720 + audio, 121 f, 24 fps | `ltx2_0000x_.mp4` | 5.0 s | 8–20 MB |
| 1080p path | 480p sample → 4× upscale → 1920×1080 | `Wan22_T2V_1080p_0000x_.mp4` | 3.4 s | 8–25 MB |

Container is h264 MP4 via the `SaveVideo` node, 24 fps unless you change `CreateVideo`. VACE
graphs in this repo are set to 16 fps, so 81 frames = 5.1 s there.

### Images

| Tier | Model | File | Size |
| --- | --- | --- | --- |
| 4 GB | SD 1.5, 512×512 | `ComfyUI_0000x_.png` | 0.4–0.8 MB |
| 6 GB | FLUX.2 Klein 4B, 1024×1024 | `ComfyUI_0000x_.png` | 1.5–3 MB |
| 8–12 GB | Z-Image Turbo, 1024×1024 | `ComfyUI_0000x_.png` | 1.5–3 MB |
| 16 GB | HiDream I1, 1024×1024 | `ComfyUI_0000x_.png` | 1.5–3 MB |
| 24 GB | Qwen-Image, 1328×1328 | `ComfyUI_0000x_.png` | 3–6 MB |
| 24–48 GB | FLUX.2 dev, up to 4 MP | `ComfyUI_0000x_.png` | 6–15 MB |

PNG is 8-bit by default. `SaveImage` has a 16-bit option, and 32-bit EXR / 10-bit AVIF are supported
if you are going into a grading pipeline.

---

## What the 6 GB build actually produced

From the measured runs on the reference machine (RTX 4050 Laptop, 6 GB, 16 GB RAM):

| Job | Output | Time | Notes |
| --- | --- | --- | --- |
| Text → video, 704×480, 81 f, 4 steps | `Wan22_T2V_00002_.mp4` | 152–174 s | the reference clip |
| Text → video, 512×288, 81 f, 4 steps | `Wan22_T2V_0000x_.mp4` | 88 s | draft quality, same motion |
| Text → video, 832×480, 81 f, 4 steps | `Wan22_T2V_0000x_.mp4` | 293–296 s | crosses the VRAM line |
| Character swap, VACE 1.3B, 33 f, 20 steps | `vace_test_00001_.mp4` | ~300 s | 704×480, 16 fps |
| 480p → 4× → 1920×1080 | `Wan22_T2V_1080p_0000x_.mp4` | not benchmarked | graph labelled experimental |
| Face swap, 385 frames + upscale | `swapped_1080x1920.mp4` | ~6.7 min | outside ComfyUI |

Two honest observations from those files:

- **480p reads as 480p.** On a phone screen it looks sharp; on a 27" monitor the softness is
  obvious, especially on faces and text. The 4× upscale sharpens edges, it does not invent detail.
- **3.4 s is short.** It is enough for a loop, a product turntable, or a shot you cut into a longer
  edit. It is not enough for a scene.

---

## Sample prompts and what to expect

These are prompt shapes that work with Wan 2.2 at 480p, not magic words.

| Prompt | Tokens | What you get | Watch out for |
| --- | --- | --- | --- |
| `a red fox walking through fresh snow, slow dolly in, golden hour` | ~14 | clean subject, believable snow, gentle camera move | fur detail at 480p is soft |
| `a ceramic coffee cup on a wooden table, steam rising, static camera, soft window light` | ~16 | stable, product-shot look | steam is the only motion; keep it short |
| `neon-lit Tokyo alley at night, rain, slow push forward, anamorphic` | ~13 | strong colour, convincing rain | neon text renders as glyph soup |
| `a woman turns to camera and smiles, shallow depth of field` | ~11 | works, identity is generic | hands and teeth degrade first |
| `a paper boat floating down a stream, macro, 60fps feel` | ~12 | good motion | "60fps" is a style cue, not a setting |

For image models the same rule holds: subject, then style, then camera. 15–60 words. Long prompts
do not add detail, they add encoder time (see [tokens.md](tokens.md)).

---

## Choosing an output format

| You want | Do |
| --- | --- |
| A loop | 81 frames, 24 fps, first and last frame similar; or 49 frames at 16 fps |
| A shot to cut into an edit | 121 frames at 24 fps, 832×480, then upscale |
| A still from a clip | `SaveImage` on the decoded frames, or grab a frame with ffmpeg |
| A 1080p deliverable | the 1080p graph: sample at 864×480, 4× UltraSharp, Lanczos to 1920×1080 |
| Transparency | PNG with alpha for images; video alpha needs a different codec, not h264 |
| Grading | 16-bit PNG or EXR out of `SaveImage` |

---

## Where files go

```
ComfyUI/output/
  Wan22_T2V_00002_.mp4
  vace_test_00001_.mp4
  ComfyUI_00001_.png
```

The 1080p graph writes into `output/video/`, and the face-swap scripts write next to their input
unless you pass `--out`. Nothing is overwritten: ComfyUI increments the counter, so a failed run
still leaves a file behind to inspect.
