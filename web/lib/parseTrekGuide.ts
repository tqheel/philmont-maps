import fs from "fs";
import path from "path";
import { marked } from "marked";

// The guide lives one level above the Next.js app root (web/../).
const GUIDE_PATH = path.join(process.cwd(), "..", "crew-618-j-trek-guide.md");

interface TrekGuide {
  introHtml: string;
  dayHtml: Record<number, string>;
}

let cached: TrekGuide | null = null;

function mdToHtml(md: string): string {
  return marked.parse(md, { async: false }) as string;
}

export function getTrekGuide(): TrekGuide {
  if (cached) return cached;

  const raw = fs.readFileSync(GUIDE_PATH, "utf-8");

  // ── Strip YAML front matter (between first pair of --- delimiters) ────────
  const withoutFrontMatter = raw.replace(/^---[\s\S]*?---\n/, "");

  // ── Intro: strip the h1 title line, keep everything through GPS Waypoints ─
  // Stop before "## Day-by-Day Camp Briefings"
  const dayByDayIdx = withoutFrontMatter.indexOf("\n## Day-by-Day Camp Briefings");
  const introMd = (dayByDayIdx >= 0
    ? withoutFrontMatter.slice(0, dayByDayIdx)
    : withoutFrontMatter
  )
    .replace(/^# .*\n/, "")   // strip h1 title (page has its own heading)
    .trim();

  // ── Per-day sections ──────────────────────────────────────────────────────
  // Each section runs from "### Day N —" to the next such heading,
  // or to "## Consolidated Gear Checklist" (first appendix).
  const appendixMarker = "\n## Consolidated Gear Checklist";
  const appendixIdx = withoutFrontMatter.indexOf(appendixMarker);
  const daysEnd = appendixIdx >= 0 ? appendixIdx : withoutFrontMatter.length;

  const dayRe = /^### Day (\d+) —[^\n]*/gm;
  const matches: { day: number; start: number }[] = [];
  let m: RegExpExecArray | null;
  while ((m = dayRe.exec(withoutFrontMatter)) !== null) {
    matches.push({ day: parseInt(m[1]), start: m.index });
  }

  const dayHtml: Record<number, string> = {};
  for (let i = 0; i < matches.length; i++) {
    const { day, start } = matches[i];
    const end = i + 1 < matches.length ? matches[i + 1].start : daysEnd;
    const section = withoutFrontMatter
      .slice(start, end)
      .replace(/^### Day \d+ —[^\n]*\n/, "") // strip heading (page shows title)
      .replace(/\n---\s*$/, "")               // strip trailing hr
      .trim();
    dayHtml[day] = mdToHtml(section);
  }

  cached = { introHtml: mdToHtml(introMd), dayHtml };
  return cached;
}
