"use client";

import dynamic from "next/dynamic";
import type { RouteData, Waypoint } from "@/lib/types";

const RouteMapDynamic = dynamic(() => import("./RouteMap"), {
  ssr: false,
  loading: () => (
    <div
      className="w-full rounded-xl bg-stone-100 animate-pulse border border-stone-200"
      style={{ height: "var(--map-h, 520px)" }}
    />
  ),
});

interface RouteMapLoaderProps {
  routeData: RouteData;
  waypoints: Waypoint[];
  selectedDay?: number;
  height?: string;
}

export default function RouteMapLoader({ height = "520px", ...props }: RouteMapLoaderProps) {
  return (
    <div style={{ "--map-h": height } as React.CSSProperties}>
      <RouteMapDynamic height={height} {...props} />
    </div>
  );
}
