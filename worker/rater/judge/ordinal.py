"""Ordinal regression on criterion scores (ridge on 0..3 targets). FROZEN family: alpha=2.0.

Missing criteria are imputed with the training mean. Fit uses only the rows passed in."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np

from ..models import LABELS

ALPHA = 2.0


@dataclass
class OrdinalModel:
    keys: list[str]
    mean: list[float]
    std: list[float]
    coef: list[float]
    intercept: float

    def score(self, crit: dict[str, float | None]) -> float:
        x = np.array([(crit.get(k) if crit.get(k) is not None else m) for k, m in zip(self.keys, self.mean, strict=True)])
        z = (x - np.array(self.mean)) / np.array(self.std)
        return float(self.intercept + z @ np.array(self.coef))

    def predict(self, crit: dict[str, float | None]) -> tuple[str, float, float]:
        """Returns (label, continuous score 0..3, confidence 0..1)."""
        s = self.score(crit)
        idx = int(np.clip(np.rint(s), 0, 3))
        conf = float(np.clip(1 - 2 * abs(s - np.clip(np.rint(s), 0, 3)), 0.2, 1.0))
        if s < -0.5 or s > 3.5:
            conf = 1.0
        return LABELS[idx], s, round(conf, 2)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=1)

    @classmethod
    def from_json(cls, s: str) -> OrdinalModel:
        return cls(**json.loads(s))


def fit(rows: list[dict[str, float | None]], labels: list[str], keys: list[str], alpha: float = ALPHA) -> OrdinalModel:
    keys = [k for k in keys if any(r.get(k) is not None for r in rows)]
    X = np.array([[r.get(k) if r.get(k) is not None else np.nan for k in keys] for r in rows], float)
    mean = np.nanmean(X, 0)
    X = np.where(np.isnan(X), mean, X)
    std = X.std(0)
    std[std < 1e-6] = 1.0
    Z = (X - mean) / std
    y = np.array([LABELS.index(lab) for lab in labels], float)
    b0 = y.mean()
    coef = np.linalg.solve(Z.T @ Z + alpha * np.eye(len(keys)), Z.T @ (y - b0))
    return OrdinalModel(keys, mean.tolist(), std.tolist(), coef.tolist(), float(b0))
