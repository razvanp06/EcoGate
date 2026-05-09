// Side-by-side carbon intensity comparison between Azure regions.
// Makes the routing decision visually legible: chosen region vs avoided baseline.
// Pure display — reads from the most recent receipt, no internal state.

import type { GreenReceipt } from "../types/receipt";

interface Props {
  receipts: GreenReceipt[];
}

const EASTUS_BASELINE = 386; // gCO2/kWh — fixed high-carbon baseline for comparison
const EASTUS_LABEL = "East US";

const REGION_LABELS: Record<string, string> = {
  westeurope:    "West Europe (NL)",
  eastus:        "East US",
  swedencentral: "Sweden Central",
  northeurope:   "North Europe (IE)",
  uksouth:       "UK South",
};

export default function CarbonMap({ receipts }: Props) {
  const latest = receipts.at(-1);

  if (!latest) {
    return (
      <div className="h-full rounded-xl border-2 border-slate-600 bg-slate-800 p-4 flex flex-col gap-4">
        <p className="text-slate-300 text-sm font-semibold uppercase tracking-wide">
          Carbon Intensity by Region
        </p>
        <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
          No requests yet
        </div>
      </div>
    );
  }

  const chosenIntensity = latest.carbon_intensity;
  const chosenRegion    = latest.region_used;
  const chosenLabel     = REGION_LABELS[chosenRegion] ?? chosenRegion;
  const isEastUs        = chosenRegion === "eastus";

  const savingsPct   = Math.max(0, (1 - chosenIntensity / EASTUS_BASELINE) * 100).toFixed(0);
  const chosenBarPct = Math.min((chosenIntensity / EASTUS_BASELINE) * 100, 100);

  return (
    <div className="h-full rounded-xl border-2 border-slate-600 bg-slate-800 p-4 flex flex-col gap-4">
      <p className="text-slate-300 text-sm font-semibold uppercase tracking-wide">
        Carbon Intensity by Region
      </p>

      {/* Chosen region — always SELECTED */}
      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-sm">
          <span className="text-green-400 font-medium">{chosenLabel}</span>
          <span className="text-green-400 font-mono">{chosenIntensity} gCO2/kWh</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-4 overflow-hidden">
          <div
            className="bg-green-500 h-full rounded-full transition-all duration-500"
            style={{ width: `${chosenBarPct}%` }}
          />
        </div>
        <p className="text-green-500 text-xs font-semibold">SELECTED</p>
      </div>

      {/* East US baseline — always AVOIDED (hidden if chosen IS eastus) */}
      {!isEastUs && (
        <div className="flex flex-col gap-1">
          <div className="flex justify-between text-sm">
            <span className="text-amber-400 font-medium">{EASTUS_LABEL}</span>
            <span className="text-amber-400 font-mono">{EASTUS_BASELINE} gCO2/kWh</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-4 overflow-hidden">
            <div className="bg-amber-500 h-full rounded-full w-full" />
          </div>
          <p className="text-amber-500 text-xs font-semibold">AVOIDED</p>
        </div>
      )}

      <p className="text-center text-slate-300 text-sm font-medium mt-auto">
        Routing to {chosenLabel} saves{" "}
        <span className="text-green-400 font-bold">{savingsPct}%</span> carbon
      </p>
    </div>
  );
}
