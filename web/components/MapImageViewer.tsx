"use client";

import { useState } from "react";
import Image from "next/image";

interface MapImageViewerProps {
  images: string[];
  day: number;
}

// next/image with unoptimized:true + static export does NOT auto-prefix basePath.
// Prefix all image paths manually so they resolve correctly on GitHub Pages.
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const mapSrc = (filename: string) => `${BASE}/maps/${filename}`;

export default function MapImageViewer({ images, day }: MapImageViewerProps) {
  const [current, setCurrent] = useState(0);

  if (images.length === 0) return null;

  const src = mapSrc(images[current]);

  return (
    <div className="space-y-3">
      {images.length > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-stone-500 font-medium">
            Sheet {current + 1} of {images.length}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrent((c) => Math.max(0, c - 1))}
              disabled={current === 0}
              className="px-3 py-1 text-sm bg-stone-100 hover:bg-stone-200 disabled:opacity-40 rounded-md transition-colors"
            >
              ← Prev Sheet
            </button>
            <button
              onClick={() => setCurrent((c) => Math.min(images.length - 1, c + 1))}
              disabled={current === images.length - 1}
              className="px-3 py-1 text-sm bg-stone-100 hover:bg-stone-200 disabled:opacity-40 rounded-md transition-colors"
            >
              Next Sheet →
            </button>
          </div>
        </div>
      )}

      {/* Sheet thumbnails */}
      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {images.map((img, i) => (
            <button
              key={img}
              onClick={() => setCurrent(i)}
              className={`flex-none rounded border-2 overflow-hidden transition-all ${
                i === current ? "border-blue-500 shadow-md" : "border-stone-200 opacity-60 hover:opacity-80"
              }`}
            >
              <Image
                src={mapSrc(img)}
                alt={`Day ${day} sheet ${i + 1} thumbnail`}
                width={80}
                height={104}
                className="object-cover"
              />
            </button>
          ))}
        </div>
      )}

      {/* Main map image — src already includes BASE */}
      <a href={src} target="_blank" rel="noopener noreferrer" title="Open full size">
        <Image
          src={src}
          alt={`Day ${day} topo map — sheet ${current + 1} of ${images.length}`}
          width={1275}
          height={1650}
          className="topo-map w-full h-auto rounded-lg border border-stone-200 shadow hover:shadow-md transition-shadow cursor-zoom-in"
          priority
        />
      </a>
      <p className="text-center text-xs text-stone-400">
        Click map to open full resolution
      </p>
    </div>
  );
}
