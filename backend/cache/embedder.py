"""
embedder.py — Local embeddings (all-MiniLM-L6-v2, 384 dims) via shared.embeddings.
Same model instance as the complexity router — no extra download needed.
"""

import logging
import time
from shared.embeddings import encode_one

logger = logging.getLogger(__name__)


def get_embedding(text: str) -> list[float]:
    start = time.perf_counter()
    embedding = encode_one(text).tolist()
    logger.debug("Embedding: %d dims in %.0fms", len(embedding), (time.perf_counter() - start) * 1000)
    return embedding
