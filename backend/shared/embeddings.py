"""
embeddings.py — Shared local embedding model (all-MiniLM-L6-v2, 384 dims).

Runs the model through fastembed (ONNX Runtime) instead of sentence-transformers
so the deployment doesn't pull in PyTorch (~5 GB with CUDA), which is far beyond
Vercel's 500 MB function limit. Same model, same 384-dim L2-normalized vectors,
so existing Pinecone entries stay compatible.

The model files (~90 MB) are downloaded on first use into a writable cache dir
(/tmp on serverless hosts) and reused for the lifetime of the instance.
"""
from __future__ import annotations
import logging
import os
import tempfile
from typing import Optional, Sequence

import numpy as np
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_CACHE_DIR = os.environ.get(
    "FASTEMBED_CACHE_PATH", os.path.join(tempfile.gettempdir(), "fastembed_cache")
)

_model: Optional[TextEmbedding] = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        logger.info("Loading embedding model '%s' (cold start)", MODEL_NAME)
        _model = TextEmbedding(MODEL_NAME, cache_dir=_CACHE_DIR)
    return _model


def encode(texts: Sequence[str]) -> np.ndarray:
    """Embed a batch of texts. Returns an (n, 384) array of L2-normalized rows."""
    vecs = np.array(list(_get_model().embed(list(texts))), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-12, None)


def encode_one(text: str) -> np.ndarray:
    """Embed a single text. Returns a 384-dim L2-normalized vector."""
    return encode([text])[0]
