# EcoGateway AI — Executive Summary

## The Problem

AI adoption is accelerating — and so is its environmental cost. Every call to a large
language model API consumes energy and emits carbon. Most developers have no visibility
into this cost and no tools to reduce it. They call the nearest available server, use the
most powerful model regardless of the task, and repeat identical queries with no awareness
that they have done so before. The result is significant, avoidable waste at scale.

## What EcoGateway Does

EcoGateway is a drop-in sustainability proxy that sits between an application and its AI
provider. It intercepts each request and automatically applies four optimisations before
the call is made — or instead of making it at all:

1. **Semantic Cache** — if a near-identical question has been answered before, the stored
   answer is returned instantly. No model call, no energy consumed.

2. **Prompt Compression** — unnecessary filler, repetition, and politeness phrases are
   stripped from the prompt before it is sent, reducing the token count and cost.

3. **Smart Model Selection** — simple questions are routed to a lightweight model;
   complex ones to the full-size model. The system decides automatically.

4. **Green Region Routing** — the request is sent to whichever data centre is running on
   the cleanest electricity at that moment, using live grid data. Low-priority requests
   can be held briefly until grid conditions improve.

The application receives the same response it would have gotten from a direct API call.
No integration work is required beyond changing a single endpoint URL.

## Impact

| Scenario | Carbon per request | vs. unoptimised baseline |
|---|---|---|
| Semantic cache hit | ~0.001 gCO₂ | **−99.5%** |
| Green region routing (Sweden, ~35 gCO₂/kWh) | ~0.014 gCO₂ | **−88%** |
| Lightweight model + green routing | ~0.002 gCO₂ | **−97%** |

At 1 000 API calls per day with a typical mix of cache hits and green-routed requests,
EcoGateway reduces annual emissions by an estimated **~41 kg CO₂eq** — the equivalent of
approximately 200 000 Google searches — compared to making the same calls without
optimisation.

For European users, green routing to Sweden Central also reduces latency compared to US
data centres, making this a performance improvement as well as an environmental one.

## Why It Matters

The carbon cost of AI inference is real, measurable, and — unlike hardware manufacturing
or data centre construction — directly controllable through software. EcoGateway
demonstrates that sustainability and performance are not in conflict: caching is faster,
smaller models are cheaper, and green grids in Europe are geographically closer to
European users.

Every metric in this product is calculated using the **Green Software Foundation SCI
standard** and verified against **live grid telemetry** from Electricity Maps. There are
no estimates dressed as measurements, and no savings claimed that are not accounted for
in the per-request receipt returned to the caller.

## Applicability

Any organisation using OpenAI, Anthropic, or Azure AI APIs today — SaaS companies,
research institutions, development teams — can deploy EcoGateway without changing their
application. The proxy is stateless, horizontally scalable, and adds under 200 ms of
overhead, which is negligible relative to typical model response times of 1–10 seconds.
