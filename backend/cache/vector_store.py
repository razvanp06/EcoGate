"""
vector_store.py — Pinecone wrapper

Pinecone este baza de date vectoriala hostata in cloud.
Inlocuieste ChromaDB local — datele persista indiferent de restart-uri
si sunt accesibile de pe orice instanta Azure Functions.

Diferenta fata de ChromaDB:
  - ChromaDB: rula pe acelasi server, date in /tmp/ (se sterg la restart)
  - Pinecone: serviciu extern, date pe serverele lor (persistent, shared)
"""

import logging
import os
import time
from pinecone import Pinecone

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Initializam clientul Pinecone o singura data la nivel de modul.
# El citeste cheia API si host-ul din variabile de mediu.
#
# pc.Index(host=...) conecteaza direct la indexul nostru "ecogate-cache"
# fara sa mai intrebe serverul central Pinecone — mai rapid.
# -------------------------------------------------------------------
_api_key = os.environ.get("PINECONE_API_KEY", "")
_index_host = os.environ.get("PINECONE_INDEX_HOST", "")

print(f"[PINECONE] ===== INIT =====")
print(f"[PINECONE] Host: {_index_host or 'MISSING!'}")
print(f"[PINECONE] API Key: {'SET (' + _api_key[:8] + '...)' if _api_key else 'MISSING!'}")

_pc = Pinecone(api_key=_api_key)
_index = _pc.Index(host=_index_host)

print(f"[PINECONE] Client conectat la index.")
print(f"[PINECONE] ================")

logger.info("Pinecone index conectat: %s", _index_host)


def add_to_store(
    cache_key: str,
    embedding: list[float],
    prompt: str,
    response: str,
    timestamp: str,
) -> None:
    """
    Adauga un vector in Pinecone.

    Pinecone numeste intrarile "vectors". Fiecare vector are:
      id       — cheia unica (md5 al prompt-ului)
      values   — vectorul numeric (1536 numere)
      metadata — date extra: promptul original si raspunsul
    """
    prompt_preview = prompt[:60] + ("..." if len(prompt) > 60 else "")
    response_preview = response[:60] + ("..." if len(response) > 60 else "")

    print(f"[PINECONE] -> add_to_store()")
    print(f"[PINECONE]    key: {cache_key}")
    print(f"[PINECONE]    prompt: {prompt_preview!r}")
    print(f"[PINECONE]    response: {response_preview!r}")
    print(f"[PINECONE]    embedding: {len(embedding)} dim")

    start = time.perf_counter()
    try:
        _index.upsert(vectors=[{
            "id": cache_key,
            "values": embedding,
            "metadata": {
                "prompt": prompt,
                "response": response,
                "timestamp": timestamp,
            },
        }])
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[PINECONE] !! upsert EROARE dupa {elapsed_ms:.0f}ms: {type(exc).__name__}: {exc}")
        raise

    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"[PINECONE] <- add_to_store() OK in {elapsed_ms:.0f}ms")
    logger.debug("Stocat in Pinecone: key=%s", cache_key)


def query_store(embedding: list[float], n_results: int = 1) -> dict:
    """
    Cauta in Pinecone cel mai apropiat vector de cel primit.

    Returneaza un dictionar cu cheia "matches" — o lista de rezultate.
    Fiecare rezultat are:
      id       — cheia intrarii gasite
      score    — similaritatea cosinus (0.0 = complet diferit, 1.0 = identic)
      metadata — promptul original si raspunsul stocat

    IMPORTANT: Pinecone returneaza direct SIMILARITATEA (score),
    nu distanta ca ChromaDB. Nu mai trebuie sa facem "1 - distance".
    """
    print(f"[PINECONE] -> query_store(top_k={n_results}, embedding_dim={len(embedding)})")

    start = time.perf_counter()
    try:
        results = _index.query(
            vector=embedding,
            top_k=n_results,
            include_metadata=True,
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[PINECONE] !! query EROARE dupa {elapsed_ms:.0f}ms: {type(exc).__name__}: {exc}")
        raise

    elapsed_ms = (time.perf_counter() - start) * 1000
    n_matches = len(results.matches) if hasattr(results, "matches") else 0

    print(f"[PINECONE] <- query_store() OK in {elapsed_ms:.0f}ms — {n_matches} match(es)")
    if n_matches > 0:
        for i, match in enumerate(results.matches):
            preview = match.metadata.get("prompt", "")[:50] if match.metadata else ""
            print(f"[PINECONE]    [{i}] score={match.score:.4f} id={match.id} prompt={preview!r}")

    return results


def key_exists(cache_key: str) -> bool:
    """
    Verifica daca un ID exista deja in index.
    Folosim fetch() — returneaza vectorii cu ID-urile cerute.
    Daca vectors e gol, inseamna ca nu exista.
    """
    print(f"[PINECONE] -> key_exists(key={cache_key})")

    start = time.perf_counter()
    try:
        result = _index.fetch(ids=[cache_key])
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[PINECONE] !! fetch EROARE dupa {elapsed_ms:.0f}ms: {type(exc).__name__}: {exc}")
        raise

    elapsed_ms = (time.perf_counter() - start) * 1000
    exists = len(result.vectors) > 0

    print(f"[PINECONE] <- key_exists() = {exists} (in {elapsed_ms:.0f}ms)")
    return exists
