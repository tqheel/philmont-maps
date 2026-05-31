"""Crew 618-J trek metadata.

Static data for Itinerary 12-1 (South Country Loop, 12 days, 2026-06-18 — 2026-06-29).
Spec reference: §7.2.
"""

from __future__ import annotations

from datetime import date


CREW_618J = {
    "expedition": "618-J",
    "itinerary": "12-1 Challenging",
    "route": "South Country Loop",
    "total_distance_miles": 53.3,
    "total_elevation_gain_ft": 30700,
    "total_elevation_loss_ft": 27540,
    "elevation_range": (6729, 9343),
    "start_date": date(2026, 6, 18),
    "end_date": date(2026, 6, 29),
    "trailhead": "Rayado Trailhead",
    "base_camp": "Camping HQ",
}


# Day → camp metadata. Day 1 is travel to Philmont; the trek's first hiking
# day is Day 2 (Base Camp → Olympia).
CAMPS = {
    1:  {"name": "Base Camp (Camping HQ)",         "elevation": 6729, "type": "staffed"},
    2:  {"name": "Olympia",                         "elevation": 6731, "type": "trail"},
    3:  {"name": "Abreu",                           "elevation": 7350, "type": "staffed"},
    4:  {"name": "Fish Camp",                       "elevation": 8500, "type": "trail"},
    5:  {"name": "Buck Creek",                      "elevation": 9131, "type": "trail"},
    6:  {"name": "Beaubien",                        "elevation": 9330, "type": "staffed"},
    7:  {"name": "Beaubien (layover)",              "elevation": 9330, "type": "layover"},
    8:  {"name": "Miners Park",                     "elevation": 8002, "type": "staffed"},
    9:  {"name": "Bear Caves",                      "elevation": 8423, "type": "trail"},
    10: {"name": "Urraca",                          "elevation": 7968, "type": "staffed"},
    11: {"name": "Stockade Ridge",                  "elevation": 7400, "type": "dry"},
    12: {"name": "Base Camp (via Tooth of Time)",   "elevation": 6729, "type": "staffed"},
}


# Official itinerary distances (use these for planning; some days differ from
# the raw KML — see spec §2.3).
DAYS = {
    2:  {"from": "Base Camp",      "to": "Olympia",        "miles": 2.6,
         "gain": 520,  "loss": 300},
    3:  {"from": "Olympia",        "to": "Abreu",          "miles": 3.3,
         "gain": 600,  "loss": 110},
    4:  {"from": "Abreu",          "to": "Fish Camp",      "miles": 7.9,
         "gain": 6970, "loss": 5480,
         "callout": "Hardest day — 6,970' cumulative gain"},
    5:  {"from": "Fish Camp",      "to": "Buck Creek",     "miles": 7.5,
         "gain": 3840, "loss": 3380,
         "passthrough": ["Apache Springs"]},
    6:  {"from": "Buck Creek",     "to": "Beaubien",       "miles": 3.3,
         "gain": 1740, "loss": 1570,
         "callout": "Horse rides, chuckwagon dinner at Beaubien"},
    7:  {"from": "Beaubien",       "to": "Beaubien",       "miles": 0.0,
         "gain": 0,    "loss": 0,
         "special": "Layover — Conservation Project"},
    8:  {"from": "Beaubien",       "to": "Miners Park",    "miles": 8.6,
         "gain": 4320, "loss": 5640,
         "passthrough": ["Black Mountain"],
         "callout": "Rock climbing + Black Mountain approach"},
    9:  {"from": "Miners Park",    "to": "Bear Caves",     "miles": 3.1,
         "gain": 1780, "loss": 1380,
         "passthrough": ["Crater Lake"]},
    10: {"from": "Bear Caves",     "to": "Urraca",         "miles": 4.6,
         "gain": 1780, "loss": 2210},
    11: {"from": "Urraca",         "to": "Stockade Ridge", "miles": 4.7,
         "gain": 1310, "loss": 1750,
         "passthrough": ["RMSC"],
         "warning": "Dry camp — carry 2-3 L/person",
         "kml_note": "KML omits RMSC detour (~1 mi)"},
    12: {"from": "Stockade Ridge", "to": "Base Camp",      "miles": 7.7,
         "gain": 2860, "loss": 3720,
         "highlight": "Tooth of Time summit (Class 3 scramble)"},
}


# Maps camp/passthrough name → KML Placemark name. Some PhilTrek placemarks
# carry suffixes like "(layover)" or "(passthrough)" — keep both forms.
KML_CAMP_NAMES = [
    "Start",
    "Olympia",
    "Abreu",
    "Fish Camp",
    "Buck Creek",
    "Beaubien (layover)",
    "Miners Park",
    "Bear Caves",
    "Urraca",
    "Stockade Ridge",
    "End",
]


# Adjacent-camp pair → trek day number. Day 7 is a Beaubien layover with no path.
DAY_SEGMENT_MAP = {
    ("Start",              "Olympia"):           2,
    ("Olympia",            "Abreu"):             3,
    ("Abreu",              "Fish Camp"):         4,
    ("Fish Camp",          "Buck Creek"):        5,
    ("Buck Creek",         "Beaubien (layover)"): 6,
    ("Beaubien (layover)", "Miners Park"):       8,
    ("Miners Park",        "Bear Caves"):        9,
    ("Bear Caves",         "Urraca"):            10,
    ("Urraca",             "Stockade Ridge"):    11,
    ("Stockade Ridge",     "End"):               12,
}


def camp_for_day(day: int) -> dict:
    return CAMPS[day]


def get_day(day: int) -> dict:
    return DAYS[day]
