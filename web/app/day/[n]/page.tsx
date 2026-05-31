import Link from "next/link";
import type { Metadata } from "next";
import type { RouteData } from "@/lib/types";
import { DAYS, WAYPOINTS, getPrevDay, getNextDay } from "@/lib/trekData";
import rawRouteData from "@/public/data/route.json";
import MapImageViewer from "@/components/MapImageViewer";
import RouteMapLoader from "@/components/RouteMapLoader";
import ElevationChartLoader from "@/components/ElevationChartLoader";
import { getTrekGuide } from "@/lib/parseTrekGuide";

export async function generateStaticParams() {
  return Object.keys(DAYS).map((n) => ({ n }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ n: string }>;
}): Promise<Metadata> {
  const { n } = await params;
  const day = DAYS[parseInt(n)];
  if (!day) return { title: "Day not found" };
  return {
    title: `Day ${day.day} — ${day.to} · Crew 618-J`,
    description: `${day.from} → ${day.to} · ${day.miles} mi · +${day.gainFt}' -${day.lossFt}'`,
  };
}

const CAMP_TYPE_COLORS: Record<string, string> = {
  staffed: "bg-green-100 text-green-800",
  trail: "bg-stone-100 text-stone-700",
  layover: "bg-indigo-100 text-indigo-800",
  dry: "bg-amber-100 text-amber-800",
};

const CAMP_TYPE_LABEL: Record<string, string> = {
  staffed: "Staffed camp",
  trail: "Trail camp",
  layover: "Layover",
  dry: "Dry camp",
};

export default async function DayPage({
  params,
}: {
  params: Promise<{ n: string }>;
}) {
  const { n } = await params;
  const dayNum = parseInt(n);
  const day = DAYS[dayNum];

  if (!day) {
    return (
      <div className="text-center py-20">
        <p className="text-stone-500">Day not found.</p>
        <Link href="/" className="text-forest-700 underline mt-2 block">Back to overview</Link>
      </div>
    );
  }

  const routeData = rawRouteData as unknown as RouteData;
  const dayRouteData = routeData.days[String(dayNum)];
  const prevDay = getPrevDay(dayNum);
  const nextDay = getNextDay(dayNum);
  const isLayover = day.campType === "layover";
  const { dayHtml } = getTrekGuide();
  const guideHtml = dayHtml[dayNum] ?? null;

  // Passthrough waypoints for this day
  const dayWaypoints = WAYPOINTS.filter(
    (wp) => wp.day === dayNum || (day.passthrough.some((p) => wp.name.startsWith(p)))
  );

  return (
    <div className="space-y-8">
      {/* Breadcrumb + nav */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <nav className="text-sm text-stone-500">
          <Link href="/" className="hover:text-forest-700 transition-colors">Overview</Link>
          <span className="mx-2">/</span>
          <span className="text-stone-800 font-medium">Day {day.day}</span>
        </nav>
        <div className="flex gap-2">
          {prevDay && (
            <Link
              href={`/day/${prevDay}/`}
              className="text-sm px-3 py-1.5 bg-white border border-stone-200 rounded-lg hover:bg-stone-50 transition-colors"
            >
              ← Day {prevDay}
            </Link>
          )}
          {nextDay && (
            <Link
              href={`/day/${nextDay}/`}
              className="text-sm px-3 py-1.5 bg-white border border-stone-200 rounded-lg hover:bg-stone-50 transition-colors"
            >
              Day {nextDay} →
            </Link>
          )}
        </div>
      </div>

      {/* Day header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-4 h-4 rounded-full flex-none" style={{ backgroundColor: day.color }} />
          <span className="text-sm text-stone-400 font-medium uppercase tracking-wide">
            Day {day.day} · {day.date}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CAMP_TYPE_COLORS[day.campType]}`}>
            {CAMP_TYPE_LABEL[day.campType]}
          </span>
          {day.hasShowers && (
            <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
              Showers
            </span>
          )}
        </div>
        <h1 className="text-3xl font-bold text-stone-900">
          {day.from}
          <span className="text-stone-400 mx-3">→</span>
          {day.to}
        </h1>
      </div>

      {/* Trek guide — full day briefing */}
      {guideHtml && (
        <div
          className="trek-prose bg-white rounded-xl border border-stone-200 shadow-sm px-6 py-5 overflow-x-auto"
          dangerouslySetInnerHTML={{ __html: guideHtml }}
        />
      )}

      {/* Stats bar */}
      {!isLayover && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Distance", value: `${day.miles} mi` },
            { label: "Elev. gain", value: `+${day.gainFt.toLocaleString()} ft`, cls: "text-green-700" },
            { label: "Elev. loss", value: `-${day.lossFt.toLocaleString()} ft`, cls: "text-red-600" },
            {
              label: "Camp elevation",
              value: `${day.endElevFt.toLocaleString()} ft`,
            },
          ].map(({ label, value, cls }) => (
            <div key={label} className="bg-white rounded-xl border border-stone-200 px-4 py-3 text-center shadow-sm">
              <div className={`text-xl font-bold ${cls ?? "text-stone-800"}`}>{value}</div>
              <div className="text-xs text-stone-400 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Callouts / warnings */}
      {day.callout && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex gap-3">
          <span className="text-amber-500 text-lg">!</span>
          <p className="text-amber-800 font-medium text-sm">{day.callout}</p>
        </div>
      )}
      {day.warning && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex gap-3">
          <span className="text-red-500 text-lg">⚠</span>
          <p className="text-red-800 font-medium text-sm">{day.warning}</p>
        </div>
      )}
      {day.highlight && (
        <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 flex gap-3">
          <span className="text-green-600 text-lg">★</span>
          <p className="text-green-800 font-medium text-sm">{day.highlight}</p>
        </div>
      )}
      {day.special && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl px-4 py-3 flex gap-3">
          <span className="text-indigo-500 text-lg">ℹ</span>
          <p className="text-indigo-800 font-medium text-sm">{day.special}</p>
        </div>
      )}

      {/* Interactive route map */}
      <div>
        <h2 className="text-base font-semibold text-stone-700 mb-3">Route Map</h2>
        <RouteMapLoader
          routeData={routeData}
          waypoints={dayWaypoints}
          selectedDay={dayNum}
          height="400px"
        />
        <p className="text-xs text-stone-400 mt-1 text-center">
          Today&apos;s segment highlighted · other days faded
        </p>
      </div>

      {/* Topo map images */}
      {day.mapImages.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-stone-700 mb-3">
            Topo Map {day.mapImages.length > 1 && `(${day.mapImages.length} sheets)`}
          </h2>
          <MapImageViewer images={day.mapImages} day={dayNum} />
        </div>
      )}

      {/* Elevation profile */}
      {dayRouteData && (
        <div className="bg-white rounded-xl border border-stone-200 p-4 shadow-sm">
          <h2 className="text-base font-semibold text-stone-700 mb-3">Elevation Profile</h2>
          <ElevationChartLoader dayData={dayRouteData as RouteData["days"][string]} color={day.color} />
          {!isLayover && (
            <div className="flex justify-between text-xs text-stone-400 mt-2">
              <span>{day.from} — {day.startElevFt.toLocaleString()} ft</span>
              <span>{day.to} — {day.endElevFt.toLocaleString()} ft</span>
            </div>
          )}
        </div>
      )}

      {/* Bottom nav */}
      <div className="flex items-center justify-between pt-6 border-t border-stone-100">
        {prevDay ? (
          <Link
            href={`/day/${prevDay}/`}
            className="text-sm px-4 py-2 bg-white border border-stone-200 rounded-xl hover:bg-stone-50 transition-colors"
          >
            ← Day {prevDay}
          </Link>
        ) : <span />}
        <Link href="/" className="text-sm text-stone-400 hover:text-forest-700 transition-colors">
          Overview
        </Link>
        {nextDay ? (
          <Link
            href={`/day/${nextDay}/`}
            className="text-sm px-4 py-2 bg-white border border-stone-200 rounded-xl hover:bg-stone-50 transition-colors"
          >
            Day {nextDay} →
          </Link>
        ) : <span />}
      </div>
    </div>
  );
}
