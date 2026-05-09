"""
embedder.py — Generarea embedding-urilor via Azure OpenAI

Un "embedding" este reprezentarea numerica a unui text:
o lista de 1536 numere (float) care captureaza sensul textului.
Doua texte cu sens similar au vectori apropiati numeric.

Noi folosim modelul "text-embedding-3-small" — cel mai ieftin si rapid.
"""

import logging
import os
import time
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Clientul AzureOpenAI se creeaza O SINGURA DATA la nivel de modul,
# nu la fiecare apel de functie.
#
# De ce? Azure Functions refoloseste aceeasi instanta Python ("warm instance")
# intre request-uri. Daca am crea clientul la fiecare request, am face
# un nou handshake TLS de fiecare data — asta adauga ~50-100ms inutil.
#
# os.environ.get("...") citeste variabilele de mediu (env vars).
# Cheile Azure NU se pun niciodata hardcodat in cod — sunt in env vars.
# -------------------------------------------------------------------
_endpoint = os.environ.get("SWEDEN_ENDPOINT", "")
_key = os.environ.get("SWEDEN_KEY", "")

print(f"[EMBEDDER] ===== INIT =====")
print(f"[EMBEDDER] Endpoint: {_endpoint or 'MISSING!'}")
print(f"[EMBEDDER] API Key: {'SET (' + _key[:8] + '...)' if _key else 'MISSING!'}")

_client = AzureOpenAI(
    azure_endpoint=_endpoint,
    api_key=_key,
    api_version="2024-02-01",
)

# Modelul de embedding — nu schimba asta, "large" e de 5x mai scump fara beneficiu
_EMBEDDING_MODEL = "text-embedding-3-small"

print(f"[EMBEDDER] Model: {_EMBEDDING_MODEL}")
print(f"[EMBEDDER] Client gata de folosit.")
print(f"[EMBEDDER] ================")


def get_embedding(text: str) -> list[float]:
    """
    Trimite textul la Azure OpenAI si primeste inapoi vectorul de 1536 numere.

    Exemplu:
      get_embedding("What is the capital of France?")
      → [0.012, -0.043, 0.071, -0.002, ...]  # 1536 valori

    Timp tipic: 150-250ms (apel HTTP la Azure).
    Aceasta este bottleneck-ul de performanta — nu putem face mai rapid.
    """
    text_preview = text[:60] + ("..." if len(text) > 60 else "")
    print(f"[EMBEDDER] -> get_embedding() apelat")
    print(f"[EMBEDDER]    Text ({len(text)} chars): {text_preview!r}")

    start = time.perf_counter()
    try:
        response = _client.embeddings.create(
            input=text,
            model=_EMBEDDING_MODEL,
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[EMBEDDER] !! EROARE dupa {elapsed_ms:.0f}ms: {type(exc).__name__}: {exc}")
        raise

    elapsed_ms = (time.perf_counter() - start) * 1000

    # response.data este o lista; [0] e primul (si singurul) rezultat.
    # .embedding este lista de floats.
    embedding = response.data[0].embedding

    print(f"[EMBEDDER] <- get_embedding() OK in {elapsed_ms:.0f}ms")
    print(f"[EMBEDDER]    Vector: {len(embedding)} dimensiuni, primele 3 valori: {embedding[:3]}")

    logger.debug("Embedding generat: %d dimensiuni pentru text de %d chars", len(embedding), len(text))
    return embedding
