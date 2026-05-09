// Side-by-side carbon intensity comparison between Azure regions.
// Makes the routing decision visually legible: chosen region vs avoided baseline.
// Pure display — reads from the most recent receipt, no internal state.

import type { GreenReceipt } from "../types/receipt";

interface Props {
  receipts: GreenReceipt[];
}

// East US baseline is a fixed reference — the backend does not send it per-request.
const EASTUS_BASELINE = 386; // gCO₂/kWh — historical average for US-MIDA-PJM

const REGION_LABELS: Record<string, string> = {
  westeurope: "West Europe (NL)",
  eastus: "East US",
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
  const chosenRegion = latest.region_used;
  const chosenLabel = REGION_LABELS[chosenRegion] ?? chosenRegion;
  const westEuropeChosen = chosenRegion === "westeurope";

  const rawSavingsPct = (1 - chosenIntensity / EASTUS_BASELINE) * 100;
  const savingsPct = Math.max(0, rawSavingsPct).toFixed(0);
  const chosenBarPct = Math.min((chosenIntensity / EASTUS_BASELINE) * 100, 100);

  return (
    <div className="h-full rounded-xl border-2 border-slate-600 bg-slate-800 p-4 flex flex-col gap-4">
      <p className="text-slate-300 text-sm font-semibold uppercase tracking-wide">
        Carbon Intensity by Region
      </p>

      {/* West Europe */}
      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-sm">
          <span className="text-green-400 font-medium">West Europe (NL)</span>
          <span className="text-green-400 font-mono">
            {westEuropeChosen ? `${chosenIntensity} gCO₂/kWh` : "— gCO₂/kWh"}
          </span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-4 overflow-hidden">
          <div
            className="bg-green-500 h-full rounded-full transition-all duration-500"
            style={{ width: westEuropeChosen ? `${chosenBarPct}%` : "0%" }}
          />
        </div>
        <p className="text-green-500 text-xs font-semibold">
          {westEuropeChosen ? "SELECTED ✓" : "AVOIDED"}
        </p>
      </div>

      {/* East US */}
      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-sm">
          <span className="text-amber-400 font-medium">East US</span>
          <span className="text-amber-400 font-mono">
            {!westEuropeChosen
              ? `${chosenIntensity} gCO₂/kWh`
              : `${EASTUS_BASELINE} gCO₂/kWh`}
          </span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-4 overflow-hidden">
          <div
            className="bg-amber-500 h-full rounded-full transition-all duration-500"
            style={{ width: westEuropeChosen ? "100%" : `${chosenBarPct}%` }}
          />
        </div>
        <p className="text-amber-500 text-xs font-semibold">
          {westEuropeChosen ? "AVOIDED" : "SELECTED ✓"}
        </p>
      </div>

      <p className="text-center text-slate-300 text-sm font-medium">
        Routing to {chosenLabel} saves{" "}
        <span className="text-green-400 font-bold">{savingsPct}%</span> carbon
      </p>
    </div>
  );
}
