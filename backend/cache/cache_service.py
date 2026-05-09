# STUB — replace with Agent 2's full implementation
from shared.models import CacheResult


def check_cache(prompt: str) -> CacheResult:
    return CacheResult(hit=False, response=None, similarity=0.0)


def store_in_cache(prompt: str, response: str) -> None:
    pass
