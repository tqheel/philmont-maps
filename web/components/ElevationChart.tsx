"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { RouteDay } from "@/lib/types";

interface ElevationChartProps {
  dayData: RouteDay;
  color: string;
  label?: string;
}

export default function ElevationChart({ dayData, color, label }: ElevationChartProps) {
  if (!dayData.elevFt || dayData.elevFt.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 bg-stone-100 rounded-lg text-stone-400 text-sm">
        No elevation data (layover day)
      </div>
    );
  }

  const step = Math.max(1, Math.floor(dayData.elevFt.length / 200));
  const chartData: { dist: number; elev: number }[] = [];
  for (let i = 0; i < dayData.elevFt.length; i += step) {
    chartData.push({ dist: parseFloat(dayData.distMi[i].toFixed(2)), elev: Math.round(dayData.elevFt[i]) });
  }
  if (chartData[chartData.length - 1]?.dist !== dayData.distMi[dayData.distMi.length - 1]) {
    chartData.push({
      dist: parseFloat(dayData.distMi[dayData.distMi.length - 1].toFixed(2)),
      elev: Math.round(dayData.elevFt[dayData.elevFt.length - 1]),
    });
  }

  const elevMin = Math.min(...dayData.elevFt);
  const elevMax = Math.max(...dayData.elevFt);
  const yMin = Math.floor((elevMin - 200) / 500) * 500;
  const yMax = Math.ceil((elevMax + 200) / 500) * 500;

  return (
    <div>
      {label && <p className="text-xs text-stone-500 mb-1">{label}</p>}
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`elev-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.4} />
              <stop offset="95%" stopColor={color} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
          <XAxis
            dataKey="dist"
            type="number"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(v) => `${v} mi`}
            tick={{ fontSize: 11, fill: "#78716c" }}
            tickCount={6}
          />
          <YAxis
            domain={[yMin, yMax]}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
            tick={{ fontSize: 11, fill: "#78716c" }}
            width={36}
          />
          <Tooltip
            formatter={(v: number) => [`${v.toLocaleString()} ft`, "Elevation"]}
            labelFormatter={(l: number) => `${l.toFixed(2)} mi`}
            contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #e7e5e4" }}
          />
          <Area
            type="monotone"
            dataKey="elev"
            stroke={color}
            strokeWidth={2}
            fill={`url(#elev-${color.replace("#", "")})`}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
