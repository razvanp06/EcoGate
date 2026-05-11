# EcoGate
Sustainability-aware proxy for LLM APIs. Combines semantic caching, rule-based prompt compression, and carbon-aware routing to cut tokens by 20–40% and minimize CO₂ per request — with a transparent green receipt on every response.

# FrostFlow

FrostFlow is a sustainability-aware proxy for LLM APIs that reduces the
energy and carbon footprint of AI inference through a four-stage pipeline.

## Pipeline

1. **Semantic Cache** — incoming prompts are checked against a vector
   store of previous queries. A cache hit short-circuits the entire
   pipeline and returns a stored response, eliminating model compute.

2. **Prompt Compression** — on cache miss, a rule-based compressor
   strips linguistic redundancy (filler phrases, politeness boilerplate,
   verbose constructions, duplicate context) while preserving semantic
   content. Code blocks are protected via placeholder substitution.
   Token counting uses `tiktoken` (cl100k_base) for accurate billing
   estimates. Typical reduction: 20–40% on verbose prompts.

3. **Carbon-Aware Scheduler** — the compressed prompt is routed to one
   of several model endpoints across regions. Routing decisions are
   driven by real-time grid carbon intensity (via Electricity Maps),
   selecting the lowest-emission viable backend per request.

4. **Green Receipt** — every response is enriched with metadata:
   tokens saved, estimated CO₂ avoided, region used, compression rules
   applied, and cache status.

## Stack

Python 3.11, FastAPI, Redis (semantic cache), tiktoken, Electricity Maps
API. Compatible with OpenAI, Anthropic, Mistral, and Groq backends via a
unified adapter layer.

## Status

Hackathon prototype (ASMI Bucharest Hackathon 2026). Functional end-to-end
with measurable token and carbon savings on a benchmark prompt set.
