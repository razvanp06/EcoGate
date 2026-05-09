// Single receipt card — used by LiveFeed and QueryTester.
// Color-coded by outcome: green = cache, light-green = mini, amber = full, blue = deferred.
// Pure display — no state, no side effects.

import type { GreenReceipt } from "../types/receipt";

interface Props {
  receipt: GreenReceipt;
}

export default function ReceiptCard({ receipt }: Props) {
  const time = new Date(receipt.timestamp).toLocaleTimeString("en-GB");
  const compressionSaved = (100 - receipt.compression_ratio * 100).toFixed(0);

  const isMini = receipt.complexity_tier === 1;

  const borderColor = receipt.cache_hit
    ? "border-green-500"
    : receipt.deferred
      ? "border-blue-500"
      : isMini
        ? "border-green-400"
        : "border-amber-500";

  const bgColor = receipt.cache_hit
    ? "bg-green-950"
    : receipt.deferred
      ? "bg-blue-950"
      : isMini
        ? "bg-slate-800"
        : "bg-amber-950";

  return (
    <div
      className={`rounded-lg border-l-4 ${borderColor} ${bgColor} p-3 flex flex-col gap-1`}
    >
      {/* Line 1 — badge */}
      <div className="flex items-center gap-2">
        {receipt.cache_hit ? (
          <Badge color="green">CACHE HIT</Badge>
        ) : receipt.deferred ? (
          <Badge color="blue">DEFERRED</Badge>
        ) : (
          <Badge color={isMini ? "green" : "amber"}>
            {receipt.model_used} · {receipt.region_used}
          </Badge>
        )}
      </div>

      {/* Line 2 — explanation */}
      <p className="text-slate-300 text-xs leading-relaxed">
        {receipt.route_explanation}
      </p>

      {/* Line 3 — numbers */}
      <p className="text-slate-400 text-xs tabular-nums">
        {receipt.gco2_this_request.toFixed(4)} gCO₂
        {" · "}saved {receipt.savings_pct.toFixed(0)}%{" · "}
        {receipt.original_tokens}→{receipt.compressed_tokens} tokens (
        {compressionSaved}% compressed)
      </p>

      {/* Line 4 — timestamp */}
      <p className="text-slate-500 text-xs">{time}</p>
    </div>
  );
}

function Badge({
  color,
  children,
}: {
  color: "green" | "amber" | "blue";
  children: React.ReactNode;
}) {
  const cls =
    color === "green"
      ? "bg-green-900 text-green-300 border-green-700"
      : color === "amber"
        ? "bg-amber-900 text-amber-300 border-amber-700"
        : "bg-blue-900 text-blue-300 border-blue-700";
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cls}`}>
      {children}
    </span>
  );
}
