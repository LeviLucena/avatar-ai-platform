"""Local, dependency-free text embeddings (hashing trick over unigrams + bigrams).

Anthropic has no embeddings endpoint; in production swap `embed` for Voyage AI /
OpenAI embeddings and move vectors to pgvector. The rest of the platform only
depends on `embed()` and `cosine()`, so that swap is isolated to this file.
"""
import re
import zlib

import numpy as np

DIM = 512
STOP = set(
    "a an the and or but if of to in on at for with from by is are was were be been it its this that these those "
    "i me my we our you your they their he she him her as so not no do did does have has had can could would "
    "will just very really also than then there here when what which who how about into out up down over after "
    "before them us am get got".split()
)
_tok = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return [t for t in _tok.findall(text.lower()) if t not in STOP and len(t) > 1]


def embed(text: str) -> list[float]:
    toks = _tokens(text)
    feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    v = np.zeros(DIM, dtype=np.float32)
    for f in feats:
        h = zlib.crc32(f.encode())
        v[h % DIM] += 1.0 if (h >> 16) & 1 else -1.0
    v = np.sign(v) * np.sqrt(np.abs(v))  # sublinear tf
    n = np.linalg.norm(v)
    return (v / n).tolist() if n else v.tolist()


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    d = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(va @ vb / d) if d else 0.0


def mean_vector(old: list[float], n_old: int, new: list[float]) -> list[float]:
    if not old or n_old <= 0:
        return list(new)
    m = (np.asarray(old) * n_old + np.asarray(new)) / (n_old + 1)
    nrm = np.linalg.norm(m)
    return (m / nrm).tolist() if nrm else m.tolist()
