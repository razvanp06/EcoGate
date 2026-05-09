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
    logger.info("Cache check pentru prompt de %d caractere", len(prompt))

    # Pasul 1: Transformam prompt-ul in vector numeric via Azure OAI (~150-250ms)
    try:
        embedding = get_embedding(prompt)
    except Exception as exc:
        # Daca Azure OAI embeddings nu e disponibil, nu blocam intregul request.
        # Logam eroarea si returnam miss — pipeline-ul continua normal.
        logger.error("Embedding esuat, tratam ca miss: %s", exc)
        return CacheResult(hit=False, response=None, similarity=0.0)

    # Pasul 2: Cautam in Pinecone cel mai apropiat vector stocat
    results = query_store(embedding, n_results=1)

    # Pasul 3: Daca nu exista nimic in cache, returnam miss imediat
    # results.matches este lista rezultatelor. Daca e goala, indexul e gol.
    if not results.matches:
        logger.info("Cache gol — miss automat")
        return CacheResult(hit=False, response=None, similarity=0.0)

    # Pasul 4: Citim similaritatea direct din rezultat
    # Pinecone returneaza direct SIMILARITATEA cosinus (spre deosebire de
    # ChromaDB care returna distanta). Nu mai facem "1 - distance".
    similarity = results.matches[0].score

    logger.info(
        "Cel mai apropiat match: similarity=%.4f (threshold=%.2f)",
        similarity,
        SIMILARITY_THRESHOLD,
    )

    # Pasul 5: Decidem daca e hit sau miss
    if similarity >= SIMILARITY_THRESHOLD:
        # Am gasit un raspuns suficient de similar — il returnam
        cached_response = results.matches[0].metadata["response"]
        matched_prompt = results.matches[0].metadata["prompt"]
        logger.info("CACHE HIT — matched: %r", matched_prompt[:80])
        return CacheResult(hit=True, response=cached_response, similarity=similarity)
    else:
        # Am gasit ceva in DB, dar nu e suficient de similar — miss
        logger.info("CACHE MISS — similarity %.4f sub threshold %.2f", similarity, SIMILARITY_THRESHOLD)
        return CacheResult(hit=False, response=None, similarity=similarity)


def store_in_cache(prompt: str, response: str) -> None:
    """
    Stocheaza un prompt si raspunsul sau in ChromaDB pentru folosire viitoare.

    Apelata de Orchestrator dupa fiecare cache miss care a primit raspuns real.
    Nu arunca exceptii — Orchestratorul o apeleaza fire-and-forget.

    De ce md5 ca key?
    - Vrem un ID unic si fix pentru fiecare prompt
    - .strip().lower() normalizeaza: "Hello " si "hello" au acelasi key
    - Asta previne duplicate identice (dar matching-ul semantic e pe vectori, nu pe key)
    """
    # Generam un ID unic pentru acest prompt
    # hashlib.md5 creeaza un "amprenta" scurta si unica a unui text
    cache_key = hashlib.md5(prompt.strip().lower().encode()).hexdigest()

    # Verificam daca exista deja ca sa evitam duplicate in Pinecone
    if key_exists(cache_key):
        logger.debug("Prompt deja in cache (key=%s), skip.", cache_key)
        return

    # Generam vectorul pentru prompt
    try:
        embedding = get_embedding(prompt)
    except Exception as exc:
        # Daca embedding esueaza, logam si iesim fara a arunca exceptie
        logger.error("store_in_cache: embedding esuat, nu stocam: %s", exc)
        return

    # Timestamp ISO 8601 pentru audit trail
    timestamp = datetime.now(timezone.utc).isoformat()

    # Stocam in Pinecone
    try:
        add_to_store(
            cache_key=cache_key,
            embedding=embedding,
            prompt=prompt,
            response=response,
            timestamp=timestamp,
        )
        logger.info("Stocat in cache: key=%s, prompt=%r", cache_key, prompt[:60])
    except Exception as exc:
        # Nici aici nu aruncam exceptie — store e fire-and-forget
        logger.error("store_in_cache: add_to_store esuat: %s", exc)
