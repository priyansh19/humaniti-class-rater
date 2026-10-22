"""v2.2 (declared before its first run): candidates are ONLY proportional-odds ordinal logistic models
on 1 or 2 of the 7 frozen rubric criterion scores, lam in {1, 5}  (7 + 21 subsets x 2 = 56 candidates).
v2.1's pool of 1-D thresholds on ~60 raw features overfit: inner LOO picked noise features (0% outer).
Selection = inner LOO exact accuracy, then MAE, then fewer features, then stronger regularisation.

Legacy v2.1 docstring:
Model selection by inner leave-one-out over a GENERIC candidate set (added in v2.1, after the
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
    if name.startswith("ologit:"):
        from .ologit import fit as fit_ol
        _, lam, keys = name.split(":")
        m = fit_ol(rows, y, [k if "." in k else f"crit.{k}" for k in keys.split("+")], lam=float(lam))
        return OL(m) if m else None
    if name.startswith("ridge:"):
        crit = [{k: r.get(f"crit.{k}") for k in CRITERIA} for r in rows]
        return Ridge(fit_ridge(crit, y, list(CRITERIA), alpha=float(name.split(":")[1])))
    return fit_threshold(rows, y, name)


LAMS = (1.0, 5.0)


def candidates_v22() -> list[str]:
    from itertools import combinations

    from .rubric import FROZEN_KEYS
    subs = [(k,) for k in FROZEN_KEYS] + list(combinations(FROZEN_KEYS, 2))
    return [f"ologit:{lam}:{'+'.join(s)}" for s in subs for lam in LAMS]


def candidates_probes(probe_keys: list[str], with_criteria: bool = True) -> list[str]:
    """Declared before the first embeddings run: v2.2 set, plus ordinal-logit on 1 probe, plus 1 criterion + 1 probe.
    with_criteria=False gives the probe-only set (1 or 2 probes)."""
    from itertools import combinations

    from .rubric import FROZEN_KEYS
    if with_criteria:
        subs = [(p,) for p in probe_keys] + [(c, p) for c in FROZEN_KEYS for p in probe_keys]
        return candidates_v22() + [f"ologit:{lam}:{'+'.join(s)}" for s in subs for lam in LAMS]
    subs = [(p,) for p in probe_keys] + list(combinations(probe_keys, 2))
    return [f"ologit:{lam}:{'+'.join(s)}" for s in subs for lam in LAMS]


@dataclass
class OL:
    model: object

    def predict(self, x: dict):
        return self.model.predict(x)


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


def select(rows: list[dict], y: list[str], version: str = "v2.2", pool: list[str] | None = None) -> tuple[str, object, dict]:
    if pool is not None:
        scores = {c: inner_score(c, rows, y) for c in pool}
        best = max(scores, key=lambda c: (scores[c][0], -scores[c][1], -c.count("+"), float(c.split(":")[1])))
    elif version == "v2.1":
        scores = {c: inner_score(c, rows, y) for c in candidates(rows)}
        best = max(scores, key=lambda c: (scores[c][0], -scores[c][1], c.startswith("ridge")))
    else:
        scores = {c: inner_score(c, rows, y) for c in candidates_v22()}
        best = max(scores, key=lambda c: (scores[c][0], -scores[c][1], -c.count("+"), float(c.split(":")[1])))
    return best, _fit_candidate(best, rows, y), scores


def to_json(name: str, model) -> str:
    if isinstance(model, OL):
        return json.dumps({"kind": "ologit", "name": name, "model": asdict(model.model)}, indent=1)
    if isinstance(model, Ridge):
        return json.dumps({"kind": "ridge", "name": name, "model": asdict(model.model)}, indent=1)
    return json.dumps({"kind": "threshold", "name": name, "model": asdict(model)}, indent=1)


def from_json(s: str):
    d = json.loads(s)
    if d.get("kind") == "ologit":
        from .ologit import OLogit
        return OL(OLogit(**d["model"]))
    if d.get("kind") == "threshold":
        return Threshold(**d["model"])
    if d.get("kind") == "ridge":
        return Ridge(OrdinalModel(**d["model"]))
    return Ridge(OrdinalModel(**d))      # legacy plain ridge json
