import pytest
import xml.etree.ElementTree as ET
from kml_parser import haversine_miles, _strip_passthrough_suffix, PathPoint, Waypoint, KMLParser

def test_haversine_miles():
    # Rayado Trailhead to Olympia (approx)
    lat1, lon1 = 36.365230, -104.930362
    lat2, lon2 = 36.371734, -104.968928
    
    dist = haversine_miles(lat1, lon1, lat2, lon2)
    assert 2.1 <= dist <= 2.3

def test_haversine_zero_distance():
    lat, lon = 36.365230, -104.930362
    assert haversine_miles(lat, lon, lat, lon) == 0.0

def test_strip_passthrough_suffix():
    assert _strip_passthrough_suffix("Apache Springs (passthrough)") == "Apache Springs"
    assert _strip_passthrough_suffix("Beaubien (layover)") == "Beaubien"
    assert _strip_passthrough_suffix("Normal Camp") == "Normal Camp"
    assert _strip_passthrough_suffix("") == ""

@pytest.fixture
def mock_kml(tmp_path):
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Path</name>
      <LineString>
        <coordinates>
          -104.93,36.36,0
          -104.94,36.37,0
          -104.95,36.38,0
          -104.96,36.39,0
          -104.97,36.40,0
          -104.98,36.41,0
          -104.99,36.42,0
          -105.00,36.43,0
          -105.01,36.44,0
          -105.02,36.45,0
          -105.03,36.46,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Start</name>
      <styleUrl>#markerStart</styleUrl>
      <Point><coordinates>-104.93,36.36,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Olympia</name>
      <styleUrl>#markerCamp</styleUrl>
      <Point><coordinates>-104.94,36.37,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Abreu</name>
      <styleUrl>#markerCamp</styleUrl>
      <Point><coordinates>-104.95,36.38,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Fish Camp</name>
      <styleUrl>#markerCamp</styleUrl>
      <Point><coordinates>-104.96,36.39,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Buck Creek</name>
      <styleUrl>#markerCamp</styleUrl>
      <Point><coordinates>-104.97,36.40,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Beaubien (layover)</name>
      <styleUrl>#markerCamp</styleUrl>
      <Point><coordinates>-104.98,36.41,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Miners Park</name>
      <styleUrl>#markerCamp</styleUrl>
      <Point><coordinates>-104.99,36.42,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Bear Caves</name>
      <styleUrl>#markerCamp</styleUrl>
      <Point><coordinates>-105.00,36.43,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Urraca</name>
      <styleUrl>#markerCamp</styleUrl>
      <Point><coordinates>-105.01,36.44,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Stockade Ridge</name>
      <styleUrl>#markerCamp</styleUrl>
      <Point><coordinates>-105.02,36.45,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>End</name>
      <styleUrl>#markerEnd</styleUrl>
      <Point><coordinates>-105.03,36.46,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>Apache Springs (passthrough)</name>
      <styleUrl>#markerPass</styleUrl>
      <Point><coordinates>-104.965,36.395,0</coordinates></Point>
    </Placemark>
  </Document>
</kml>
"""
    kml_file = tmp_path / "test.kml"
    kml_file.write_text(kml_content)
    return kml_file

def test_extract_path(mock_kml):
    parser = KMLParser(mock_kml)
    path = parser.extract_path()
    assert len(path) == 11
    assert path[0].lon == -104.93
    assert path[0].lat == 36.36

def test_extract_waypoints(mock_kml):
    parser = KMLParser(mock_kml)
    waypoints = parser.extract_waypoints()
    assert len(waypoints) == 12
    assert "Start" in waypoints
    assert waypoints["Start"].type == "trailhead_start"
    assert "Olympia" in waypoints
    assert waypoints["Olympia"].type == "camp"
    assert "Apache Springs (passthrough)" in waypoints
    assert waypoints["Apache Springs (passthrough)"].type == "passthrough"

def test_snap_to_path():
    path = [
        PathPoint(lon=-104.0, lat=36.0, index=0),
        PathPoint(lon=-104.1, lat=36.1, index=1),
        PathPoint(lon=-104.2, lat=36.2, index=2),
    ]
    wp = Waypoint(name="Test", type="camp", lon=-104.101, lat=36.101)
    
    idx, dist = KMLParser.snap_to_path(wp, path)
    assert idx == 1
    assert dist < 0.1

def test_segment_path_by_camps(mock_kml):
    parser = KMLParser(mock_kml)
    path = parser.extract_path()
    waypoints = parser.extract_waypoints()
    segments = parser.segment_path_by_camps(path, waypoints)
    
    # Expected days: 2, 3, 4, 5, 6, 7 (layover), 8, 9, 10, 11, 12
    assert len(segments) == 11
    assert 2 in segments
    assert segments[2].from_camp == "Start"
    assert segments[2].to_camp == "Olympia"
    assert len(segments[2].path) == 2
    
    assert 7 in segments
    assert segments[7].from_camp == "Beaubien (layover)"
    assert segments[7].to_camp == "Beaubien (layover)"
    assert len(segments[7].path) == 1
    
def test_segment_path_by_camps_reversed_path(mock_kml):
    parser = KMLParser(mock_kml)
    path = parser.extract_path()
    # Reverse the path points but keep indices
    reversed_path = list(reversed(path))
    for idx, p in enumerate(reversed_path):
        p.index = idx
        
    waypoints = parser.extract_waypoints()
    # Now 'Start' will be at the end of the path list, and 'End' at the beginning.
    segments = parser.segment_path_by_camps(reversed_path, waypoints)
    
    # Day 2: Start to Olympia. 
    # In reversed_path, Start is at index 10, Olympia is at index 9.
    # The code should now reverse [9:11] to get [Start, Olympia].
    day2 = segments[2]
    assert day2.from_camp == "Start"
    assert day2.to_camp == "Olympia"
    # First point should be Start (at index 10 in reversed_path before reversal)
    assert day2.path[0].lat == waypoints["Start"].lat
    assert day2.path[-1].lat == waypoints["Olympia"].lat
