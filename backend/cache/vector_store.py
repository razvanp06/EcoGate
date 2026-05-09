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
from pinecone import Pinecone

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Initializam clientul Pinecone o singura data la nivel de modul.
# El citeste cheia API si host-ul din variabile de mediu.
#
# pc.Index(host=...) conecteaza direct la indexul nostru "ecogate-cache"
# fara sa mai intrebe serverul central Pinecone — mai rapid.
# -------------------------------------------------------------------
_pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY", ""))
_index = _pc.Index(host=os.environ.get("PINECONE_INDEX_HOST", ""))

logger.info("Pinecone index conectat: %s", os.environ.get("PINECONE_INDEX_HOST", ""))


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
    _index.upsert(vectors=[{
        "id": cache_key,
        "values": embedding,
        "metadata": {
            "prompt": prompt,
            "response": response,
            "timestamp": timestamp,
        },
    }])
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
    results = _index.query(
        vector=embedding,
        top_k=n_results,
        include_metadata=True,
    )
    return results


def key_exists(cache_key: str) -> bool:
    """
    Verifica daca un ID exista deja in index.
    Folosim fetch() — returneaza vectorii cu ID-urile cerute.
    Daca vectors e gol, inseamna ca nu exista.
    """
    result = _index.fetch(ids=[cache_key])
    return len(result.vectors) > 0
