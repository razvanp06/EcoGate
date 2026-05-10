// Hero metric — full-width box at the top. Shows total CO₂ saved, km equivalent,
// request count, avg savings %, and cache hit count. Pure display, no fetching.

interface Props {
  stats: {
    totalSaved: number;
    totalPct: number;
    cacheHits: number;
    count: number;
  };
}

export default function SavingsCounter({ stats }: Props) {
  const { totalSaved, totalPct, cacheHits, count } = stats;
  const avgSavingsPct = count ? totalPct / count : 0;
  const googleSearches = Math.round(totalSaved / 0.2);

  return (
    <div className="h-full rounded-xl border-2 border-green-500 bg-slate-800 p-5 flex flex-col justify-between">
      <p className="text-slate-400 text-xs uppercase tracking-widest font-medium">
        CO₂ Saved vs. Direct API Calls
      </p>

      <div>
        <p className="text-green-400 text-5xl font-bold tabular-nums leading-none">
          {totalSaved.toFixed(4)}
          <span className="text-2xl ml-2 text-green-500">gCO₂</span>
        </p>
        <p className="text-slate-400 text-sm mt-1">
          ≈ {googleSearches} Google {googleSearches === 1 ? "search" : "searches"} equivalent
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Chip label="Requests" value={String(count)} />
        <Chip label="Avg Reduction" value={`${avgSavingsPct.toFixed(1)}%`} />
        <Chip label="Cache Hits" value={String(cacheHits)} />
      </div>
    </div>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-center">
      <p className="text-slate-400 text-xs uppercase tracking-wide truncate">
        {label}
      </p>
      <p className="text-white text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}
