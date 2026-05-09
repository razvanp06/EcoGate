// Scrolling list of the 10 most recent receipts, newest at top.
// Receives receipts from Dashboard — does no polling of its own.

import type { GreenReceipt } from "../types/receipt";
import ReceiptCard from "./ReceiptCard";

interface Props {
  receipts: GreenReceipt[];
}

export default function LiveFeed({ receipts }: Props) {
  const latest = [...receipts].reverse().slice(0, 10);

  return (
    <div className="h-full rounded-xl border-2 border-slate-600 bg-slate-800 p-4 flex flex-col gap-3 overflow-hidden">
      <div className="flex items-center justify-between">
        <p className="text-slate-300 text-sm font-semibold uppercase tracking-wide">
          Live Feed
        </p>
        <span className="text-xs text-slate-500">last 10</span>
      </div>

      <div className="flex-1 min-h-0 flex flex-col gap-2 overflow-y-auto">
        {latest.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">
            Waiting for requests…
          </p>
        ) : (
          latest.map((r) => <ReceiptCard key={r.request_id} receipt={r} />)
        )}
      </div>
    </div>
  );
}
