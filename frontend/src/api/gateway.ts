// All HTTP communication with the backend lives here.
// Components never call fetch() directly — they import from this file.
//
// Two public functions:
//   fetchReceipts() — called by Dashboard's polling loop every 3 seconds
//   sendQuery()     — called by QueryTester when the user submits a prompt
//
// STUB_RECEIPTS is used during development before the backend is running.
// Switch to real calls by removing the stub usage in Dashboard/QueryTester.

import type {
  GreenReceipt,
  ReceiptsResponse,
  QueryRequest,
  QueryResponse,
} from "../types/receipt";

// Empty by default: the browser calls /api/* on the same origin, which Vercel
// routes to the backend service. Set VITE_BACKEND_URL (e.g. http://localhost:7071)
// only when running the Vite dev server against a separately started backend.
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "";

export async function fetchReceipts(): Promise<GreenReceipt[]> {
  const res = await fetch(`${BACKEND_URL}/api/receipts`);
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  const data: ReceiptsResponse = await res.json();
  return data.receipts;
}

export async function sendQuery(req: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${BACKEND_URL}/api/gateway`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  return res.json();
}
