export type CampType = "staffed" | "trail" | "layover" | "dry";

export interface DayInfo {
  day: number;
  date: string;
  from: string;
  to: string;
  miles: number;
  gainFt: number;
  lossFt: number;
  startElevFt: number;
  endElevFt: number;
  campType: CampType;
  hasShowers: boolean;
  color: string;
  mapImages: string[];
  programs: string[];
  callout: string | null;
  warning: string | null;
  special: string | null;
  highlight: string | null;
  tips: string[];
  passthrough: string[];
}

export interface TrekMeta {
  expedition: string;
  itinerary: string;
  route: string;
  totalMiles: number;
  totalGainFt: number;
  totalLossFt: number;
  elevMinFt: number;
  elevMaxFt: number;
  startDate: string;
  endDate: string;
  crew: string;
  numHikingDays: number;
}

export interface RouteDay {
  track: [number, number][];
  elevFt: number[];
  distMi: number[];
}

export interface RouteData {
  colors: Record<string, string>;
  days: Record<string, RouteDay>;
}

export interface Waypoint {
  name: string;
  lat: number;
  lon: number;
  day: number;
  elevFt: number;
  type: "camp" | "trailhead_start" | "trailhead_end" | "passthrough";
  campType?: CampType;
}
