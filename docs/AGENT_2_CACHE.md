# Agent 2 — Semantic Cache Service
**This file is your complete implementation brief. Read it fully before writing a single line.**

---

## Your Role
You are building the **first stage of the EcoGateway pipeline**: a semantic cache that intercepts incoming prompts and checks whether a sufficiently similar query has been answered before. A cache hit means zero model inference, zero tokens billed, near-zero carbon. This is the highest-leverage optimization in the entire system.

You own exactly one module: `backend/cache/`. Nothing else.

---

## Full Project Context

EcoGateway is an AI API proxy with a 4-stage sustainability pipeline:
1. **Semantic Cache (you)** — check if this prompt was already answered. Hit = skip everything else.
2. Prompt Compression (Agent 3) — strip tokens from novel prompts.
3. Carbon-Aware Scheduler (Agent 4) — pick the greenest Azure region and model tier.
4. Green Receipt (Agent 1) — append carbon/cost metadata to every response.

The Orchestrator (Agent 1) calls your two functions at the very start of every request. Your code must be fast — it runs on every single request, including cache misses.

**Tech stack:** Python 3.11, Azure Functions, ChromaDB (local vector store), OpenAI Python SDK (for embeddings via Azure OpenAI).

---

## Your Deliverables

### Files to create
```
backend/
└── cache/
    ├── __init__.py
    ├── cache_service.py      # YOUR primary file — the two public functions
    ├── embedder.py           # Embedding generation via Azure OpenAI
    └── vector_store.py       # ChromaDB wrapper
```

---

## Interface Contract

### What you EXPOSE (Agent 1 calls these — do not change signatures)

```python
# cache/cache_service.py

from shared.models import CacheResult

def check_cache(prompt: str) -> CacheResult:
    """
    Embeds the prompt and searches ChromaDB for the nearest stored query.
    Returns a hit if cosine similarity >= SIMILARITY_THRESHOLD (0.92).
    Fast path: should complete in <200ms including the embedding call.
    """
    ...

def store_in_cache(prompt: str, response: str) -> None:
    """
    Embeds the prompt and stores (prompt_embedding, prompt_text, response) in ChromaDB.
    Called after every cache miss that gets a real model response.
    Fire-and-forget — do not block the response on this.
    """
    ...
```

### Shared model you use (defined in shared/models.py by Agent 1)
```python
@dataclass
class CacheResult:
    hit: bool
    response: str | None    # the cached response if hit, else None
    similarity: float       # cosine similarity score, 0.0 if miss
```

If Agent 1 hasn't created shared/models.py yet, define CacheResult locally in cache_service.py and move it later.

### What you CONSUME
- Azure OpenAI embeddings endpoint (env var: `AZURE_OAI_WESTEUROPE_ENDPOINT`, key: `AZURE_OAI_WESTEUROPE_KEY`)
- Embedding model: `text-embedding-3-small` (cheapest, fastest — do not use large)
- ChromaDB (local, in-process — no server needed)

---

## Implementation Details

### Similarity threshold
```python
SIMILARITY_THRESHOLD = 0.92  # tune this during testing
# 0.92 means "almost identical meaning, different wording"
# Lower = more cache hits but risk of wrong answers
# Higher = fewer hits but safer
# This threshold is part of your Green Receipt contribution — report it
```

### ChromaDB setup (vector_store.py)
```python
import chromadb

# Persistent storage so cache survives function restarts
# Use /tmp/ecogate_cache for Azure Functions (writable temp dir)
client = chromadb.PersistentClient(path="/tmp/ecogate_cache")
collection = client.get_or_create_collection(
    name="prompt_cache",
    metadata={"hnsw:space": "cosine"}  # cosine similarity
)
```

Key ChromaDB operations you need:
```python
# Store
collection.add(
    ids=[cache_key],           # md5 of the prompt
    embeddings=[embedding],    # list of floats from Azure OAI
    documents=[prompt],
    metadatas=[{"response": response, "timestamp": iso_timestamp}]
)

# Query
results = collection.query(
    query_embeddings=[embedding],
    n_results=1,
    include=["documents", "metadatas", "distances"]
)
# ChromaDB returns distances (lower = more similar for cosine)
# Convert: similarity = 1 - distance
```

### Embedding generation (embedder.py)
```python
from openai import AzureOpenAI
import os

def get_embedding(text: str) -> list[float]:
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OAI_WESTEUROPE_ENDPOINT"],
        api_key=os.environ["AZURE_OAI_WESTEUROPE_KEY"],
        api_version="2024-02-01"
    )
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding
```

**Important:** Cache the AzureOpenAI client instance at module level (not inside the function) to reuse the connection across requests in the same Azure Function warm instance.

### Full check_cache flow
```
1. Call get_embedding(prompt) → embedding vector
2. Call collection.query(embedding, n_results=1)
3. If no results → return CacheResult(hit=False, response=None, similarity=0.0)
4. distance = results["distances"][0][0]
5. similarity = 1 - distance
6. if similarity >= SIMILARITY_THRESHOLD:
       return CacheResult(hit=True, response=results["metadatas"][0][0]["response"], similarity=similarity)
   else:
       return CacheResult(hit=False, response=None, similarity=similarity)
```

### Cache key for deduplication
When storing, generate a key so you don't store exact duplicates:
```python
import hashlib
cache_key = hashlib.md5(prompt.strip().lower().encode()).hexdigest()
# Check if key already exists before adding to avoid ChromaDB duplicate errors
existing = collection.get(ids=[cache_key])
if not existing["ids"]:
    collection.add(...)
```

---

## Implementation Order

### Step 1 — vector_store.py
Set up ChromaDB client and collection. Write `add_to_store(key, embedding, prompt, response)` and `query_store(embedding, n_results=1)`. Test standalone with a hardcoded embedding vector.

### Step 2 — embedder.py
Implement `get_embedding(text)`. Test by printing the first 5 values of the returned vector. Confirm the vector has 1536 dimensions (text-embedding-3-small output size).

### Step 3 — cache_service.py
Wire Steps 1 and 2 into `check_cache` and `store_in_cache`. Write a local test:
```python
if __name__ == "__main__":
    store_in_cache("What is the capital of France?", "Paris.")
    result = check_cache("What's the capital city of France?")
    print(result)  # should be a hit with similarity > 0.92
    result2 = check_cache("How do I cook pasta?")
    print(result2)  # should be a miss
```

### Step 4 — Handle cold start
ChromaDB on a fresh Azure Function instance will have an empty collection. That's fine — it warms up over time. Do NOT seed it with fake data. Log a message when the collection is empty on startup.

---

## Performance Requirements
- `check_cache` must return in <300ms (the embedding API call is the bottleneck)
- `store_in_cache` should be called asynchronously after the response is sent — do not make the user wait for it
- The AzureOpenAI client must be initialized once at module load, not per request

---

## What NOT to do
- Do not use `text-embedding-3-large` — it's 5x more expensive and unnecessary
- Do not store the full response in the ChromaDB vector — put it in `metadatas`
- Do not set SIMILARITY_THRESHOLD below 0.85 — you'll return wrong cached answers
- Do not implement your own vector math — use ChromaDB's built-in cosine distance

---

## Dependencies to add to requirements.txt
```
chromadb>=0.4.0
openai>=1.0.0
```

---

## Definition of Done
- [ ] `check_cache("What is the capital of France?")` after storing that query returns `hit=True` and `similarity > 0.92`
- [ ] `check_cache("How do I make coffee?")` returns `hit=False`
- [ ] `store_in_cache` does not throw when called twice with the same prompt
- [ ] AzureOpenAI client is instantiated once at module level
- [ ] No API keys in source code
- [ ] Collection persists to `/tmp/ecogate_cache` and survives a Python process restart
