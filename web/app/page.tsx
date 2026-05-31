import Link from "next/link";
import type { RouteData } from "@/lib/types";
import { TREK_META, DAY_LIST, WAYPOINTS } from "@/lib/trekData";
import rawRouteData from "@/public/data/route.json";
import RouteMapLoader from "@/components/RouteMapLoader";

const CAMP_TYPE_LABEL: Record<string, string> = {
  staffed: "Staffed",
  trail: "Trail camp",
  layover: "Layover",
  dry: "Dry camp",
};

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center bg-white rounded-lg px-4 py-2 shadow-sm border border-stone-100">
      <span className="text-lg font-bold text-forest-800">{value}</span>
      <span className="text-xs text-stone-500">{label}</span>
    </div>
  );
}

function DayCard({ day }: { day: (typeof DAY_LIST)[number] }) {
  const isLayover = day.campType === "layover";
  const isDry = day.campType === "dry";

  return (
    <Link
      href={`/day/${day.day}/`}
      className="group block bg-white rounded-xl border border-stone-200 shadow-sm hover:shadow-md transition-all overflow-hidden"
    >
      {/* color bar */}
      <div className="h-1" style={{ backgroundColor: day.color }} />
      <div className="p-3">
        <div className="flex items-start justify-between mb-1">
          <span className="text-xs font-semibold text-stone-400 uppercase tracking-wide">Day {day.day}</span>
          <div className="flex gap-1">
            {day.hasShowers && <span title="Showers" className="text-xs">🚿</span>}
            {isDry && <span title="Dry camp" className="text-xs text-amber-600 font-bold">DRY</span>}
            {isLayover && <span className="text-xs bg-indigo-100 text-indigo-700 px-1 rounded">Layover</span>}
          </div>
        </div>
        <div className="text-xs text-stone-400 mb-1">{day.date}</div>
        <div className="font-semibold text-stone-800 text-sm leading-tight mb-2">
          {day.from}
          <span className="text-stone-400 mx-1">→</span>
          {day.to}
        </div>
        {isLayover ? (
          <div className="text-xs text-stone-400">Rest day · {CAMP_TYPE_LABEL[day.campType]}</div>
        ) : (
          <div className="flex gap-2 text-xs text-stone-500">
            <span className="font-medium">{day.miles} mi</span>
            <span className="text-green-600">+{day.gainFt.toLocaleString()}&apos;</span>
            <span className="text-red-500">-{day.lossFt.toLocaleString()}&apos;</span>
          </div>
        )}
        {day.callout && (
          <div className="mt-2 text-xs text-amber-700 bg-amber-50 rounded px-2 py-1 leading-tight">
            {day.callout}
          </div>
        )}
        {day.warning && (
          <div className="mt-2 text-xs text-red-700 bg-red-50 rounded px-2 py-1 leading-tight">
            {day.warning}
          </div>
        )}
      </div>
      <div className="px-3 pb-3">
        <span className="text-xs text-stone-400 group-hover:text-forest-700 transition-colors">
          View map →
        </span>
      </div>
    </Link>
  );
}

export default function HomePage() {
  const routeData = rawRouteData as unknown as RouteData;
  const hikingDays = DAY_LIST.filter((d) => d.campType !== "layover");
  const totalMiles = DAY_LIST.reduce((s, d) => s + d.miles, 0);

  return (
    <div className="space-y-8">
      {/* Trek header */}
      <div>
        <h1 className="text-3xl font-bold text-stone-900 mb-1">
          Crew 618-J · Philmont 2026
        </h1>
        <p className="text-stone-500 text-sm mb-4">
          {TREK_META.itinerary} · {TREK_META.route} · June 18–29, 2026
        </p>
        <div className="flex flex-wrap gap-3">
          <StatPill label="Total miles" value={`${totalMiles.toFixed(1)} mi`} />
          <StatPill label="Cumul. gain" value={`${TREK_META.totalGainFt.toLocaleString()}'`} />
          <StatPill label="Cumul. loss" value={`${TREK_META.totalLossFt.toLocaleString()}'`} />
          <StatPill label="Hiking days" value={`${hikingDays.length}`} />
          <StatPill label="High point" value={`${TREK_META.elevMaxFt.toLocaleString()} ft`} />
          <StatPill label="Low point" value={`${TREK_META.elevMinFt.toLocaleString()} ft`} />
        </div>
      </div>

      {/* Interactive route map */}
      <div>
        <h2 className="text-lg font-semibold text-stone-700 mb-3">Full Route — click any segment for day detail</h2>
        <RouteMapLoader routeData={routeData} waypoints={WAYPOINTS} height="520px" />
        <p className="text-xs text-stone-400 mt-2 text-center">
          Tiles © OpenStreetMap contributors · Route from SRTM-derived GPX
        </p>
      </div>

      {/* Day cards */}
      <div>
        <h2 className="text-lg font-semibold text-stone-700 mb-4">Day-by-Day</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {DAY_LIST.map((day) => (
            <DayCard key={day.day} day={day} />
          ))}
        </div>
      </div>

      {/* Summary map download */}
      <div className="flex gap-3 pt-2 border-t border-stone-100">
        <a
          href="/maps/summary-1.png"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-forest-700 hover:text-forest-800 underline"
        >
          Summary map (full route PNG)
        </a>
        <span className="text-stone-300">·</span>
        <Link href="/itinerary/" className="text-sm text-forest-700 hover:text-forest-800 underline">
          Full itinerary table
        </Link>
      </div>
    </div>
  );
}
