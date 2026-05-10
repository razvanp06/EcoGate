"""
embedder.py — Local embeddings via sentence-transformers (all-MiniLM-L6-v2, 384 dims)
Same model already used by the complexity router — no extra download needed.
"""

import logging
import time
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def get_embedding(text: str) -> list[float]:
    start = time.perf_counter()
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True).tolist()
    logger.debug("Embedding: %d dims in %.0fms", len(embedding), (time.perf_counter() - start) * 1000)
    return embedding
