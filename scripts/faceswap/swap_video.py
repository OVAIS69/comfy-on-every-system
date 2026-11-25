"""Face swap a video with ONNX models (YuNet detect + ArcFace w600k + inswapper_128).

Pipeline per frame:
  1. YuNet finds the largest face + 5 landmarks in the video frame
  2. Umeyama similarity transform aligns that face to the ArcFace template
  3. inswapper_128 generates the swapped 128x128 face from the source embedding
  4. the result is warped back with a soft elliptical mask

Usage:
  python swap_video.py --src hush_ref.png --video in.mp4 --out out.mp4
  python swap_video.py --src ref.png --video in.mp4 --out test.mp4 --count 8
"""
import argparse
import os
import sys
import time

import cv2
import numpy as np
import onnx
import onnxruntime as ort
from onnx import numpy_helper

HERE = os.path.dirname(os.path.abspath(__file__))


def find_models_dir(explicit=None):
    """Models live next to the script, or in <repo>/models/faceswap."""
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates += [
        HERE,
        os.path.abspath(os.path.join(HERE, "..", "..", "models", "faceswap")),
    ]
    for d in candidates:
        if os.path.exists(os.path.join(d, "inswapper_128.onnx")):
            return d
    return HERE


MODELS = find_models_dir()
DET = os.path.join(MODELS, "face_detection_yunet_2023mar.onnx")
EMB = os.path.join(MODELS, "w600k_r50.onnx")
SWAP = os.path.join(MODELS, "inswapper_128.onnx")

# ArcFace 5-point template for a 112x112 crop
ARC112 = np.array(
    [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
     [41.5493, 92.3655], [70.7299, 92.2041]], dtype=np.float64)


def umeyama(src, dst, estimate_scale=True):
    """Least-squares similarity transform mapping src -> dst (Umeyama 1991)."""
    src = np.asarray(src, np.float64)
    dst = np.asarray(dst, np.float64)
    n = src.shape[0]
    mu_s = src.mean(0)
    mu_d = dst.mean(0)
    s_c = src - mu_s
    d_c = dst - mu_d
    cov = d_c.T @ s_c / n
    u, d, vt = np.linalg.svd(cov)
    s = np.eye(2)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        s[1, 1] = -1.0
    r = u @ s @ vt
    if estimate_scale:
        var_s = (s_c ** 2).sum() / n
        scale = (d * np.diag(s)).sum() / var_s
    else:
        scale = 1.0
    t = mu_d - scale * (r @ mu_s)
    return np.concatenate([scale * r, t[:, None]], axis=1).astype(np.float32)


def template(size):
    return ARC112 * (size / 112.0)


def make_detector(w, h):
    d = cv2.FaceDetectorYN.create(DET, "", (w, h), score_threshold=0.5,
                                  nms_threshold=0.3, top_k=50)
    d.setInputSize((w, h))
    return d


def detect(det, img):
    h, w = img.shape[:2]
    det.setInputSize((w, h))
    _, faces = det.detect(img)
    if faces is None or len(faces) == 0:
        return []
    return sorted(faces, key=lambda f: f[2] * f[3], reverse=True)


def align(img, kps, size):
    M = umeyama(kps, template(size))
    out = cv2.warpAffine(img, M, (size, size), borderMode=cv2.BORDER_REPLICATE,
                         flags=cv2.INTER_LINEAR)
    return out, M


def face_mask(size):
    m = np.zeros((size, size), np.uint8)
    cv2.ellipse(m, (size // 2, int(size * 0.55)),
                (int(size * 0.44), int(size * 0.56)), 0, 0, 360, 255, -1)
    m = cv2.GaussianBlur(m, (0, 0), size * 0.05)
    return m


def match_colors(fake, tgt, mask, strength=0.85):
    """Reinhard-style transfer: full chroma match, partial luminance match."""
    m = mask > 64
    if m.sum() < 64:
        return fake
    lf = cv2.cvtColor(fake, cv2.COLOR_BGR2LAB).astype(np.float32)
    lt = cv2.cvtColor(tgt, cv2.COLOR_BGR2LAB).astype(np.float32)
    contrast = (0.35, 1.0, 1.0)  # L gets a gentler contrast match than a/b
    for c in range(3):
        f = lf[..., c][m]
        t = lt[..., c][m]
        sf = max(float(f.std()), 1.0)
        st = float(t.std())
        gain = (st / sf) ** contrast[c]
        mean_f = float(f.mean())
        mean_t = float(t.mean())
        new = (f - mean_f) * gain + mean_t
        lf[..., c][m] = f + (new - f) * strength
    return cv2.cvtColor(np.clip(lf, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="reference face image")
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--count", type=int, default=0, help="0 = every frame")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--blend", type=float, default=1.0, help="0..1 swap strength")
    ap.add_argument("--color", type=float, default=0.85,
                    help="0..1 strength of LAB colour match to the target face")
    ap.add_argument("--models", default=None,
                    help="folder with inswapper_128.onnx, w600k_r50.onnx and the YuNet model")
    a = ap.parse_args()

    global MODELS, DET, EMB, SWAP
    MODELS = find_models_dir(a.models)
    DET = os.path.join(MODELS, "face_detection_yunet_2023mar.onnx")
    EMB = os.path.join(MODELS, "w600k_r50.onnx")
    SWAP = os.path.join(MODELS, "inswapper_128.onnx")
    for p in (DET, EMB, SWAP):
        if not os.path.exists(p):
            sys.exit("missing model: " + p + "\nRun scripts\\download_models.ps1 -IncludeFaceswap "
                     "or pass --models <dir>.")
    print("models from", MODELS)

    so = ort.SessionOptions()
    so.log_severity_level = 3
    providers = ["CPUExecutionProvider"]
    emb_sess = ort.InferenceSession(EMB, so, providers=providers)
    swap_sess = ort.InferenceSession(SWAP, so, providers=providers)
    emap = numpy_helper.to_array(onnx.load(SWAP).graph.initializer[-1])
    print("ort", ort.__version__, "| emap", emap.shape,
          "| swap inputs", [i.name for i in swap_sess.get_inputs()])

    src = cv2.imread(a.src, cv2.IMREAD_COLOR)
    if src is None:
        sys.exit("cannot read source image " + a.src)
    s_faces = detect(make_detector(src.shape[1], src.shape[0]), src)
    if not s_faces:
        sys.exit("no face found in source image " + a.src)
    sb = s_faces[0]
    print("source %dx%d faces=%d bbox=%s score=%.2f"
          % (src.shape[1], src.shape[0], len(s_faces),
             sb[:4].astype(int).tolist(), float(sb[-1])))
    s_crop, _ = align(src, sb[4:14].reshape(5, 2), 112)
    dbg = os.path.join(os.path.dirname(os.path.abspath(a.out)), "last_src_crop.png")
    cv2.imwrite(dbg, s_crop)

    x = s_crop[:, :, ::-1].astype(np.float32)
    x = np.transpose((x / 255.0 - 0.5) / 0.5, (2, 0, 1))[None]
    e = emb_sess.run(None, {emb_sess.get_inputs()[0].name: x})[0].ravel()
    e = e / max(np.linalg.norm(e), 1e-6)
    latent = e[None] @ emap
    latent = (latent / max(np.linalg.norm(latent), 1e-6)).astype(np.float32)
    print("source embedding ready, |latent| =", round(float(np.linalg.norm(latent)), 3))

    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        sys.exit("cannot open video " + a.video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    print("video %dx%d %.2f fps %d frames" % (W, H, fps, total))

    det = make_detector(W, H)
    mk = face_mask(a.size)
    vw = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    if not vw.isOpened():
        sys.exit("cannot open writer " + a.out)

    i = done = missed = 0
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i < a.start:
            i += 1
            continue
        if a.count and done >= a.count:
            break
        faces = detect(det, frame)
        if faces:
            kps = faces[0][4:14].reshape(5, 2)
            tgt, M = align(frame, kps, a.size)
            blob = cv2.dnn.blobFromImage(tgt, 1.0 / 255.0, (a.size, a.size),
                                         (0, 0, 0), swapRB=True).astype(np.float32)
            fake = swap_sess.run(None, {"target": blob, "source": latent})[0][0]
            fake = np.clip(fake.transpose(1, 2, 0) * 255.0, 0, 255).astype(np.uint8)
            if a.color > 0:
                fake = match_colors(fake, tgt, mk, a.color)
            inv = cv2.invertAffineTransform(M)
            warped = cv2.warpAffine(fake, inv, (W, H), flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REPLICATE)
            mfull = cv2.warpAffine(mk, inv, (W, H), flags=cv2.INTER_LINEAR)
            alpha = (mfull.astype(np.float32) / 255.0)[:, :, None] * a.blend
            frame = np.clip(warped.astype(np.float32) * alpha
                            + frame.astype(np.float32) * (1 - alpha), 0, 255).astype(np.uint8)
        else:
            missed += 1
        vw.write(frame)
        done += 1
        i += 1
        if done % 25 == 0:
            el = time.time() - t0
            print("%d frames, %.2f fps, %.1fs" % (done, done / el, el))

    cap.release()
    vw.release()
    el = time.time() - t0
    print("DONE %d frames in %.1fs (%.2f fps), %d frames without a face -> %s"
          % (done, el, done / max(el, 1e-6), missed, a.out))


if __name__ == "__main__":
    main()
