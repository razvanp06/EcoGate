import logging
import os
import time
from pinecone import Pinecone

logger = logging.getLogger(__name__)

_index = None


def _get_index():
    """Connect lazily so a missing/invalid Pinecone config degrades to cache
    misses instead of crashing the whole app at import time."""
    global _index
    if _index is None:
        api_key = os.environ.get("PINECONE_API_KEY", "")
        index_host = os.environ.get("PINECONE_INDEX_HOST", "")
        if not api_key or not index_host:
            raise RuntimeError("PINECONE_API_KEY / PINECONE_INDEX_HOST not set")
        _index = Pinecone(api_key=api_key).Index(host=index_host)
        logger.info("Pinecone index connected: %s", index_host)
    return _index


def add_to_store(
    cache_key: str,
    embedding: list[float],
    prompt: str,
    response: str,
    timestamp: str,
) -> None:
    logger.debug("Pinecone upsert: key=%s prompt=%r", cache_key, prompt[:60])
    start = time.perf_counter()
    _get_index().upsert(vectors=[{
        "id": cache_key,
        "values": embedding,
        "metadata": {
            "prompt": prompt,
            "response": response,
            "timestamp": timestamp,
        },
    }])
    logger.debug("Pinecone upsert OK in %.0fms", (time.perf_counter() - start) * 1000)


def query_store(embedding: list[float], n_results: int = 1):
    start = time.perf_counter()
    results = _get_index().query(
        vector=embedding,
        top_k=n_results,
        include_metadata=True,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    n = len(results.matches) if hasattr(results, "matches") else 0
    logger.debug("Pinecone query: %d match(es) in %.0fms", n, elapsed_ms)
    return results


def key_exists(cache_key: str) -> bool:
    result = _get_index().fetch(ids=[cache_key])
    return len(result.vectors) > 0
