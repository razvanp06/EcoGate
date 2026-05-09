# Agent 5 — React Frontend Dashboard
**This file is your complete implementation brief. Read it fully before writing a single line.**

---

## Your Role
You are building the **user-facing transparency layer** of EcoGateway: a React dashboard that visualizes the Green Receipts produced by every API request, tracks cumulative carbon savings, and makes the invisible environmental cost of AI visible to developers. This is what the jury sees during the demo — make it clear, real, and impressive.

You own exactly one directory: `frontend/`. Nothing else.

---

## Full Project Context

EcoGateway is an AI API proxy with a 4-stage sustainability pipeline:
1. Semantic Cache — returns cached answers with zero compute.
2. Prompt Compression — strips tokens before sending to the model.
3. Neural Router — routes simple prompts to cheaper, greener models.
4. Carbon-Aware Scheduler — picks the lowest-carbon Azure region; defers batch jobs.

Every request through the proxy generates a **Green Receipt**: a JSON object with the exact carbon cost, savings, route taken, and SCI score. Your dashboard reads these receipts from the backend and renders them in real time.

**You are not building a toy UI.** The jury specifically scores User Experience (15%) and asks: *"Is it intuitive and usable for a real user? Does the design support the core scenario clearly?"*

---

## Your Deliverables

### Project setup
```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   └── gateway.ts        # API calls to the backend
│   ├── components/
│   │   ├── Dashboard.tsx     # Main layout
│   │   ├── LiveFeed.tsx      # Real-time receipt stream
│   │   ├── SavingsCounter.tsx # Cumulative CO₂ saved (the hero metric)
│   │   ├── ReceiptCard.tsx   # Single receipt display
│   │   ├── RouteBreakdown.tsx # Pie/bar: cache hits vs compressed vs routed
│   │   ├── CarbonMap.tsx     # Region comparison: westeurope vs eastus
│   │   └── QueryTester.tsx   # Send a test prompt, see the receipt live
│   ├── types/
│   │   └── receipt.ts        # TypeScript types matching backend GreenReceipt
│   └── index.css
├── index.html
├── package.json
└── vite.config.ts
```

### Scaffold
Use Vite + React + TypeScript:
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install recharts lucide-react
```
No heavy UI frameworks (no MUI, no Ant Design) — Tailwind CSS via CDN is fine, or plain CSS. Keep the bundle small.

---

## Green Receipt Type (types/receipt.ts)

This is the data structure your backend produces. Match it exactly:

```typescript
export interface GreenReceipt {
  request_id: string;
  timestamp: string;           // ISO8601

  // Stage 1: Cache
  cache_hit: boolean;
  cache_similarity: number;    // 0.0 if miss

  // Stage 2: Compression
  original_tokens: number;
  compressed_tokens: number;
  compression_ratio: number;   // e.g. 0.72 = 28% saved
  tokens_saved_by_compression: number;

  // Stage 3+4: Routing
  complexity_tier: number;     // 1 or 2
  model_used: string;          // "gpt-4o-mini" or "gpt-4o"
  region_used: string;         // "westeurope" or "eastus"
  carbon_intensity: number;    // gCO₂/kWh at time of request
  deferred: boolean;
  defer_until: string | null;

  // SCI
  energy_kwh: number;
  gco2_this_request: number;
  gco2_baseline: number;       // what gpt-4o in eastus would have cost
  gco2_saved: number;          // baseline - this_request
  sci_score: number;           // gCO₂ per request

  savings_pct: number;         // percentage saved vs baseline
  route_explanation: string;   // one sentence from the backend
}

export interface ReceiptsResponse {
  receipts: GreenReceipt[];
}
```

---

## API Layer (api/gateway.ts)

```typescript
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:7071";

export async function fetchReceipts(): Promise<GreenReceipt[]> {
  const res = await fetch(`${BACKEND_URL}/api/receipts`);
  const data: ReceiptsResponse = await res.json();
  return data.receipts;
}

export interface QueryRequest {
  prompt: string;
  urgency: "realtime" | "batch";
  system_prompt?: string;
}

export interface QueryResponse {
  response: string | null;
  green_receipt: GreenReceipt;
  job_id?: string;
  status?: string;
}

export async function sendQuery(req: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${BACKEND_URL}/api/gateway`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return res.json();
}
```

---

## Components to Build

### 1. SavingsCounter.tsx — The Hero Metric
This is the number that immediately tells the jury the system works. Display prominently at the top:

```
┌─────────────────────────────────────────────────────┐
│  Total CO₂ Avoided This Session                     │
│                                                     │
│           2.847 gCO₂                               │
│      ≈ 0.9km driven by average car                 │
│                                                     │
│  [42 requests]  [73% avg savings]  [12 cache hits] │
└─────────────────────────────────────────────────────┘
```

Calculate from the receipts array:
```typescript
const totalSaved = receipts.reduce((sum, r) => sum + r.gco2_saved, 0);
const avgSavingsPct = receipts.reduce((sum, r) => sum + r.savings_pct, 0) / receipts.length;
const cacheHits = receipts.filter(r => r.cache_hit).length;
// Car conversion: 1 km ≈ 120g CO₂ → gco2_saved / 0.12 = km equivalent
const kmEquivalent = (totalSaved / 0.12).toFixed(1);
```

### 2. LiveFeed.tsx — Real-Time Receipt Stream
Poll `GET /api/receipts` every 3 seconds. Show the last 10 receipts as cards in a scrolling list, newest at the top. Animate new cards sliding in from the top.

Each card: route_explanation text, gco2_this_request, savings_pct, model_used, cache_hit badge.

### 3. ReceiptCard.tsx — Single Receipt
```
┌─────────────────────────────────────────────────────┐
│ [CACHE HIT] or [gpt-4o-mini • westeurope]          │
│ "Routed to gpt-4o-mini in westeurope (142 gCO₂/kWh)│
│  simple prompt, efficient model."                   │
│                                                     │
│ 0.0089 gCO₂  •  saved 73%  •  98→71 tokens (28%)  │
│ 12:43:21                                            │
└─────────────────────────────────────────────────────┘
```
Color coding:
- Cache hit → green background
- Mini model → light green
- Full model → amber
- Deferred → blue

### 4. RouteBreakdown.tsx — Where Are Requests Going?
A simple horizontal bar or pie chart (use Recharts) showing:
- % cache hits (darkest green)
- % routed to gpt-4o-mini (green)
- % routed to gpt-4o (amber)
- % deferred (blue)

```typescript
import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";

const data = [
  { name: "Cache Hit", value: cacheHits, color: "#22c55e" },
  { name: "Mini Model", value: miniCount, color: "#86efac" },
  { name: "Full Model", value: fullCount, color: "#f59e0b" },
  { name: "Deferred", value: deferredCount, color: "#3b82f6" },
];
```

### 5. CarbonMap.tsx — Region Carbon Intensity
A simple side-by-side comparison showing live carbon intensity per region. This makes the carbon-aware routing decision visually legible:

```
West Europe (NL)    East US
   142 gCO₂/kWh    386 gCO₂/kWh
   ████░░░░░░░░    ████████████
   SELECTED ✓       AVOIDED
   Saves 63%
```

Fetch the most recent receipt's `carbon_intensity` for the current region and `carbon_intensity_baseline` for the baseline. Show them as a bar comparison.

### 6. QueryTester.tsx — Interactive Demo Panel
The most important component for the live demo. A panel where the jury can type a prompt and see the green receipt in real time:

```
┌─────────────────────────────────────────────────────┐
│ Test EcoGateway                                     │
│                                                     │
│ [textarea: enter your prompt here...]               │
│                                                     │
│ Urgency: ○ Real-time  ● Batch                      │
│                                                     │
│ [Send →]                                            │
└─────────────────────────────────────────────────────┘

↓ after submission:

┌─────────────────────────────────────────────────────┐
│ Response: "Paris is the capital of France."         │
│                                                     │
│ Green Receipt                                       │
│ ✓ Cache Hit (similarity: 0.94)                     │
│   CO₂ this request: 0.000 g (saved 100%)           │
│   Route: Semantic cache — no model call needed      │
└─────────────────────────────────────────────────────┘
```

This is your killer demo moment. Have 3 test prompts ready:
1. First send: "What is the capital of France?" → full pipeline, green receipt shows route
2. Second send: "What's France's capital city?" → cache hit, similarity ~0.96, zero CO₂
3. Send a complex prompt → routes to gpt-4o, shows tier 2 routing

---

## Dashboard Layout (Dashboard.tsx)

```
┌──────────────────────────────────────────────────────────────┐
│  EcoGateway  🌿  AI Sustainability Proxy                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [SavingsCounter — full width hero metric]                  │
│                                                              │
├────────────────────────┬─────────────────────────────────────┤
│  RouteBreakdown        │  CarbonMap                         │
│  (pie chart)           │  (region comparison)               │
├────────────────────────┴─────────────────────────────────────┤
│                                                              │
│  [QueryTester — left half]   [LiveFeed — right half]        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Polling Strategy
```typescript
// In Dashboard.tsx — poll every 3 seconds
useEffect(() => {
  const load = async () => {
    const data = await fetchReceipts();
    setReceipts(data);
  };
  load();
  const interval = setInterval(load, 3000);
  return () => clearInterval(interval);
}, []);
```
Do not use WebSockets — polling is sufficient and simpler for a demo.

---

## Visual Design Guidelines
- Background: dark (`#0f172a` slate-900) — makes green metrics pop
- Accent color: `#22c55e` (green-500) for savings, `#f59e0b` (amber) for cost
- Font: system-ui or Inter (no Google Fonts CDN calls needed)
- Numbers: large and readable — the jury is looking at a screen from 2 meters away
- No unnecessary animations — only animate new receipt cards appearing
- Show units always: `gCO₂`, `kWh`, `tokens`, `%` — never naked numbers

---

## Environment Variable
Create `frontend/.env.local` (gitignored):
```
VITE_BACKEND_URL=http://localhost:7071
```

---

## Implementation Order

### Step 1 — types/receipt.ts + api/gateway.ts
Define types and API functions. Test `fetchReceipts()` in the browser console.

### Step 2 — Stub data for development
Before the backend is ready, use stub receipts so you can build the UI without blocking on Agent 1:
```typescript
// api/gateway.ts
export const STUB_RECEIPTS: GreenReceipt[] = [
  {
    request_id: "stub-1",
    timestamp: new Date().toISOString(),
    cache_hit: true,
    cache_similarity: 0.94,
    original_tokens: 120,
    compressed_tokens: 120,
    compression_ratio: 1.0,
    tokens_saved_by_compression: 0,
    complexity_tier: 1,
    model_used: "gpt-4o-mini",
    region_used: "westeurope",
    carbon_intensity: 142,
    deferred: false,
    defer_until: null,
    energy_kwh: 0,
    gco2_this_request: 0,
    gco2_baseline: 0.042,
    gco2_saved: 0.042,
    sci_score: 0,
    savings_pct: 100,
    route_explanation: "Cache hit — no model call needed.",
  },
  // add 4-5 more stubs with different routes
];
```

### Step 3 — SavingsCounter + Dashboard skeleton
Get the layout and hero metric working with stub data.

### Step 4 — RouteBreakdown + CarbonMap
Add charts. Verify they update when you change the stub array.

### Step 5 — QueryTester
Wire up to real backend endpoint. This is the last piece — do it after the layout is solid.

### Step 6 — LiveFeed + polling
Enable real polling. Test with the backend running.

---

## What NOT to do
- Do not use placeholder values in the final demo — every number must come from a real receipt
- Do not build a login/auth flow — this is an internal developer tool
- Do not use heavy charting libraries (D3, Chart.js) — Recharts is sufficient and much lighter
- Do not show raw JSON to the jury — translate every field into human-readable language
- Do not put the API key in any frontend file — the frontend never calls Azure OpenAI directly

---

## Definition of Done
- [ ] Dashboard loads and shows stub data correctly
- [ ] `fetchReceipts()` successfully gets receipts from the real backend
- [ ] `sendQuery()` returns a response + receipt, which immediately appears in LiveFeed
- [ ] SavingsCounter totals are calculated correctly across all receipts
- [ ] Cache hit cards display differently from routed cards (color + badge)
- [ ] QueryTester demo works: first send routes to model, second send hits cache
- [ ] Numbers always have units (gCO₂, tokens, %)
- [ ] No API keys anywhere in frontend source
- [ ] Runs with `npm run dev` without errors
