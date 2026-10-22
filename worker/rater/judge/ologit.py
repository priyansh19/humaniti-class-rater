"""Cumulative-link (proportional-odds) ordinal logistic regression in numpy.

P(y <= k | x) = sigmoid(theta_k - w.x), k = 0..2, with theta increasing. L2 on w (strength lam).
Features are standardised on the training rows. Small and deterministic: suitable for n ~ 10."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..models import LABELS


def _sig(z):
    return 1 / (1 + np.exp(-z))


@dataclass
class OLogit:
    keys: list[str]
    mu: list[float]
    sd: list[float]
    w: list[float]
    theta: list[float]

    def proba(self, x: dict) -> np.ndarray:
        v = np.array([(x.get(k) if x.get(k) is not None else m) for k, m in zip(self.keys, self.mu, strict=True)], float)
        z = float(np.dot(self.w, (v - np.array(self.mu)) / np.array(self.sd)))
        cum = np.concatenate([_sig(np.array(self.theta) - z), [1.0]])
        return np.diff(np.concatenate([[0.0], cum]))

    def predict(self, x: dict) -> tuple[str, float, float]:
        p = self.proba(x)
        k = int(np.argmax(p))
        return LABELS[k], float(np.dot(p, np.arange(4))), round(float(p[k]), 2)


def fit(rows: list[dict], y: list[str], keys: list[str], lam: float = 1.0) -> OLogit | None:
    from scipy.optimize import minimize  # fit-time only; predict needs numpy alone
    X = np.array([[np.nan if r.get(k) is None else r.get(k) for k in keys] for r in rows], float)
    if np.isnan(X).all(0).any():
        return None                                # a criterion never observed with these modalities
    mu = np.nanmean(X, 0)
    X = np.where(np.isnan(X), mu, X)
    sd = X.std(0) + 1e-6
    Z = (X - mu) / sd
    yi = np.array([LABELS.index(t) for t in y])
    m, idx = len(keys), np.arange(len(yi))

    def unpack(q):
        t0, d = q[m], q[m + 1:]
        return q[:m], np.array([t0, t0 + np.exp(d[0]), t0 + np.exp(d[0]) + np.exp(d[1])])

    def nll(q):
        w, th = unpack(q)
        cum = np.column_stack([np.zeros(len(yi)), _sig(th[None, :] - (Z @ w)[:, None]), np.ones(len(yi))])
        p = cum[idx, yi + 1] - cum[idx, yi]
        return -np.log(np.clip(p, 1e-12, None)).sum() + 0.5 * lam * (w @ w)

    q = minimize(nll, np.concatenate([np.zeros(m), [-1.0, 0.0, 0.0]]), method="L-BFGS-B").x
    w, th = unpack(q)
    return OLogit(list(keys), mu.tolist(), sd.tolist(), w.tolist(), th.tolist())
