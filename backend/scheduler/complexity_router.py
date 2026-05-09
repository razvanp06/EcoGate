from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TRAINING_DATA_PATH = Path(__file__).parent / "training_data.json"

# Bias toward the cheap model: tier 2 only when complex-similarity beats
# simple-similarity by at least this margin. Increase to route more to tier 1.
TIER_2_MARGIN = 0.0

MODEL_FOR_TIER = {
    1: "o4-mini",
    2: "gpt-4o",
}

_model: Optional[SentenceTransformer] = None
_simple_embs: Optional[np.ndarray] = None
_complex_embs: Optional[np.ndarray] = None
_training_data: Optional[dict] = None


def _load_training_data() -> dict:
    global _training_data
    if _training_data is None:
        with open(TRAINING_DATA_PATH, "r", encoding="utf-8") as f:
            _training_data = json.load(f)
        logger.info(
            "Training data loaded: %d simple, %d complex examples",
            len(_training_data["simple"]),
            len(_training_data["complex"]),
        )
    return _training_data


def _ensure_initialized() -> None:
    """Lazy-load the embedding model and pre-compute example embeddings.
    Runs once per process."""
    global _model, _simple_embs, _complex_embs
    if _model is not None:
        return

    data = _load_training_data()
    logger.info("Loading sentence-transformer '%s' (cold start)", EMBEDDING_MODEL_NAME)
    t0 = time.perf_counter()
    _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    _simple_embs = _model.encode(
        data["simple"], normalize_embeddings=True, show_progress_bar=False
    )
    _complex_embs = _model.encode(
        data["complex"], normalize_embeddings=True, show_progress_bar=False
    )
    logger.info(
        "Model ready in %.2fs (%d simple + %d complex example embeddings cached)",
        time.perf_counter() - t0,
        len(_simple_embs),
        len(_complex_embs),
    )


def _cosine_similarities(prompt_emb: np.ndarray, examples: np.ndarray) -> np.ndarray:
    # Both inputs are L2-normalized → dot product == cosine similarity
    return examples @ prompt_emb


def score_prompt(prompt: str) -> dict:
    """Returns a transparent breakdown of the routing decision.
    Used for logging and demo explainability."""
    _ensure_initialized()
    t0 = time.perf_counter()
    prompt_emb = _model.encode(prompt, normalize_embeddings=True, show_progress_bar=False)

    sim_simple = _cosine_similarities(prompt_emb, _simple_embs)
    sim_complex = _cosine_similarities(prompt_emb, _complex_embs)

    mean_simple = float(sim_simple.mean())
    mean_complex = float(sim_complex.mean())
    max_simple = float(sim_simple.max())
    max_complex = float(sim_complex.max())

    tier = 2 if (mean_complex - mean_simple) > TIER_2_MARGIN else 1
    elapsed_ms = (time.perf_counter() - t0) * 1000

    preview = prompt if len(prompt) <= 60 else prompt[:57] + "..."
    logger.info(
        "Classified tier=%d margin=%+0.3f (%.1fms) :: %s",
        tier, mean_complex - mean_simple, elapsed_ms, preview,
    )
    logger.debug(
        "Score breakdown — mean_simple=%.3f mean_complex=%.3f max_simple=%.3f max_complex=%.3f",
        mean_simple, mean_complex, max_simple, max_complex,
    )

    return {
        "tier": tier,
        "mean_simple": mean_simple,
        "mean_complex": mean_complex,
        "max_simple": max_simple,
        "max_complex": max_complex,
        "margin": mean_complex - mean_simple,
    }


def classify_complexity(prompt: str) -> int:
    """Returns 1 (o4-mini) or 2 (gpt-4o). Per-request, stateless."""
    return score_prompt(prompt)["tier"]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Silence noisy third-party libraries during self-tests
    for noisy in ("sentence_transformers", "httpx", "urllib3", "filelock", "huggingface_hub"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    data = _load_training_data()
    test_cases = data.get("test_cases", [])

    print(f"Loading model '{EMBEDDING_MODEL_NAME}'...")
    _ensure_initialized()
    print(f"Loaded. Simple examples: {len(data['simple'])}, complex: {len(data['complex'])}")
    print()

    correct = 0
    for case in test_cases:
        result = score_prompt(case["prompt"])
        ok = result["tier"] == case["expected_tier"]
        correct += ok
        marker = "OK  " if ok else "FAIL"
        preview = case["prompt"] if len(case["prompt"]) <= 60 else case["prompt"][:57] + "..."
        print(
            f"[{marker}] tier={result['tier']} expected={case['expected_tier']} "
            f"margin={result['margin']:+.3f} :: {preview}"
        )

    print()
    print(f"Accuracy: {correct}/{len(test_cases)}")
