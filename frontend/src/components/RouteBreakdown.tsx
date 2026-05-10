// Pie chart showing where requests are being routed.
// Uses Recharts. Four slices: cache hits, mini model, full model, deferred.
// Pure display — derives everything from receipts prop.

import type { GreenReceipt } from "../types/receipt";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Props {
  receipts: GreenReceipt[];
}

const COLORS = {
  "Cache Hit": "#22c55e",
  "Mini Model": "#86efac",
  "Full Model": "#f59e0b",
  Deferred: "#3b82f6",
};

export default function RouteBreakdown({ receipts }: Props) {
  const cacheHits = receipts.filter((r) => r.cache_hit).length;
  const deferredCount = receipts.filter((r) => r.deferred).length;
  const miniCount = receipts.filter(
    (r) => !r.cache_hit && !r.deferred && r.complexity_tier === 1,
  ).length;
  const fullCount = receipts.filter(
    (r) => !r.cache_hit && !r.deferred && r.complexity_tier === 2,
  ).length;

  const data = [
    { name: "Cache Hit", value: cacheHits },
    { name: "Mini Model", value: miniCount },
    { name: "Full Model", value: fullCount },
    { name: "Deferred", value: deferredCount },
  ].filter((d) => d.value > 0);

  return (
    <div className="h-full rounded-xl border-2 border-slate-600 bg-slate-800 p-4 flex flex-col gap-2">
      <p className="text-slate-300 text-sm font-semibold uppercase tracking-wide">
        Route Breakdown
      </p>

      {receipts.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
          No requests yet
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                labelLine={false}
                label={({
                  cx,
                  cy,
                  midAngle,
                  innerRadius,
                  outerRadius,
                  value,
                }) => {
                  const RADIAN = Math.PI / 180;
                  const radius =
                    innerRadius + (outerRadius - innerRadius) * 0.5;
                  const x = cx + radius * Math.cos(-midAngle * RADIAN);
                  const y = cy + radius * Math.sin(-midAngle * RADIAN);
                  return (
                    <text
                      x={x}
                      y={y}
                      fill="white"
                      textAnchor="middle"
                      dominantBaseline="central"
                      fontSize={13}
                      fontWeight="bold"
                    >
                      {value}
                    </text>
                  );
                }}
              >
                {data.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={COLORS[entry.name as keyof typeof COLORS]}
                  />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number, name: string) => [
                  `${value} (${receipts.length ? ((value / receipts.length) * 100).toFixed(0) : 0}%)`,
                  name,
                ]}
                contentStyle={{
                  background: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: 8,
                  color: "#f1f5f9",
                }}
                labelStyle={{ color: "#f1f5f9" }}
                itemStyle={{ color: "#f1f5f9" }}
              />
              <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 13 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
