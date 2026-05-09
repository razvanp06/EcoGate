// TypeScript interfaces that exactly mirror the backend's GreenReceipt dataclass.
// Every field here maps 1-to-1 to what POST /api/gateway and GET /api/receipts return.
// Import from this file everywhere — never define receipt shapes inline.

export interface GreenReceipt {
  // Identity
  request_id: string;   // UUID — unique per request, use as React list key
  timestamp: string;    // ISO8601 — when the request was processed

  // Stage 1: Semantic Cache
  cache_hit: boolean;         // true = cached answer returned, zero compute used
  cache_similarity: number;   // 0.0–1.0 cosine similarity; 0.0 when cache_hit is false

  // Stage 2: Prompt Compression
  original_tokens: number;              // token count before compression
  compressed_tokens: number;            // token count after compression (≤ original)
  compression_ratio: number;            // compressed / original, e.g. 0.72 = 28% stripped
  tokens_saved_by_compression: number;  // original - compressed

  // Stage 3 + 4: Neural Router + Carbon-Aware Scheduler
  complexity_tier: number;    // 1 = gpt-4o-mini, 2 = gpt-4o
  model_used: string;         // "gpt-4o-mini" | "gpt-4o"
  region_used: string;        // "westeurope" | "eastus"
  carbon_intensity: number;   // live gCO₂/kWh for the chosen region at request time
  deferred: boolean;          // true = batch job queued, not yet executed
  defer_until: string | null; // ISO8601 when job will run; null if not deferred

  // SCI Calculation (Green Software Foundation formula: SCI = E×I + M)
  energy_kwh: number;         // energy consumed: token_count × model_energy_factor
  gco2_this_request: number;  // actual CO₂ cost: energy_kwh × carbon_intensity + embodied
  gco2_baseline: number;      // what gpt-4o in eastus would have cost (worst-case baseline)
  gco2_saved: number;         // gco2_baseline - gco2_this_request (EcoGateway's saving)
  sci_score: number;          // formal SCI score in gCO₂ per request

  // Human-readable summary
  savings_pct: number;        // (gco2_saved / gco2_baseline) * 100; 100 for cache hits
  route_explanation: string;  // one sentence from backend: why this route was chosen
}

// Shape of GET /api/receipts response
export interface ReceiptsResponse {
  receipts: GreenReceipt[];
}

// Shape of POST /api/gateway request body
export interface QueryRequest {
  prompt: string;
  urgency: "realtime" | "batch";
  system_prompt?: string;
}

// Shape of POST /api/gateway response
export interface QueryResponse {
  response: string | null;    // AI answer text; null when request is deferred
  green_receipt: GreenReceipt;
  job_id?: string;            // present only when deferred === true
  status?: string;            // "queued" when deferred
}
