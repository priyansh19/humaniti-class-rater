"""Audio quality features from 8 kHz mono PCM."""
from __future__ import annotations

import numpy as np

from .media import pcm

FEATURE_NAMES = ["silence_frac", "loudness_db_median", "dynamic_range_db", "clip_frac", "noisiness"]


def compute_from_signal(x: np.ndarray, rate: int = 8000) -> dict[str, float]:
    n = x.size // rate
    if n < 5:
        return {k: 0.0 for k in FEATURE_NAMES}
    frames = x[: n * rate].reshape(n, rate)
    rms = np.sqrt((frames ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    voiced = db > np.percentile(db, 95) - 30
    spec = np.abs(np.fft.rfft(frames[voiced][:600] if voiced.any() else frames[:600], axis=1)) + 1e-9
    flat = np.exp(np.log(spec).mean(1)) / spec.mean(1)        # spectral flatness: ~1 noise, ~0 tonal/speech
    return {
        "silence_frac": round(float(1 - voiced.mean()), 4),
        "loudness_db_median": round(float(np.median(db[voiced])) if voiced.any() else -90.0, 2),
        "dynamic_range_db": round(float(np.percentile(db, 95) - np.percentile(db, 10)), 2),
        "clip_frac": round(float((np.abs(x) > 0.99).mean()), 6),
        "noisiness": round(float(np.median(flat)), 4),
    }


def compute(path: str) -> dict[str, float]:
    return compute_from_signal(pcm(path, 8000), 8000)
