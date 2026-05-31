"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import type { RouteData, Waypoint } from "@/lib/types";

interface RouteMapProps {
  routeData: RouteData;
  waypoints: Waypoint[];
  selectedDay?: number;
  height?: string;
}

export default function RouteMap({
  routeData,
  waypoints,
  selectedDay,
  height = "520px",
}: RouteMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("leaflet").Map | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    // Leaflet accesses window — dynamic import keeps it client-only
    import("leaflet").then((L) => {
      // Fix default icon path issue in webpack/Next.js
      // @ts-expect-error leaflet private API
      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      const map = L.map(containerRef.current!, {
        center: [36.41, -105.03],
        zoom: 11,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© <a href='https://openstreetmap.org'>OpenStreetMap</a> contributors",
        maxZoom: 17,
      }).addTo(map);

      // Draw day track segments
      Object.entries(routeData.days).forEach(([dayStr, dayData]) => {
        const day = parseInt(dayStr);
        if (!dayData.track || dayData.track.length === 0) return;

        const color = routeData.colors[dayStr] ?? "#888";
        const isSelected = selectedDay === day;
        const isOverview = selectedDay == null;

        const weight = isSelected ? 5 : isOverview ? 3 : 2;
        const opacity = isSelected ? 1 : isOverview ? 0.85 : 0.25;

        const line = L.polyline(dayData.track, { color, weight, opacity }).addTo(map);

        line.bindTooltip(`Day ${day}`, { sticky: true });
        line.on("click", () => router.push(`/day/${day}/`));
        line.on("mouseover", () => line.setStyle({ weight: weight + 2, opacity: 1 }));
        line.on("mouseout", () => line.setStyle({ weight, opacity }));
      });

      // Camp markers
      waypoints.forEach((wp) => {
        if (wp.type === "passthrough") return; // skip passthrough dots on overview

        const color = wp.type === "trailhead_start" || wp.type === "trailhead_end"
          ? "#1a472a"
          : routeData.colors[String(wp.day)] ?? "#555";

        const size = wp.type.startsWith("trailhead") ? 12 : 9;

        const marker = L.circleMarker([wp.lat, wp.lon], {
          radius: size / 2,
          color: "#fff",
          weight: 2,
          fillColor: color,
          fillOpacity: 1,
        }).addTo(map);

        const elevStr = wp.elevFt.toLocaleString();
        marker.bindPopup(
          `<strong>${wp.name}</strong><br/>${elevStr} ft<br/><em>Day ${wp.day}</em>`,
          { maxWidth: 160 }
        );

        if (selectedDay != null && wp.day === selectedDay) {
          marker.openPopup();
        }
      });

      mapRef.current = map;
    });

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [routeData, waypoints, selectedDay, router]);

  // Leaflet CSS — loaded at module level in the useEffect via CDN link tag
  useEffect(() => {
    if (document.getElementById("leaflet-css")) return;
    const link = document.createElement("link");
    link.id = "leaflet-css";
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);
  }, []);

  return (
    <div
      ref={containerRef}
      style={{ height }}
      className="w-full rounded-xl overflow-hidden shadow-md border border-stone-200"
    />
  );
}
