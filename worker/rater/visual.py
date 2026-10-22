"""Frame-layout classification and presentation features (spec: analysis.md §7).

Zoom recordings show one of: the active speaker's video, a camera-off name tile
(near-uniform dark grey), or a screen share (e.g. a chess board). Camera-off tiles that
coincide with the *tutor* speaking (from transcript timestamps) mean the tutor's camera was off.
"""
from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Iterable
from functools import lru_cache

import numpy as np

from .models import Utterance

FEATURE_NAMES = ["frames", "video_frac", "camera_off_frac", "screen_share_frac", "tutor_camera_off_frac",
                 "video_brightness", "face_in_video_frac", "brand_background_frac"]


@lru_cache(maxsize=1)
def _face():
    import cv2
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def classify(img: np.ndarray) -> str:
    import cv2
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    med = float(np.median(g))
    near = float((np.abs(g.astype(int) - med) < 10).mean())
    edges = float((cv2.Canny(g, 80, 160) > 0).mean())
    if near > 0.85 and med < 90 and edges < 0.02:
        return "camera_off"
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    colourful = float(((hsv[..., 1] > 60) & (hsv[..., 2] > 60)).mean())
    if edges > 0.09 or (colourful > 0.10 and edges > 0.07):
        return "screen_share"
    return "video"


def brand_background(img: np.ndarray) -> bool:
    """8x8 virtual background: mostly dark with large bright blocks in the upper half (logo)."""
    import cv2
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    top = g[: g.shape[0] // 2]
    return float((g < 50).mean()) > 0.35 and 0.06 < float((top > 190).mean()) < 0.45


def has_face(img: np.ndarray) -> bool:
    import cv2
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = min(g.shape[:2])
    return len(_face().detectMultiScale(g, 1.1, 5, minSize=(m // 8, m // 8))) > 0


def tutor_speaking_lookup(utts: list[Utterance]) -> Callable[[float], bool | None]:
    if not utts:
        return lambda t: None
    starts = [u.start for u in utts]

    def f(t: float) -> bool | None:
        i = bisect_right(starts, t) - 1
        if i < 0:
            return None
        u = utts[i]
        if u.start - 1 <= t <= u.end + 2:
            return u.role == "tutor"
        return None
    return f


def compute(frame_iter: Iterable[tuple[float, np.ndarray]], utts: list[Utterance] | None = None,
            on_frame: Callable[[int], None] | None = None) -> dict[str, float]:
    import cv2
    speaking = tutor_speaking_lookup(utts or [])
    kinds, bright, faces, brand = [], [], [], []
    tutor_frames = tutor_off = 0
    for i, (t, img) in enumerate(frame_iter):
        k = classify(img)
        kinds.append(k)
        if k == "video":
            bright.append(float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean()))
            faces.append(has_face(img))
            brand.append(brand_background(img))
        ts = speaking(t)
        if ts:
            tutor_frames += 1
            tutor_off += k == "camera_off"
        if on_frame:
            on_frame(i)
    n = max(len(kinds), 1)
    return {
        "frames": float(len(kinds)),
        "video_frac": round(kinds.count("video") / n, 4),
        "camera_off_frac": round(kinds.count("camera_off") / n, 4),
        "screen_share_frac": round(kinds.count("screen_share") / n, 4),
        "tutor_camera_off_frac": round(tutor_off / tutor_frames, 4) if tutor_frames else 0.0,
        "video_brightness": round(float(np.mean(bright)), 2) if bright else 0.0,
        "face_in_video_frac": round(float(np.mean(faces)), 4) if faces else 0.0,
        "brand_background_frac": round(float(np.mean(brand)), 4) if brand else 0.0,
    }
