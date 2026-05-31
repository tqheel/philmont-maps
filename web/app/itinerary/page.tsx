import Link from "next/link";
import type { Metadata } from "next";
import { TREK_META, DAY_LIST, WAYPOINTS } from "@/lib/trekData";

export const metadata: Metadata = {
  title: "Itinerary · Crew 618-J · Philmont 2026",
  description: "Full day-by-day itinerary for Crew 618-J, Itinerary 12-1 South Country Loop",
};

const CAMP_BADGE: Record<string, { label: string; cls: string }> = {
  staffed: { label: "Staffed ★", cls: "bg-green-100 text-green-700" },
  trail: { label: "Trail", cls: "bg-stone-100 text-stone-600" },
  layover: { label: "Layover", cls: "bg-indigo-100 text-indigo-700" },
  dry: { label: "Dry", cls: "bg-amber-100 text-amber-700" },
};

export default function ItineraryPage() {
  const hikingDays = DAY_LIST.filter((d) => d.campType !== "layover");
  const cumMiles = hikingDays.reduce((s, d) => s + d.miles, 0);

  return (
    <div className="space-y-10">
      {/* Header */}
      <div>
        <nav className="text-sm text-stone-500 mb-4">
          <Link href="/" className="hover:text-forest-700 transition-colors">Overview</Link>
          <span className="mx-2">/</span>
          <span className="text-stone-800 font-medium">Itinerary</span>
        </nav>
        <h1 className="text-2xl font-bold text-stone-900 mb-1">Full Itinerary</h1>
        <p className="text-stone-500 text-sm">
          {TREK_META.itinerary} · {TREK_META.route} · {TREK_META.startDate} – {TREK_META.endDate}
        </p>

        {/* Trek-level summary stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
          {[
            { label: "Total miles", value: `${cumMiles.toFixed(1)} mi` },
            { label: "Total gain", value: `+${TREK_META.totalGainFt.toLocaleString()} ft` },
            { label: "Total loss", value: `-${TREK_META.totalLossFt.toLocaleString()} ft` },
            { label: "Hiking days", value: `${hikingDays.length} days` },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white border border-stone-200 rounded-xl p-3 text-center shadow-sm">
              <div className="text-lg font-bold text-stone-800">{value}</div>
              <div className="text-xs text-stone-400 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Day-by-day table */}
      <div>
        <h2 className="text-lg font-semibold text-stone-700 mb-4">Daily Summary</h2>
        <div className="overflow-x-auto rounded-xl border border-stone-200 shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-stone-50 border-b border-stone-200">
                <th className="text-left px-4 py-3 font-semibold text-stone-500 w-20">Day</th>
                <th className="text-left px-4 py-3 font-semibold text-stone-500">Date</th>
                <th className="text-left px-4 py-3 font-semibold text-stone-500">Camp</th>
                <th className="text-left px-4 py-3 font-semibold text-stone-500 hidden sm:table-cell">Type</th>
                <th className="text-right px-4 py-3 font-semibold text-stone-500">Miles</th>
                <th className="text-right px-4 py-3 font-semibold text-stone-500 hidden md:table-cell">Gain</th>
                <th className="text-right px-4 py-3 font-semibold text-stone-500 hidden md:table-cell">Loss</th>
                <th className="text-right px-4 py-3 font-semibold text-stone-500 hidden lg:table-cell">Elev.</th>
                <th className="px-4 py-3 hidden sm:table-cell" />
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-stone-100 bg-stone-50/50">
                <td className="px-4 py-3 text-stone-400">Day 1</td>
                <td className="px-4 py-3 text-stone-400">June 18</td>
                <td className="px-4 py-3 text-stone-400">Base Camp (Camping HQ)</td>
                <td className="px-4 py-3 hidden sm:table-cell">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">Staffed ★</span>
                </td>
                <td className="px-4 py-3 text-right text-stone-400">—</td>
                <td className="px-4 py-3 text-right text-stone-400 hidden md:table-cell">—</td>
                <td className="px-4 py-3 text-right text-stone-400 hidden md:table-cell">—</td>
                <td className="px-4 py-3 text-right text-stone-400 hidden lg:table-cell">6,729 ft</td>
                <td className="px-4 py-3 hidden sm:table-cell" />
              </tr>
              {DAY_LIST.map((day) => {
                const badge = CAMP_BADGE[day.campType];
                const isLayover = day.campType === "layover";
                return (
                  <tr
                    key={day.day}
                    className="border-b border-stone-100 hover:bg-stone-50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full flex-none" style={{ backgroundColor: day.color }} />
                        <span className="font-medium text-stone-700">Day {day.day}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-stone-500">{day.date}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-stone-800">{day.to}</div>
                      <div className="text-xs text-stone-400">from {day.from}</div>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${badge.cls}`}>
                        {badge.label}
                      </span>
                      {day.hasShowers && <span className="ml-1 text-xs">🚿</span>}
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-stone-700">
                      {isLayover ? "—" : `${day.miles}`}
                    </td>
                    <td className="px-4 py-3 text-right text-green-700 hidden md:table-cell">
                      {isLayover ? "—" : `+${day.gainFt.toLocaleString()}`}
                    </td>
                    <td className="px-4 py-3 text-right text-red-600 hidden md:table-cell">
                      {isLayover ? "—" : `-${day.lossFt.toLocaleString()}`}
                    </td>
                    <td className="px-4 py-3 text-right text-stone-500 hidden lg:table-cell">
                      {day.endElevFt.toLocaleString()} ft
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <Link
                        href={`/day/${day.day}/`}
                        className="text-xs text-forest-700 hover:text-forest-800 underline whitespace-nowrap"
                      >
                        Map →
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {/* Totals row */}
              <tr className="bg-stone-50 border-t-2 border-stone-200">
                <td colSpan={4} className="px-4 py-3 font-semibold text-stone-700">TOTAL</td>
                <td className="px-4 py-3 text-right font-bold text-stone-900">
                  {TREK_META.totalMiles} mi
                </td>
                <td className="px-4 py-3 text-right font-bold text-green-700 hidden md:table-cell">
                  +{TREK_META.totalGainFt.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right font-bold text-red-600 hidden md:table-cell">
                  -{TREK_META.totalLossFt.toLocaleString()}
                </td>
                <td colSpan={2} className="hidden lg:table-cell" />
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs text-stone-400 mt-2">
          Gain/loss = cumulative ascent/descent for the day (total vertical feet traveled, not net change).
        </p>
      </div>

      {/* GPS Waypoints */}
      <div>
        <h2 className="text-lg font-semibold text-stone-700 mb-4">GPS Waypoints (WGS84)</h2>
        <div className="overflow-x-auto rounded-xl border border-stone-200 shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-stone-50 border-b border-stone-200">
                <th className="text-left px-4 py-3 font-semibold text-stone-500">Waypoint</th>
                <th className="text-left px-4 py-3 font-semibold text-stone-500 hidden sm:table-cell">Type</th>
                <th className="text-right px-4 py-3 font-semibold text-stone-500">Lat</th>
                <th className="text-right px-4 py-3 font-semibold text-stone-500">Lon</th>
                <th className="text-right px-4 py-3 font-semibold text-stone-500 hidden md:table-cell">Elev.</th>
              </tr>
            </thead>
            <tbody>
              {WAYPOINTS.map((wp) => (
                <tr key={`${wp.name}-${wp.day}`} className="border-b border-stone-100 hover:bg-stone-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-stone-800">{wp.name}</td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      wp.type === "passthrough"
                        ? "bg-stone-100 text-stone-500"
                        : wp.type.startsWith("trailhead")
                        ? "bg-forest-100 text-forest-800 bg-green-100 text-green-800"
                        : wp.campType
                        ? CAMP_BADGE[wp.campType]?.cls
                        : ""
                    }`}>
                      {wp.type === "passthrough"
                        ? "Passthrough"
                        : wp.type === "trailhead_start"
                        ? "Trailhead start"
                        : wp.type === "trailhead_end"
                        ? "Trailhead end"
                        : wp.campType
                        ? CAMP_BADGE[wp.campType]?.label
                        : "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-stone-600 font-mono text-xs">
                    {wp.lat.toFixed(6)}
                  </td>
                  <td className="px-4 py-3 text-right text-stone-600 font-mono text-xs">
                    {wp.lon.toFixed(6)}
                  </td>
                  <td className="px-4 py-3 text-right text-stone-500 hidden md:table-cell">
                    {wp.elevFt.toLocaleString()} ft
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Logistics */}
      <div className="bg-white rounded-xl border border-stone-200 p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-700 mb-4">Logistics Overview</h2>
        <div className="grid sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="font-medium text-stone-600 mb-1">Commissary / Food Resupply</p>
            <ul className="space-y-1 text-stone-500">
              <li><span className="font-medium text-stone-700">Day 1</span> — Camping HQ commissary</li>
              <li><span className="font-medium text-stone-700">Day 5</span> — Apache Springs commissary</li>
              <li><span className="font-medium text-stone-700">Day 8</span> — Miners Park commissary</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-stone-600 mb-1">Showers Available</p>
            <ul className="space-y-1 text-stone-500">
              <li><span className="font-medium text-stone-700">Days 3</span> — Abreu</li>
              <li><span className="font-medium text-stone-700">Days 6–7</span> — Beaubien</li>
              <li><span className="font-medium text-stone-700">Day 8</span> — Miners Park</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-stone-600 mb-1">Pre-Trip Reservations Required</p>
            <ul className="space-y-1 text-stone-500">
              <li>Horse rides at Beaubien (book Day 1 at Base Camp)</li>
              <li>Adult fishing licenses (purchase before trail; not available backcountry)</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-stone-600 mb-1">Water Notes</p>
            <ul className="space-y-1 text-stone-500">
              <li>Purified water at all staffed camps</li>
              <li><span className="font-medium text-amber-700">Day 11</span> — Dry camp; carry 2–3 L into Stockade Ridge</li>
              <li>All natural sources must be filtered/purified</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
