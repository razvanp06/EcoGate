"""
cache_service.py — Interfata publica a modulului de cache (Agent 2)

Acesta este singurul fisier pe care Orchestratorul (Agent 1) il importa.
El contine exact doua functii publice — semnatura lor NU se schimba.

Flow complet:
  1. Orchestratorul primeste un prompt de la utilizator
  2. Apeleaza check_cache(prompt) — noi cautam un raspuns similar
  3a. Daca gasim (hit=True)  → Orchestratorul returneaza raspunsul cached, gata
  3b. Daca nu gasim (hit=False) → Orchestratorul merge mai departe prin pipeline
  4. Dupa ce modelul raspunde, Orchestratorul apeleaza store_in_cache(prompt, response)
     ca sa retinem raspunsul pentru data viitoare
"""

import hashlib
import logging
import time
from datetime import datetime, timezone

from shared.models import CacheResult
from cache.embedder import get_embedding
from cache.vector_store import add_to_store, query_store, key_exists

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Pragul de similaritate: 0.92
#
# Similaritatea cosinus merge de la 0.0 (complet diferit) la 1.0 (identic).
# La 0.92 inseamna "aproape identic ca sens, poate formulare diferita".
#
# Exemple de ce returneaza:
#   "What is the capital of France?" vs "What's France's capital?" → ~0.96 (HIT)
#   "What is the capital of France?" vs "How do I make pasta?"     → ~0.12 (MISS)
#   "What is the capital of France?" vs "What is the capital of Germany?" → ~0.88 (MISS — corect!)
#
# Sub 0.85 = pericol de raspunsuri gresite (intrebari diferite par similare)
# Peste 0.95 = ratezi hit-uri evidente
# -------------------------------------------------------------------
SIMILARITY_THRESHOLD = 0.92


def check_cache(prompt: str) -> CacheResult:
    """
    Verifica daca exista un raspuns cached semantic similar cu prompt-ul primit.

    Returneaza un CacheResult cu:
      hit=True,  response="...", similarity=0.96  → am gasit, foloseste raspunsul
      hit=False, response=None,  similarity=0.43  → nu am gasit, mergi mai departe

    Orchestratorul se uita doar la .hit ca sa decida ce face.
    .similarity ajunge in GreenReceipt pentru transparenta.
    """
    prompt_preview = prompt[:60] + ("..." if len(prompt) > 60 else "")

    print(f"\n[CACHE] ============ check_cache() START ============")
    print(f"[CACHE] Prompt ({len(prompt)} chars): {prompt_preview!r}")
    print(f"[CACHE] Threshold: {SIMILARITY_THRESHOLD}")

    total_start = time.perf_counter()
    logger.info("Cache check pentru prompt de %d caractere", len(prompt))

    # Pasul 1: Transformam prompt-ul in vector numeric via Azure OAI (~150-250ms)
    print(f"[CACHE] Pas 1/4: Generare embedding...")
    try:
        embedding = get_embedding(prompt)
    except Exception as exc:
        # Daca Azure OAI embeddings nu e disponibil, nu blocam intregul request.
        # Logam eroarea si returnam miss — pipeline-ul continua normal.
        print(f"[CACHE] !! Embedding EROARE: {type(exc).__name__}: {exc}")
        print(f"[CACHE] -> Tratam ca MISS si continuam pipeline-ul")
        print(f"[CACHE] ============ check_cache() END (eroare) ===\n")
        logger.error("Embedding esuat, tratam ca miss: %s", exc)
        return CacheResult(hit=False, response=None, similarity=0.0)

    # Pasul 2: Cautam in Pinecone cel mai apropiat vector stocat
    print(f"[CACHE] Pas 2/4: Cautare in Pinecone...")
    results = query_store(embedding, n_results=1)

    # Pasul 3: Daca nu exista nimic in cache, returnam miss imediat
    # results.matches este lista rezultatelor. Daca e goala, indexul e gol.
    if not results.matches:
        total_ms = (time.perf_counter() - total_start) * 1000
        print(f"[CACHE] Pas 3/4: Niciun rezultat — cache gol sau prompt nou")
        print(f"[CACHE] DECIZIE: MISS automat (similarity=0.0)")
        print(f"[CACHE] Total time: {total_ms:.0f}ms")
        print(f"[CACHE] ============ check_cache() END (miss-empty) ===\n")
        logger.info("Cache gol — miss automat")
        return CacheResult(hit=False, response=None, similarity=0.0)

    # Pasul 4: Citim similaritatea direct din rezultat
    # Pinecone returneaza direct SIMILARITATEA cosinus (spre deosebire de
    # ChromaDB care returna distanta). Nu mai facem "1 - distance".
    similarity = results.matches[0].score

    print(f"[CACHE] Pas 3/4: Cel mai apropiat match: similarity={similarity:.4f}")
    logger.info(
        "Cel mai apropiat match: similarity=%.4f (threshold=%.2f)",
        similarity,
        SIMILARITY_THRESHOLD,
    )

    # Pasul 5: Decidem daca e hit sau miss
    print(f"[CACHE] Pas 4/4: Decizie hit/miss...")
    total_ms = (time.perf_counter() - total_start) * 1000

    if similarity >= SIMILARITY_THRESHOLD:
        # Am gasit un raspuns suficient de similar — il returnam
        cached_response = results.matches[0].metadata["response"]
        matched_prompt = results.matches[0].metadata["prompt"]
        response_preview = cached_response[:80] + ("..." if len(cached_response) > 80 else "")

        print(f"[CACHE] DECIZIE: *** CACHE HIT *** (similarity {similarity:.4f} >= {SIMILARITY_THRESHOLD})")
        print(f"[CACHE]   Matched prompt: {matched_prompt[:80]!r}")
        print(f"[CACHE]   Returnam response: {response_preview!r}")
        print(f"[CACHE] Total time: {total_ms:.0f}ms")
        print(f"[CACHE] ============ check_cache() END (HIT) ===\n")

        logger.info("CACHE HIT — matched: %r", matched_prompt[:80])
        return CacheResult(hit=True, response=cached_response, similarity=similarity)
    else:
        # Am gasit ceva in DB, dar nu e suficient de similar — miss
        print(f"[CACHE] DECIZIE: MISS (similarity {similarity:.4f} < {SIMILARITY_THRESHOLD})")
        print(f"[CACHE]   Pipeline-ul continua catre Agent 3, 4, model")
        print(f"[CACHE] Total time: {total_ms:.0f}ms")
        print(f"[CACHE] ============ check_cache() END (MISS) ===\n")

        logger.info("CACHE MISS — similarity %.4f sub threshold %.2f", similarity, SIMILARITY_THRESHOLD)
        return CacheResult(hit=False, response=None, similarity=similarity)


def store_in_cache(prompt: str, response: str) -> None:
    """
    Stocheaza un prompt si raspunsul sau in Pinecone pentru folosire viitoare.

    Apelata de Orchestrator dupa fiecare cache miss care a primit raspuns real.
    Nu arunca exceptii — Orchestratorul o apeleaza fire-and-forget.

    De ce md5 ca key?
    - Vrem un ID unic si fix pentru fiecare prompt
    - .strip().lower() normalizeaza: "Hello " si "hello" au acelasi key
    - Asta previne duplicate identice (dar matching-ul semantic e pe vectori, nu pe key)
    """
    prompt_preview = prompt[:60] + ("..." if len(prompt) > 60 else "")
    response_preview = response[:60] + ("..." if len(response) > 60 else "")

    print(f"\n[CACHE] ============ store_in_cache() START ============")
    print(f"[CACHE] Prompt ({len(prompt)} chars): {prompt_preview!r}")
    print(f"[CACHE] Response ({len(response)} chars): {response_preview!r}")

    total_start = time.perf_counter()

    # Generam un ID unic pentru acest prompt
    # hashlib.md5 creeaza un "amprenta" scurta si unica a unui text
    cache_key = hashlib.md5(prompt.strip().lower().encode()).hexdigest()
    print(f"[CACHE] Pas 1/4: cache_key generat = {cache_key}")

    # Verificam daca exista deja ca sa evitam duplicate in Pinecone
    print(f"[CACHE] Pas 2/4: Verificam daca cheia exista deja...")
    if key_exists(cache_key):
        total_ms = (time.perf_counter() - total_start) * 1000
        print(f"[CACHE] -> Cheia exista deja, skip stocare")
        print(f"[CACHE] Total time: {total_ms:.0f}ms")
        print(f"[CACHE] ============ store_in_cache() END (skip) ===\n")
        logger.debug("Prompt deja in cache (key=%s), skip.", cache_key)
        return

    # Generam vectorul pentru prompt
    print(f"[CACHE] Pas 3/4: Generam embedding pentru prompt...")
    try:
        embedding = get_embedding(prompt)
    except Exception as exc:
        # Daca embedding esueaza, logam si iesim fara a arunca exceptie
        total_ms = (time.perf_counter() - total_start) * 1000
        print(f"[CACHE] !! Embedding EROARE: {type(exc).__name__}: {exc}")
        print(f"[CACHE] -> Nu stocam, dar nu aruncam exceptie")
        print(f"[CACHE] Total time: {total_ms:.0f}ms")
        print(f"[CACHE] ============ store_in_cache() END (eroare) ===\n")
        logger.error("store_in_cache: embedding esuat, nu stocam: %s", exc)
        return

    # Timestamp ISO 8601 pentru audit trail
    timestamp = datetime.now(timezone.utc).isoformat()

    # Stocam in Pinecone
    print(f"[CACHE] Pas 4/4: Stocare in Pinecone...")
    try:
        add_to_store(
            cache_key=cache_key,
            embedding=embedding,
            prompt=prompt,
            response=response,
            timestamp=timestamp,
        )
        total_ms = (time.perf_counter() - total_start) * 1000
        print(f"[CACHE] *** STOCAT CU SUCCES ***")
        print(f"[CACHE]   key: {cache_key}")
        print(f"[CACHE]   timestamp: {timestamp}")
        print(f"[CACHE] Total time: {total_ms:.0f}ms")
        print(f"[CACHE] ============ store_in_cache() END (OK) ===\n")
        logger.info("Stocat in cache: key=%s, prompt=%r", cache_key, prompt[:60])
    except Exception as exc:
        total_ms = (time.perf_counter() - total_start) * 1000
        print(f"[CACHE] !! add_to_store EROARE: {type(exc).__name__}: {exc}")
        print(f"[CACHE] Total time: {total_ms:.0f}ms")
        print(f"[CACHE] ============ store_in_cache() END (eroare) ===\n")
        # Nici aici nu aruncam exceptie — store e fire-and-forget
        logger.error("store_in_cache: add_to_store esuat: %s", exc)
