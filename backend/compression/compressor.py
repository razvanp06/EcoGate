# STUB — replace with Agent 3's full implementation
import tiktoken
from shared.models import CompressionResult

_encoder = tiktoken.get_encoding("cl100k_base")


def compress_prompt(prompt: str) -> CompressionResult:
    tokens = len(_encoder.encode(prompt))
    return CompressionResult(
        compressed_prompt=prompt,
        original_tokens=tokens,
        compressed_tokens=tokens,
        ratio=1.0,
        rules_applied=[],
    )
