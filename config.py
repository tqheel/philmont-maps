"""Print, layout, and style configuration for Philmont topo maps.

Spec reference: §7.1 Print Parameters and §4.2 Map Styling.
"""

from __future__ import annotations

# Page geometry (Letter, portrait)
PAGE_WIDTH_IN = 8.5
PAGE_HEIGHT_IN = 11.0
MARGIN_IN = 0.5
DPI = 300
PAPER_ORIENTATION = "portrait"

# Trek identity (mirrored in trek_data.CREW_618J)
EXPEDITION = "618-J"
ITINERARY = "12-1 Challenging"
START_DATE = "2026-06-18"
END_DATE = "2026-06-29"

# Coordinate system (runtime-configurable; CLI overrides win)
GRID_TYPE = "latlon"   # "latlon" | "utm" | "both"
MAP_SCALE = "1:24000"   # default: USGS 7.5' quad scale
UTM_ZONE = 13           # Zone 13N for Philmont (Northern Hemisphere)
UTM_HEMISPHERE = "N"

# Grid display — USGS quad convention: lat/lon ticks at neatline, UTM grid in blue
SHOW_GRID_LINES = True
GRID_LINE_COLOR = "#999999"          # lat/lon grid (subdued)
GRID_LINE_WIDTH_PT = 0.3
GRID_LABEL_COLOR = "#444444"
GRID_LABEL_SIZE = 7
UTM_GRID_COLOR = "#1F4E8C"           # USGS UTM blue
UTM_GRID_WIDTH_PT = 1.0
UTM_GRID_ALPHA = 0.9
UTM_LABEL_COLOR = "#1F4E8C"

# Map styling — USGS 7.5' quad inspired (white BG, brown contours, gray hillshade)
ELEVATION_COLORMAP = None           # None → no hypsometric fill, just hillshade
MAP_BACKGROUND = "#FFFFFF"
CONTOUR_INTERVAL_FT = 40            # USGS standard contour interval for mountainous quads
CONTOUR_MAJOR_INTERVAL = 5          # every 5th line is an "index" contour (200 ft)
CONTOUR_COLOR = "#7B4F2B"           # USGS contour brown
CONTOUR_WEIGHT_PT = 0.4
CONTOUR_MAJOR_WEIGHT_PT = 0.9
CONTOUR_LABEL_SIZE = 6

# Route styling
DAY_ROUTE_COLOR = "#E31C23"
DAY_ROUTE_WIDTH_PT = 2.5
CONTEXT_ROUTE_COLOR = "#888888"
CONTEXT_ROUTE_WIDTH_PT = 1.0
CONTEXT_ROUTE_ALPHA = 0.45

# Waypoint markers
CAMP_STAFFED_COLOR = "#FF6B35"
CAMP_TRAIL_COLOR = "#004E89"
CAMP_LAYOVER_COLOR = "#9B59B6"
CAMP_DRY_COLOR = "#B07A00"
PASSTHROUGH_COLOR = "#F7B801"
TRAILHEAD_COLOR = "#444444"
MARKER_SIZE = 150

# Elevation profile
PROFILE_FILL_COLOR = "#70AD47"
PROFILE_FILL_ALPHA = 0.4
PROFILE_LINE_COLOR = "#222222"
PROFILE_LINE_WIDTH = 1.8

# Fonts (matplotlib-compatible kwargs)
FONT_HEADER = {"size": 11, "weight": "bold"}
FONT_TITLE = {"size": 11, "weight": "bold"}
FONT_AXIS = {"size": 9}
FONT_LABEL = {"size": 7, "weight": "bold"}
FONT_ANNOTATION = {"size": 7}

# Output
OUTPUT_FORMAT = "pdf"
OUTPUT_DIR = "output"

# Interpolation / DEM
INTERPOLATION_METHOD = "cubic"
GRID_RESOLUTION = 300       # samples per axis for terrain rendering
DAY_BBOX_BUFFER_DEG = 0.01  # padding around per-day bounding box

# Hillshade — USGS-style: subtle gray on white, NW light source
HILLSHADE_AZIMUTH = 315.0   # NW light source (cartographic convention)
HILLSHADE_ALTITUDE = 45.0   # sun elevation
HILLSHADE_ALPHA = 0.55      # higher alpha now that it's the only terrain fill

# GPX defaults (Garmin export)
GARMIN_SAMPLE_INTERVAL_M = 100
GARMIN_TRACK_COLOR = "#E31C23"

# Constants
FT_PER_M = 3.28084
MILES_PER_KM = 0.621371
EARTH_RADIUS_MI = 3958.7613
