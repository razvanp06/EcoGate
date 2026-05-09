// Interactive demo panel — the jury types here and sees the green receipt live.
// Manages its own local state: prompt, urgency, loading, result.
// Calls sendQuery() directly; does NOT push to Dashboard state.

import { useState } from "react";
import type { GreenReceipt, QueryResponse } from "../types/receipt";
import { sendQuery } from "../api/gateway";
import ReceiptCard from "./ReceiptCard";

interface Props {
  onNewReceipt: (r: GreenReceipt) => void;
}

export default function QueryTester({ onNewReceipt }: Props) {
  const [prompt, setPrompt] = useState("");
  const [urgency, setUrgency] = useState<"realtime" | "batch">("realtime");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await sendQuery({ prompt: prompt.trim(), urgency });
      setResult(res);
      onNewReceipt(res.green_receipt);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Backend unreachable — is it running?",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border-2 border-blue-500 bg-slate-800 p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-slate-300 text-sm font-semibold uppercase tracking-wide">
          Test EcoGateway
        </p>
        <div className="flex items-center gap-4">
          <p className="text-slate-400 text-sm">Urgency:</p>
          {(["realtime", "batch"] as const).map((u) => (
            <label
              key={u}
              className="flex items-center gap-2 cursor-pointer text-sm text-slate-300"
            >
              <input
                type="radio"
                name="urgency"
                value={u}
                checked={urgency === u}
                onChange={() => setUrgency(u)}
                className="accent-blue-500"
              />
              {u === "realtime" ? "Real-time" : "Batch"}
            </label>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 items-stretch">
        <textarea
          className="flex-1 bg-slate-900 border border-slate-600 rounded-lg p-3 text-white text-sm placeholder-slate-500 resize-none focus:outline-none focus:border-blue-500 transition-colors"
          rows={3}
          placeholder="Enter your prompt here…"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (!loading && prompt.trim())
                handleSubmit(e as unknown as React.FormEvent);
            }
          }}
        />
        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="w-14 shrink-0 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-xl rounded-lg transition-colors flex items-center justify-center"
        >
          {loading ? <span className="text-sm font-normal">…</span> : "→"}
        </button>
      </form>

      {error && (
        <p className="text-red-400 text-sm bg-red-950 border border-red-800 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      {result && (
        <div className="flex flex-col gap-3">
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-3">
            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">
              Response
            </p>
            <p className="text-white text-sm">
              {result.response ?? (
                <span className="text-blue-400">
                  Queued — job_id: {result.job_id}
                </span>
              )}
            </p>
          </div>

          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">
              Green Receipt
            </p>
            <ReceiptCard receipt={result.green_receipt} />
          </div>
        </div>
      )}
    </div>
  );
}
