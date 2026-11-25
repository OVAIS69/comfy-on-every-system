"""Upscale a video with 4x-UltraSharp (RRDBNet) on the GPU, tiled, then resize to target.

Usage:
  python upscale_video.py --video in.mp4 --out out.mp4 --width 1080 --height 1920
"""
import argparse
import os
import time

import av
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from safetensors.torch import load_file

HERE = os.path.dirname(os.path.abspath(__file__))
CKPT = os.environ.get(
    "UPSCALE_MODEL",
    os.path.abspath(os.path.join(HERE, "..", "..", "ComfyUI_windows_portable",
                                 "ComfyUI", "models", "upscale_models",
                                 "4x-UltraSharp.safetensors")))


class ResidualDenseBlock(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(nf, gc)
        self.rdb2 = ResidualDenseBlock(nf, gc)
        self.rdb3 = ResidualDenseBlock(nf, gc)

    def forward(self, x):
        out = self.rdb3(self.rdb2(self.rdb1(x)))
        return out * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, nf=64, nb=23, gc=32):
        super().__init__()
        self.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


def load_model(dev, ckpt):
    if not os.path.exists(ckpt):
        raise SystemExit("upscale model not found: " + ckpt +
                         "\nPass --ckpt PATH or set the UPSCALE_MODEL env var.")
    sd = load_file(ckpt)
    sd = {k.replace("params_ema.", "").replace("params.", ""): v for k, v in sd.items()}
    m = RRDBNet()
    m.load_state_dict(sd, strict=True)
    return m.eval().to(dev).half()


@torch.no_grad()
def upscale_frame(model, img_bgr, dev, tile=256, overlap=24):
    h, w = img_bgr.shape[:2]
    out = torch.zeros((3, h * 4, w * 4), dtype=torch.float16, device=dev)
    step = tile - overlap
    for y in range(0, h, step):
        for x in range(0, w, step):
            y2 = min(y + tile, h)
            x2 = min(x + tile, w)
            y1 = max(0, y2 - tile)
            x1 = max(0, x2 - tile)
            crop = img_bgr[y1:y2, x1:x2][:, :, ::-1].astype(np.float32) / 255.0
            t = torch.from_numpy(np.ascontiguousarray(crop.transpose(2, 0, 1)))[None].to(dev).half()
            res = model(t).float().clamp(0, 1)[0]
            oy1, ox1 = y1 * 4, x1 * 4
            oy2, ox2 = oy1 + (y2 - y1) * 4, ox1 + (x2 - x1) * 4
            out[:, oy1:oy2, ox1:ox2] = res.half()
            del t, res
    arr = out.float().clamp(0, 1).cpu().numpy().transpose(1, 2, 0)
    return arr[:, :, ::-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--ckpt", default=CKPT, help="path to 4x-UltraSharp.safetensors/.pth")
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print("device", dev, "loading RRDBNet ...")
    model = load_model(dev, a.ckpt)

    cap = cv2.VideoCapture(a.video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    print(f"input {W}x{H} @ {fps}")

    container = av.open(a.out, mode="w")
    stream = container.add_stream("libx264", rate=int(round(fps)))
    stream.width = a.width
    stream.height = a.height
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": str(a.crf), "preset": "medium"}

    n = 0
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        big = upscale_frame(model, frame, dev)
        big = cv2.resize(big, (a.width, a.height), interpolation=cv2.INTER_LANCZOS4)
        vf = av.VideoFrame.from_ndarray(big.astype(np.uint8), format="bgr24")
        for pkt in stream.encode(vf):
            container.mux(pkt)
        n += 1
        if n % 20 == 0:
            el = time.time() - t0
            print(f"{n} frames {n/el:.2f} fps {el:.0f}s", flush=True)
    for pkt in stream.encode():
        container.mux(pkt)
    container.close()
    cap.release()
    print(f"DONE {n} frames in {time.time()-t0:.1f}s -> {a.out}")


if __name__ == "__main__":
    main()
