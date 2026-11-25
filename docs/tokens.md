# Tokens

A prompt is not free. Before a single denoising step runs, your text is tokenised, run through a
text encoder, and turned into conditioning vectors. On low-end hardware that pass is frequently
**the largest single cost of the job** — on the 6 GB reference machine it is 75–80% of a 3.4 s clip.

This page is about that number: how many tokens each encoder accepts, what a token costs, and how
to spend fewer of them.

---

## What a token is here

Roughly ¾ of a word in English. `a red fox in fresh snow, golden hour, 85mm` is about 12 tokens.
The limits below are **per prompt, including the negative prompt** — and with CFG above 1.0 the
negative prompt is a second full encode, so a CFG-6 workflow pays twice.

---

## Token limits by encoder

| Encoder | Models | Max tokens | Notes |
| --- | --- | --- | --- |
| CLIP-L / CLIP-G | SD 1.5, SDXL, FLUX.1 (CLIP half) | **77** | hard architectural limit; longer prompts are truncated, not summarised |
| T5-XXL | FLUX.1, SD 3.5, Chroma | **512** | longer prompts are cut |
| UMT5-XXL | Wan 2.1, Wan 2.2, VACE, SCAIL-2, Bernini-R | **512** | 256 also works; 512 is the usual workflow setting |
| T5 (CogVideoX) | CogVideoX | **226** | padded to 226 |
| T5 (Mochi) | Mochi 1 | **256** | — |
| Qwen2.5-VL 7B | Qwen-Image, HunyuanVideo 1.5, LongCat, Kandinsky 5 | **512** | accepts long prompts; 512 is the pipeline setting |
| Qwen3 4B | Z-Image, FLUX.2 Klein 4B, Anima | **512** | reference implementations truncate at 512 |
| Qwen3 8B | FLUX.2 Klein 9B | **512** | — |
| Qwen3-VL 8B | Krea 2, FLUX 3, Ideogram 4, Qwen-Image 2.1 | **512** | — |
| Qwen3.5 9B | MOSS-Image | **512** | — |
| Mistral Small 3.1 | FLUX.2 dev | **512** | `max_sequence_length` in the pipeline |
| Ministral 3B | ERNIE-Image | **512** | — |
| Gemma 3 12B | LTX-2, LTX-2.3 | **512** | — |
| Llama 3.1 8B | HiDream I1 | 128 (per encoder) | four encoders, each with its own budget |

Two things worth internalising:

1. **CLIP's 77 is a wall, not a default.** Past 77 tokens on SDXL or SD 1.5 the text is silently
   dropped. Prompt weighting (`(word:1.3)`) and `BREAK` are how people work around it.
2. **The 512s are pipeline settings, not physics.** Z-Image's rotary positions allow up to 1536
   text positions; the reference code truncates at 512 because that is what the model was trained
   on. Feeding 1500 tokens is possible and mostly a waste.

---

## What a token costs

Encode time scales linearly with tokens and roughly with encoder size. From the measured 6 GB run
(Wan 2.2 5B, UMT5-XXL Q4 streamed from RAM):

| Prompt length | Tokens | Encode time (6 GB, measured/derived) |
| --- | --- | --- |
| `a fox in snow` | 4 | ~55 s |
| 20-word scene description | ~28 | ~65 s |
| 60-word description | ~85 | ~85 s |
| 200-word description | ~280 | ~120 s |
| 350-word description | ~490 (at the 512 cap) | ~130 s |

The curve is not steep because the encoder is fast. It is steep because **the whole 4.66 GB encoder
has to be walked through for every prompt**, and the per-token work sits on top of that. A 4-token
prompt still costs ~55 s; a 500-token prompt costs ~130 s. The fixed cost dominates, the token cost
is the second term.

Consequences:

- **Rewriting a prompt costs the same as the first prompt.** ComfyUI re-encodes unless the
  conditioning is cached as a node output.
- **Batching is free text.** Batch size 4 shares one encode across four clips. This is the single
  best way to amortise the encoder on a small card.
- **Deleting the negative prompt is a 50% discount** whenever CFG is 1.0 — with CFG 1.0 the
  negative conditioning is mathematically ignored, so encoding it is pure waste. The Turbo graphs in
  this repo do exactly that.

---

## The same prompt, different tiers

Encoding a 500-token prompt on each tier, as a share of total job time:

| Tier | Encoder placement | Encode | Share of a 3.4 s clip |
| --- | --- | --- | --- |
| 4 GB | CPU, Q3 | 150–200 s | 90%+ |
| 6 GB | CPU, Q4 | ~120 s | **75–80% (measured)** |
| 8 GB | CPU, Q4/Q8 | 80–120 s | 60–70% |
| 12 GB | GPU, Q8 | 8–15 s | 10–20% |
| 16 GB | GPU, Q8 | 5–10 s | <10% |
| 24 GB | GPU, fp16 | 3–6 s | <5% |

The cliff between 8 GB and 12 GB is not the video model — it is the encoder finally living on the
GPU. **If you are choosing a card for this work, that cliff is the one to buy across.**

---

## Spending fewer tokens

| Do | Why |
| --- | --- |
| Keep prompts under ~75 words for video | the fixed encoder cost is already paid; more words buy little |
| Put the subject first | attention weight decays with position |
| Use one style clause, not five | `cinematic, 35mm, shallow depth of field` is enough |
| Delete the negative at CFG 1.0 | it is not read |
| Batch prompts | one encode, many clips |
| Use a smaller encoder quant on <8 GB | Q3_K_M cuts the pass ~40% for a small quality cost |
| Cache conditioning | feed a saved conditioning into several samplers in one graph |
| Keep the encoder resident across runs | don't restart ComfyUI between prompts |

What does **not** help: shortening a prompt from 200 words to 50 on a 6 GB card. You save ~20 s out
of 150. The encoder weights, not the tokens, are the cost.

---

## If you meant "tokens" as API credits

ComfyUI's partner/API nodes (Nano Banana, Seedance, Kling, etc.) are priced per run by the
provider, not in tokens, and they run on someone else's GPU — the whole memory discussion above
does not apply. The `--offline` flag disables them entirely. Everything on this page is local
inference, and local inference has no per-token billing.

---

## Prompt budget cheat sheet

```
SD 1.5 / SDXL        77 tokens   -> ~50 words, use weights and BREAK
FLUX.1 / Chroma      512 (T5) + 77 (CLIP)
Qwen-Image           512 tokens  -> ~350 words
FLUX.2 dev/Klein     512 tokens  -> ~350 words
Z-Image / Anima      512 tokens
Wan 2.1 / 2.2        512 tokens  -> ~350 words
HunyuanVideo 1.5     512 tokens
LTX-2 / 2.3          512 tokens
CogVideoX            226 tokens  -> ~150 words
Mochi                256 tokens  -> ~170 words
```

A good video prompt is 30–70 words. A good image prompt is 15–60. If you are past 200 words you are
usually describing a scene to a language model, not to a diffusion model.
