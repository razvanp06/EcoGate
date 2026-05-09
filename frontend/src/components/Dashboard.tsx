// Root layout component and single source of truth for receipt state.
// Loads existing history once on mount, then appends new receipts via callback from QueryTester.

import { useState, useEffect } from "react";
import type { GreenReceipt } from "../types/receipt";
import { fetchReceipts } from "../api/gateway";
import SavingsCounter from "./SavingsCounter";
import RouteBreakdown from "./RouteBreakdown";
import CarbonMap from "./CarbonMap";
import QueryTester from "./QueryTester";
import LiveFeed from "./LiveFeed";

interface Stats {
  totalSaved: number;
  totalPct: number;
  cacheHits: number;
  count: number;
}

function statsFromReceipts(data: GreenReceipt[]): Stats {
  return {
    totalSaved: data.reduce((s, r) => s + r.gco2_saved, 0),
    totalPct: data.reduce((s, r) => s + r.savings_pct, 0),
    cacheHits: data.filter((r) => r.cache_hit).length,
    count: data.length,
  };
}

export default function Dashboard() {
  const [receipts, setReceipts] = useState<GreenReceipt[]>([]);
  const [stats, setStats] = useState<Stats>({
    totalSaved: 0,
    totalPct: 0,
    cacheHits: 0,
    count: 0,
  });

  useEffect(() => {
    const poll = () =>
      fetchReceipts()
        .then((data) => {
          setReceipts(data);
          setStats(statsFromReceipts(data));
        })
        .catch(() => {});
    poll();
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, []);

  function handleNewReceipt(r: GreenReceipt) {
    setReceipts((prev) => [...prev, r]);
    setStats((prev) => ({
      totalSaved: prev.totalSaved + r.gco2_saved,
      totalPct: prev.totalPct + r.savings_pct,
      cacheHits: prev.cacheHits + (r.cache_hit ? 1 : 0),
      count: prev.count + 1,
    }));
  }

  return (
    <div className="h-screen overflow-hidden bg-slate-900 text-white flex flex-col">
      {/* ── Header ── */}
      <header className="shrink-0 bg-slate-800 border-b border-slate-700 px-6 py-3 flex items-center gap-3">
        <span className="text-green-400 text-xl">🌿</span>
        <h1 className="text-lg font-semibold tracking-tight">
          EcoGateway
          <span className="text-slate-400 font-normal ml-2 text-base">
            AI Sustainability Proxy
          </span>
        </h1>
      </header>

      <main className="flex-1 min-h-0 p-4 flex flex-col gap-4 overflow-hidden">
        {/* ── Row 1 — Query tester (full width, top) ── */}
        <div className="shrink-0">
          <QueryTester onNewReceipt={handleNewReceipt} />
        </div>

        {/* ── Row 2 — Charts (two equal columns) ── */}
        <div className="flex-1 min-h-0 grid grid-cols-2 gap-4">
          <RouteBreakdown receipts={receipts} />
          <CarbonMap receipts={receipts} />
        </div>

        {/* ── Row 3 — Savings counter (bottom-left) + live feed (right) ── */}
        <div className="flex-1 min-h-0 grid grid-cols-2 gap-4">
          <SavingsCounter stats={stats} />
          <LiveFeed receipts={receipts} />
        </div>
      </main>
    </div>
  );
}
