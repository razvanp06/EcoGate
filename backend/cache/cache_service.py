import hashlib
import logging
from datetime import datetime, timezone

from shared.models import CacheResult
from cache.embedder import get_embedding
from cache.vector_store import add_to_store, query_store, key_exists

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.92


def check_cache(prompt: str) -> CacheResult:
    try:
        embedding = get_embedding(prompt)
    except Exception as exc:
        logger.error("Embedding failed, treating as cache miss: %s", exc)
        return CacheResult(hit=False, response=None, similarity=0.0)

    try:
        results = query_store(embedding, n_results=1)
    except Exception as exc:
        logger.error("Vector store query failed, treating as cache miss: %s", exc)
        return CacheResult(hit=False, response=None, similarity=0.0)

    if not results.matches:
        return CacheResult(hit=False, response=None, similarity=0.0)

    similarity = results.matches[0].score

    if similarity >= SIMILARITY_THRESHOLD:
        cached_response = results.matches[0].metadata["response"]
        matched_prompt = results.matches[0].metadata["prompt"]
        logger.info("Cache HIT — similarity=%.3f matched=%r", similarity, matched_prompt[:80])
        return CacheResult(hit=True, response=cached_response, similarity=similarity)

    logger.info("Cache MISS — similarity=%.3f below threshold %.2f", similarity, SIMILARITY_THRESHOLD)
    return CacheResult(hit=False, response=None, similarity=similarity)


def store_in_cache(prompt: str, response: str) -> None:
    cache_key = hashlib.md5(prompt.strip().lower().encode()).hexdigest()

    try:
        if key_exists(cache_key):
            logger.debug("Prompt already cached (key=%s), skipping.", cache_key)
            return
    except Exception as exc:
        logger.error("store_in_cache: vector store unavailable, not storing: %s", exc)
        return

    try:
        embedding = get_embedding(prompt)
    except Exception as exc:
        logger.error("store_in_cache: embedding failed, not storing: %s", exc)
        return

    try:
        add_to_store(
            cache_key=cache_key,
            embedding=embedding,
            prompt=prompt,
            response=response,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("Stored in cache: key=%s prompt=%r", cache_key, prompt[:60])
    except Exception as exc:
        logger.error("store_in_cache: upsert failed: %s", exc)
