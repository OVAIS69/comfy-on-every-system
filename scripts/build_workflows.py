"""Regenerate the four ComfyUI workflow JSONs used by this project.

Usage:
    python build_workflows.py [output_dir]

Default output: <repo>/ComfyUI_windows_portable/ComfyUI/user/default/workflows
Override with the first argument or the COMFY_WORKFLOWS_DIR environment variable.
"""
import json, os, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "ComfyUI_windows_portable", "ComfyUI",
                           "user", "default", "workflows")
OUT = (sys.argv[1] if len(sys.argv) > 1
       else os.environ.get("COMFY_WORKFLOWS_DIR", DEFAULT_OUT))
OUT = os.path.abspath(OUT)
os.makedirs(OUT, exist_ok=True)


class G:
    def __init__(self):
        self.nodes = []
        self.links = []
        self._link = 0

    def add(self, nid, ntype, widgets, pos, size, inputs=(), outputs=(), title=None, color=None, mode=0):
        node = {
            "id": nid,
            "type": ntype,
            "pos": list(pos),
            "size": list(size),
            "flags": {},
            "order": len(self.nodes),
            "mode": mode,
            "inputs": [],
            "outputs": [],
            "properties": {"cnr_id": "comfy-core", "Node name for S&R": ntype},
            "widgets_values": list(widgets),
        }
        if title:
            node["title"] = title
        if color:
            node["color"] = color[0]
            node["bgcolor"] = color[1]
        for i, (name, typ) in enumerate(inputs):
            node["inputs"].append({"name": name, "type": typ, "link": None})
        for i, (name, typ) in enumerate(outputs):
            node["outputs"].append({"name": name, "type": typ, "slot_index": i, "links": []})
        self.nodes.append(node)
        return node

    def node(self, nid):
        for n in self.nodes:
            if n["id"] == nid:
                return n
        raise KeyError(nid)

    def link(self, src, src_slot, dst, dst_slot, typ):
        self._link += 1
        lid = self._link
        s = self.node(src)
        d = self.node(dst)
        s["outputs"][src_slot]["links"].append(lid)
        d["inputs"][dst_slot]["link"] = lid
        self.links.append([lid, src, src_slot, dst, dst_slot, typ])
        return lid

    def dump(self, path, name):
        doc = {
            "id": str(uuid.uuid4()),
            "revision": 0,
            "last_node_id": max(n["id"] for n in self.nodes),
            "last_link_id": self._link,
            "nodes": self.nodes,
            "links": self.links,
            "groups": [],
            "config": {},
            "extra": {"ds": {"scale": 0.72, "offset": [0, 0]}},
            "version": 0.4,
        }
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print("wrote", name, len(self.nodes), "nodes", self._link, "links")


POS_WAN22 = (
    "Low contrast. A lone street musician plays guitar in a dim 1970s subway station, "
    "rough textures, warm tungsten light, commuters passing in soft focus. "
    "The camera slowly pushes in. Film grain, muted color palette."
)
NEG = ("blurry, low quality, jpeg artifacts, static, still frame, extra limbs, "
       "deformed hands, distorted face, watermark, text, subtitles")

# ---------------------------------------------------------------- 1) TEXT TO VIDEO
g = G()
g.add(1, "UnetLoaderGGUF", ["Wan22-Turbo-Q4_K_M.gguf"], (-30, 60), (350, 82),
      outputs=[("MODEL", "MODEL")])
g.add(2, "CLIPLoaderGGUF", ["umt5-xxl-encoder-Q4_K_M.gguf", "wan"], (-30, 200), (350, 106),
      outputs=[("CLIP", "CLIP")])
g.add(3, "VAELoader", ["wan2.2_vae.safetensors"], (-30, 360), (350, 58),
      outputs=[("VAE", "VAE")])

g.add(4, "CLIPTextEncode", [POS_WAN22], (380, 60), (440, 200),
      inputs=[("clip", "CLIP")], outputs=[("CONDITIONING", "CONDITIONING")],
      title="Prompt (text to video)", color=("#232", "#353"))

g.add(5, "Wan22ImageToVideoLatent", [704, 480, 81, 1], (380, 300), (300, 130),
      inputs=[("vae", "VAE"), ("start_image", "IMAGE")],
      outputs=[("LATENT", "LATENT")],
      title="Video size + length (no start image = text to video)")

g.add(6, "ModelSamplingSD3", [8.0], (880, 60), (240, 58),
      inputs=[("model", "MODEL")], outputs=[("MODEL", "MODEL")])

g.add(7, "KSampler", [123456789, "randomize", 4, 1.0, "euler", "simple", 1.0], (880, 160), (330, 262),
      inputs=[("model", "MODEL"), ("positive", "CONDITIONING"), ("negative", "CONDITIONING"), ("latent_image", "LATENT")],
      outputs=[("LATENT", "LATENT")],
      title="KSampler - Turbo 4 steps")

g.add(8, "VAEDecode", [], (1250, 160), (220, 46),
      inputs=[("samples", "LATENT"), ("vae", "VAE")], outputs=[("IMAGE", "IMAGE")])
g.add(9, "CreateVideo", [24], (1250, 240), (280, 78),
      inputs=[("images", "IMAGE"), ("audio", "AUDIO")], outputs=[("VIDEO", "VIDEO")])
g.add(10, "SaveVideo", ["video/Wan22_T2V", "auto", "auto"], (1250, 350), (620, 420),
      inputs=[("video", "VIDEO")])

g.link(1, 0, 6, 0, "MODEL")
g.link(6, 0, 7, 0, "MODEL")
g.link(2, 0, 4, 0, "CLIP")
g.link(4, 0, 7, 1, "CONDITIONING")
g.link(4, 0, 7, 2, "CONDITIONING")   # negative = positive: CFG 1.0, saves a whole encoder pass
g.link(3, 0, 5, 0, "VAE")
g.link(5, 0, 7, 3, "LATENT")
g.link(7, 0, 8, 0, "LATENT")
g.link(3, 0, 8, 1, "VAE")
g.link(8, 0, 9, 0, "IMAGE")
g.link(9, 0, 10, 0, "VIDEO")

g.add(11, "MarkdownNote", [
    "## Wan 2.2 Turbo 5B - TEXT TO VIDEO\n\n"
    "No image needed. Type a prompt and press **Run**.\n\n"
    "**Defaults that work on this laptop (6 GB VRAM):**\n"
    "- 704 x 480, 81 frames (3.4 s @ 24 fps), 4 steps, CFG 1.0\n"
    "- About **2.5 min** per clip\n\n"
    "**Speed tips**\n"
    "- 49 frames instead of 81 = roughly half the time.\n"
    "- 640 x 352 is the next step down in cost.\n"
    "- Keep steps at 4 - this is the 4-step Turbo model.\n\n"
    "**Negative prompt:** there is none on purpose. CFG 1.0 ignores it, and having\n"
    "a second text-encode node costs about 60 s per run on this machine.\n\n"
    "Models used: Wan22-Turbo-Q4_K_M.gguf, umt5-xxl-encoder-Q4_K_M.gguf, wan2.2_vae.safetensors"
], (-520, 60), (460, 430), title="Read me", color=("#222", "#000"))

g.dump(OUT, "Wan2.2-Turbo-5B-TextToVideo.json")

# ---------------------------------------------------------------- 2) CHARACTER SWAP (VACE R2V)
g = G()
g.add(1, "UnetLoaderGGUF", ["Wan21-VACE-1.3B-Q8_0.gguf"], (-30, 60), (370, 82),
      outputs=[("MODEL", "MODEL")])
g.add(2, "CLIPLoaderGGUF", ["umt5-xxl-encoder-Q4_K_M.gguf", "wan"], (-30, 200), (370, 106),
      outputs=[("CLIP", "CLIP")])
g.add(3, "VAELoader", ["wan_2.1_vae.safetensors"], (-30, 360), (370, 58),
      outputs=[("VAE", "VAE")])

g.add(4, "LoadImage", ["character.png", "image"], (-30, 460), (370, 400),
      outputs=[("IMAGE", "IMAGE"), ("MASK", "MASK")],
      title="Your character reference image")

g.add(5, "CLIPTextEncode", [
    "The person from the reference image walks through a neon-lit alley at night, "
    "cinematic lighting, shallow depth of field, slow camera dolly, detailed face, film look."
], (400, 60), (440, 190),
      inputs=[("clip", "CLIP")], outputs=[("CONDITIONING", "CONDITIONING")],
      title="Describe what your character does", color=("#232", "#353"))

g.add(6, "CLIPTextEncode", [NEG], (400, 280), (440, 130),
      inputs=[("clip", "CLIP")], outputs=[("CONDITIONING", "CONDITIONING")],
      title="Negative prompt", color=("#322", "#533"))

g.add(7, "WanVaceToVideo", [704, 480, 81, 1, 1.0], (400, 450), (330, 190),
      inputs=[("positive", "CONDITIONING"), ("negative", "CONDITIONING"), ("vae", "VAE"),
              ("control_video", "IMAGE"), ("control_masks", "MASK"), ("reference_image", "IMAGE")],
      outputs=[("positive", "CONDITIONING"), ("negative", "CONDITIONING"),
               ("latent", "LATENT"), ("trim_latent", "INT")],
      title="VACE - reference image to video")

g.add(8, "ModelSamplingSD3", [8.0], (900, 60), (240, 58),
      inputs=[("model", "MODEL")], outputs=[("MODEL", "MODEL")])

g.add(9, "KSampler", [987654321, "randomize", 20, 6.0, "uni_pc", "simple", 1.0], (900, 160), (330, 262),
      inputs=[("model", "MODEL"), ("positive", "CONDITIONING"), ("negative", "CONDITIONING"), ("latent_image", "LATENT")],
      outputs=[("LATENT", "LATENT")],
      title="KSampler - CFG 6, 20 steps")

g.add(10, "TrimVideoLatent", [0], (1270, 160), (240, 60),
      inputs=[("samples", "LATENT"), ("trim_amount", "INT")],
      outputs=[("LATENT", "LATENT")],
      title="Drop reference frames")
g.node(10)["inputs"][1]["widget"] = {"name": "trim_amount"}

g.add(11, "VAEDecode", [], (1270, 260), (220, 46),
      inputs=[("samples", "LATENT"), ("vae", "VAE")], outputs=[("IMAGE", "IMAGE")])
g.add(12, "CreateVideo", [16], (1270, 340), (280, 78),
      inputs=[("images", "IMAGE"), ("audio", "AUDIO")], outputs=[("VIDEO", "VIDEO")])
g.add(13, "SaveVideo", ["video/VACE_CharacterSwap", "auto", "auto"], (1270, 450), (620, 400),
      inputs=[("video", "VIDEO")])

g.link(1, 0, 8, 0, "MODEL")
g.link(8, 0, 9, 0, "MODEL")
g.link(2, 0, 5, 0, "CLIP")
g.link(2, 0, 6, 0, "CLIP")
g.link(5, 0, 7, 0, "CONDITIONING")
g.link(6, 0, 7, 1, "CONDITIONING")
g.link(3, 0, 7, 2, "VAE")
g.link(4, 0, 7, 5, "IMAGE")
g.link(7, 0, 9, 1, "CONDITIONING")
g.link(7, 1, 9, 2, "CONDITIONING")
g.link(7, 2, 9, 3, "LATENT")
g.link(9, 0, 10, 0, "LATENT")
g.link(7, 3, 10, 1, "INT")
g.link(10, 0, 11, 0, "LATENT")
g.link(3, 0, 11, 1, "VAE")
g.link(11, 0, 12, 0, "IMAGE")
g.link(12, 0, 13, 0, "VIDEO")

g.add(14, "MarkdownNote", [
    "## Wan 2.1 VACE 1.3B - CHARACTER SWAP\n\n"
    "Puts **your character** (reference image) into a new scene.\n\n"
    "### How to use\n"
    "1. Put a picture of the character in `ComfyUI\\input\\` (any name, e.g. `character.png`).\n"
    "2. Click the image node and pick it.\n"
    "3. Describe the scene + what they do in the prompt.\n"
    "4. Press **Run**.\n\n"
    "The result is a 3.4 s clip with that character's face, hair and clothes carried over.\n\n"
    "### Defaults\n"
    "- 704 x 480, 81 frames, **20 steps, CFG 6** (this model is not distilled)\n"
    "- About **1.5-2 min** per clip\n\n"
    "### Notes\n"
    "- Best with a clear, front-facing, well-lit reference photo.\n"
    "- Lower `strength` (0.7-0.9) if the face is copied too rigidly.\n"
    "- This is VACE reference-to-video. Wan 2.2 *Animate* gives better swaps but is a\n"
    "  14B model (~30 GB) and cannot run on 6 GB VRAM.\n\n"
    "Models used: Wan21-VACE-1.3B-Q8_0.gguf, umt5-xxl-encoder-Q4_K_M.gguf, wan_2.1_vae.safetensors"
], (-520, 60), (460, 500), title="Read me", color=("#222", "#000"))

g.dump(OUT, "Wan2.1-VACE-1.3B-CharacterSwap.json")

# ---------------------------------------------------------------- 3) TEXT TO VIDEO -> 1080p
g = G()
g.add(1, "UnetLoaderGGUF", ["Wan22-Turbo-Q4_K_M.gguf"], (-30, 60), (350, 82),
      outputs=[("MODEL", "MODEL")])
g.add(2, "CLIPLoaderGGUF", ["umt5-xxl-encoder-Q4_K_M.gguf", "wan"], (-30, 200), (350, 106),
      outputs=[("CLIP", "CLIP")])
g.add(3, "VAELoader", ["wan2.2_vae.safetensors"], (-30, 360), (350, 58),
      outputs=[("VAE", "VAE")])
g.add(4, "CLIPTextEncode", [POS_WAN22], (380, 60), (440, 200),
      inputs=[("clip", "CLIP")], outputs=[("CONDITIONING", "CONDITIONING")],
      title="Prompt", color=("#232", "#353"))
g.add(5, "Wan22ImageToVideoLatent", [864, 480, 81, 1], (380, 300), (300, 130),
      inputs=[("vae", "VAE"), ("start_image", "IMAGE")],
      outputs=[("LATENT", "LATENT")],
      title="Generate at 864x480 (16:9), upscale after")
g.add(6, "ModelSamplingSD3", [8.0], (880, 60), (240, 58),
      inputs=[("model", "MODEL")], outputs=[("MODEL", "MODEL")])
g.add(7, "KSampler", [123456789, "randomize", 4, 1.0, "euler", "simple", 1.0], (880, 160), (330, 262),
      inputs=[("model", "MODEL"), ("positive", "CONDITIONING"), ("negative", "CONDITIONING"), ("latent_image", "LATENT")],
      outputs=[("LATENT", "LATENT")], title="KSampler - Turbo 4 steps")
g.add(8, "VAEDecode", [], (1250, 160), (220, 46),
      inputs=[("samples", "LATENT"), ("vae", "VAE")], outputs=[("IMAGE", "IMAGE")])

g.add(9, "UpscaleModelLoader", ["4x-UltraSharp.safetensors"], (1250, 260), (330, 58),
      outputs=[("UPSCALE_MODEL", "UPSCALE_MODEL")],
      title="Bypass this node (Ctrl+B) if you run out of memory")
g.add(10, "ImageUpscaleWithModel", [], (1250, 350), (330, 46),
      inputs=[("upscale_model", "UPSCALE_MODEL"), ("image", "IMAGE")],
      outputs=[("IMAGE", "IMAGE")])
g.add(11, "ImageScale", ["lanczos", 1920, 1080, "center"], (1250, 430), (330, 130),
      inputs=[("image", "IMAGE")], outputs=[("IMAGE", "IMAGE")],
      title="Final resolution 1920x1080")
g.add(12, "CreateVideo", [24], (1620, 160), (280, 78),
      inputs=[("images", "IMAGE"), ("audio", "AUDIO")], outputs=[("VIDEO", "VIDEO")])
g.add(13, "SaveVideo", ["video/Wan22_1080p", "auto", "auto"], (1620, 270), (620, 400),
      inputs=[("video", "VIDEO")])

g.link(1, 0, 6, 0, "MODEL")
g.link(6, 0, 7, 0, "MODEL")
g.link(2, 0, 4, 0, "CLIP")
g.link(4, 0, 7, 1, "CONDITIONING")
g.link(4, 0, 7, 2, "CONDITIONING")
g.link(3, 0, 5, 0, "VAE")
g.link(5, 0, 7, 3, "LATENT")
g.link(7, 0, 8, 0, "LATENT")
g.link(3, 0, 8, 1, "VAE")
g.link(8, 0, 10, 1, "IMAGE")
g.link(9, 0, 10, 0, "UPSCALE_MODEL")
g.link(10, 0, 11, 0, "IMAGE")
g.link(11, 0, 12, 0, "IMAGE")
g.link(12, 0, 13, 0, "VIDEO")

g.add(14, "MarkdownNote", [
    "## 1920x1080 output - how it is done here\n\n"
    "6 GB of VRAM cannot *sample* at 1080p, so this graph does it in two stages:\n\n"
    "1. Generate the clip at **864 x 480** (16:9, the model's 480p comfort zone).\n"
    "2. Upscale the decoded frames **4x** with UltraSharp, then rescale to **1920 x 1080**.\n\n"
    "You get a true 1920x1080 file. Detail is interpolated, not invented - it looks\n"
    "like good 480p shot on a sharper lens, not like native 1080p.\n\n"
    "### If it runs out of memory (OOM)\n"
    "Click the `UpscaleModelLoader` node and press **Ctrl+B** to bypass it.\n"
    "The graph then does a plain Lanczos 1920x1080 upscale: much less VRAM,\n"
    "slightly softer, and it never fails.\n\n"
    "### Other limits\n"
    "- 81 frames x 1080p needs a lot of RAM; 49 frames is safer.\n"
    "- Native 1080p sampling needs ~20 GB VRAM. On this laptop that means a cloud GPU\n"
    "  (RunPod / fal / Replicate, roughly 0.3-0.8 USD per clip)."
], (2230, 60), (470, 520), title="Read me", color=("#222", "#000"))

g.dump(OUT, "Wan2.2-Turbo-5B-TextToVideo-1080p.json")

# ---------------------------------------------------------------- validate
# The image-to-video graph is the official template with GGUF loaders swapped in,
# so it is shipped as-is and not regenerated here.
for fn in ["Wan2.2-Turbo-5B-TextToVideo.json",
           "Wan2.1-VACE-1.3B-CharacterSwap.json",
           "Wan2.2-Turbo-5B-TextToVideo-1080p.json"]:
    with open(os.path.join(OUT, fn), encoding="utf-8") as f:
        d = json.load(f)
    byid = {n["id"]: n for n in d["nodes"]}
    bad = []
    for lid, src, ss, dst, ds, typ in d["links"]:
        if lid not in byid[src]["outputs"][ss]["links"]:
            bad.append(("origin", lid))
        if byid[dst]["inputs"][ds]["link"] != lid:
            bad.append(("target", lid))
    print("OK" if not bad else "BAD " + str(bad), fn)
