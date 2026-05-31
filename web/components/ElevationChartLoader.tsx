"use client";

import dynamic from "next/dynamic";
import type { RouteDay } from "@/lib/types";

const ElevationChartDynamic = dynamic(() => import("./ElevationChart"), {
  ssr: false,
  loading: () => (
    <div className="w-full rounded-lg bg-stone-100 animate-pulse" style={{ height: 220 }} />
  ),
});

interface ElevationChartLoaderProps {
  dayData: RouteDay;
  color: string;
  label?: string;
}

export default function ElevationChartLoader(props: ElevationChartLoaderProps) {
  return <ElevationChartDynamic {...props} />;
}
