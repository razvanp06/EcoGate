# EcoGateway AI — Technical Summary

## Sustainability Hypothesis

> **Every unoptimised OpenAI/Anthropic API call emits ~0.04–0.15 gCO₂ that can be partially or fully avoided.**
> EcoGateway reduces this by routing to low-carbon Azure regions, selecting the smallest model
> sufficient for the task, compressing prompts before inference, and serving semantically
> equivalent queries from cache — targeting chat and Q&A workloads of 50–2 000 tokens at
> SaaS scale (≥ 100 req/day) where semantic repetition is common.

---

## 4-Stage Pipeline

| Stage | Technique | Carbon mechanism |
|---|---|---|
| **1 · Semantic Cache** | Pinecone vector DB, cosine similarity ≥ 0.92 (all-MiniLM-L6-v2, 384 dims) | Skip inference entirely — zero energy, ~99.5% reduction |
| **2 · Prompt Compression** | Regex + NLP rules: filler removal, deduplication, artefact fixing; code blocks protected | 5–20% fewer input tokens → proportional energy reduction |
| **3 · Complexity Router** | sentence-transformers kNN vs labelled simple/complex examples | Route simple queries to o4-mini (10× lower energy factor vs gpt-4o) |
| **4 · Carbon-Aware Scheduler** | Live grid data via Electricity Maps API; defer batch when grid > 250 gCO₂/kWh | Pick lowest-carbon Azure region per request; hold batch jobs up to 2 h |

---

## Carbon Accounting — Green Software Foundation SCI

**Formula:** `SCI = (E × I + M) / R`
- **E** = inference energy (kWh) = tokens / 1 000 × model energy factor
- **I** = live carbon intensity (gCO₂/kWh) from Electricity Maps API
- **M** = embodied hardware carbon = 0.001 gCO₂/request (constant)
- **R** = 1 request

**Baseline** (what the user would spend without EcoGateway): gpt-4o at **300 gCO₂/kWh**
— weighted average of primary API regions (US-East ~320, EU-West ~250, US-West ~100).
Not a worst-case; represents a typical unconstrained call.

**Energy factors:** gpt-4o = 0.00090 kWh/1k tokens; o4-mini = 0.00009 kWh/1k tokens
(Patterson et al. 2021 + ElectricityMaps/ML CO₂ Impact cross-reference).
o4-mini reasoning tokens are **excluded from the baseline** — gpt-4o has no equivalent
overhead, so including them would inflate savings artificially.

**Measured savings breakdown (non-cached requests):**

| Lever | Mechanism | Typical saving |
|---|---|---|
| Carbon-aware routing | swedencentral ~35 gCO₂/kWh vs 300 baseline | **~88%** |
| Model switching | o4-mini vs gpt-4o (same region) | **~90%** |
| Prompt compression | 15% average token reduction | **~15%** |
| Semantic cache hit | No inference, hardware carbon only | **~99.5%** |
| Combined (routing + model + compression) | Multiplicative | **~93–97%** |

---

## Transparent Trade-offs

| Optimisation | What was traded |
|---|---|
| Semantic cache | Stale responses if knowledge changes; 0.92 threshold can miss edge-case prompt variants |
| Complexity routing | Tier-1 (o4-mini) produces shorter answers; reserved for prompts the classifier scores as simple |
| Prompt compression | Filler/politeness removal only; code blocks, lists, and structured content are protected |
| Batch deferral | Up to 2 h latency; only available when caller sets `urgency=batch` |
| Gateway overhead | ~100–200 ms per request (embedding + cache lookup + routing) |

---

## Practical Relevance

Drop-in proxy for any team using the OpenAI-compatible API — single endpoint change, no
application code modifications. Applicable to SaaS chatbots, internal tooling, university
research portals, and developer tools where prompt repetition exceeds ~15%.

**Back-of-envelope at 1 000 req/day, 40% cache hit rate, remaining routed to swedencentral:**
- Baseline: 1 000 × 0.120 gCO₂ = **120 gCO₂/day** (~43.8 kg CO₂/year)
- With EcoGateway: ~7 gCO₂/day (~2.6 kg CO₂/year)
- **Annual saving: ~41 kg CO₂eq** — equivalent to ~200 000 Google searches

---

## Standards & Methodology Signals

- **GSF SCI formula** for all per-request carbon calculations (not aggregate estimates)
- **Real telemetry**: live grid intensity from Electricity Maps API; falls back to 5-year
  historical averages (SE: 40 gCO₂/kWh, PJM/US-East: 386 gCO₂/kWh) on API failure
- **Reproducible**: all energy factors, baseline intensity, and thresholds are explicit
  named constants in `receipt.py` and `carbon_client.py`
- **Quantified before/after**: every response includes a `GreenReceipt` with actual gCO₂,
  baseline gCO₂, savings %, model used, region used, and live carbon intensity
- **Changes behaviour, not just visualises**: routes, compresses, and caches in the
  critical request path — not a dashboard bolted on after the fact
