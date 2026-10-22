"""Model selection by inner leave-one-out over a GENERIC candidate set (added in v2.1, after the
pre-registered ridge model failed; see docs/EVAL.md). Selection only ever sees training rows.

Candidates:
  * threshold(f): 1-D ordinal model on one feature f (any raw feature or criterion score); cut-points
    are midpoints between adjacent training-class means, direction from the sign of correlation.
  * ridge(alpha): ridge-ordinal over all 7 criterion scores, alpha in {1, 10, 100}.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np

from ..models import LABELS
from .ordinal import OrdinalModel
from .ordinal import fit as fit_ridge
from .rubric import CRITERIA, criterion_scores

ALPHAS = (1.0, 10.0, 100.0)


def flat(features: dict[str, dict[str, float]]) -> dict[str, float | None]:
    out: dict[str, float | None] = {f"{m}.{k}": v for m, d in features.items() for k, v in d.items()}
    out.update({f"crit.{k}": v for k, v in criterion_scores(features).items()})
    return out


@dataclass
class Threshold:
    feature: str
    sign: float
    cuts: list[float]
    fill: float

    def predict(self, x: dict) -> tuple[str, float, float]:
        v = x.get(self.feature)
        v = self.fill if v is None else v
        s = self.sign * v
        idx = int(np.searchsorted(self.cuts, s))
        edges = [c for c in self.cuts if np.isfinite(c)]
        margin = min((abs(s - c) for c in edges), default=1.0)
        scale = (max(edges) - min(edges)) / 3 if len(edges) > 1 else 1.0
        return LABELS[idx], float(idx), round(float(np.clip(0.4 + margin / (scale + 1e-9), 0.4, 0.95)), 2)


def fit_threshold(rows: list[dict], y: list[str], feature: str) -> Threshold | None:
    vals = [r.get(feature) for r in rows]
    known = [v for v in vals if v is not None]
    if len(known) < len(rows) or np.std(known) < 1e-9:
        return None
    yi = np.array([LABELS.index(t) for t in y], float)
    v = np.array(known, float)
    sign = 1.0 if np.corrcoef(v, yi)[0, 1] >= 0 else -1.0
    means = {k: float(np.mean(sign * v[yi == k])) for k in range(4) if (yi == k).any()}
    cuts = []
    for k in range(3):
        a, b = means.get(k), means.get(k + 1)
        cuts.append((a + b) / 2 if a is not None and b is not None else (np.inf if b is None else -np.inf))
    return Threshold(feature, sign, sorted(cuts), float(np.mean(v)))


@dataclass
class Ridge:
    model: OrdinalModel

    def predict(self, x: dict) -> tuple[str, float, float]:
        return self.model.predict({k: x.get(f"crit.{k}") for k in CRITERIA})


def _fit_candidate(name: str, rows: list[dict], y: list[str]):
    if name.startswith("ridge:"):
        crit = [{k: r.get(f"crit.{k}") for k in CRITERIA} for r in rows]
        return Ridge(fit_ridge(crit, y, list(CRITERIA), alpha=float(name.split(":")[1])))
    return fit_threshold(rows, y, name)


def candidates(rows: list[dict]) -> list[str]:
    keys = sorted(set().union(*[r.keys() for r in rows]))
    return [f"ridge:{a}" for a in ALPHAS] + [k for k in keys if all(r.get(k) is not None for r in rows)]


def inner_score(name: str, rows: list[dict], y: list[str]) -> tuple[float, float]:
    hits, err = 0, 0.0
    for i in range(len(rows)):
        m = _fit_candidate(name, rows[:i] + rows[i + 1:], y[:i] + y[i + 1:])
        if m is None:
            return (-1, 9)
        p = m.predict(rows[i])[0]
        hits += p == y[i]
        err += abs(LABELS.index(p) - LABELS.index(y[i]))
    return hits / len(rows), err / len(rows)


def select(rows: list[dict], y: list[str]) -> tuple[str, object, dict]:
    scores = {c: inner_score(c, rows, y) for c in candidates(rows)}
    best = max(scores, key=lambda c: (scores[c][0], -scores[c][1], c.startswith("ridge")))
    return best, _fit_candidate(best, rows, y), scores


def to_json(name: str, model) -> str:
    if isinstance(model, Ridge):
        return json.dumps({"kind": "ridge", "name": name, "model": asdict(model.model)}, indent=1)
    return json.dumps({"kind": "threshold", "name": name, "model": asdict(model)}, indent=1)


def from_json(s: str):
    d = json.loads(s)
    if d.get("kind") == "threshold":
        return Threshold(**d["model"])
    if d.get("kind") == "ridge":
        return Ridge(OrdinalModel(**d["model"]))
    return Ridge(OrdinalModel(**d))      # legacy plain ridge json
