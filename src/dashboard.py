#!/usr/bin/env python3
"""
SatWatch - ISS Tracking Dashboard

A Streamlit dashboard that displays the International Space Station's
current position on an interactive world map with real-time updates.

Author: SatWatch Project
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional
import math
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import numpy as np

# Add src directory to path to import iss_tracker_json functions
sys.path.insert(0, str(Path(__file__).parent))
from iss_tracker_json import (
    load_iss_tle_from_file,
    download_iss_tle_json,
    parse_tle_from_json,
    calculate_iss_position
)
import requests
import json
from skyfield.api import load, EarthSatellite


def fetch_satellites(catnr_list: list) -> list:
    """
    Fetch TLE data for multiple satellites by their NORAD catalog numbers.
    
    This function takes a list of NORAD catalog numbers and fetches 3LE (three-line element)
    format data from CelesTrak. The 3LE format includes TLE lines directly, which is
    what Skyfield needs for position calculations.
    
    Args:
        catnr_list: List of NORAD catalog numbers (e.g., [25544, 44713, 34009])
        
    Returns:
        list: List of satellite dictionaries with TLE data. Each dict contains:
            - OBJECT_NAME: Satellite name
            - TLE_LINE1: First line of TLE data
            - TLE_LINE2: Second line of TLE data
            - NORAD_CAT_ID: NORAD catalog ID (extracted from TLE_LINE1)
    """
    satellites = []
    
    # Fetch each satellite individually
    for catnr in catnr_list:
        try:
            # CelesTrak API endpoint for individual satellite by catalog number
            # Format: https://celestrak.org/NORAD/elements/gp.php?CATNR={id}&FORMAT=3LE
            # 3LE format returns three lines: name, TLE line 1, TLE line 2
            url = "https://celestrak.org/NORAD/elements/gp.php"
            params = {
                'CATNR': catnr,  # Catalog number
                'FORMAT': '3le'  # Request 3LE (three-line element) format
            }
            
            # Download the 3LE text data with timeout
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # Raise an error if download failed
            
            # Check if response has content
            if not response.text or not response.text.strip():
                st.warning(f"No data returned for satellite {catnr} (may not exist in database)")
                continue
            
            # Parse the 3LE format (three lines: name, line1, line2)
            # Split by newline and filter out empty lines (in case of extra whitespace)
            lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
            
            # 3LE format should have exactly 3 lines per satellite
            if len(lines) < 3:
                st.warning(f"Invalid 3LE format for satellite {catnr}: Expected 3 lines, got {len(lines)}")
                continue
            
            # Extract the three lines
            name_line = lines[0]
            tle_line1 = lines[1]
            tle_line2 = lines[2]
            
            # Validate TLE line format
            if not tle_line1.startswith('1 ') or not tle_line2.startswith('2 '):
                st.warning(f"Invalid TLE format for satellite {catnr}: TLE lines don't start with '1 ' and '2 '")
                continue
            
            # Extract catalog number from TLE line 1 (positions 2-7, 0-indexed: 2:7)
            # Format: "1 25544U ..." - catalog number is at positions 2-7
            try:
                norad_cat_id = int(tle_line1[2:7].strip())
            except (ValueError, IndexError) as e:
                st.warning(f"Could not extract catalog number from TLE line 1 for satellite {catnr}: {e}")
                continue
            
            # Create satellite data dictionary in the format expected by the rest of the code
            satellite_data = {
                'OBJECT_NAME': name_line,
                'TLE_LINE1': tle_line1,
                'TLE_LINE2': tle_line2,
                'NORAD_CAT_ID': str(norad_cat_id),  # Store as string for consistency with JSON format
                'OBJECT_ID': str(norad_cat_id)  # Also include for compatibility
            }
            
            satellites.append(satellite_data)
                
        except requests.RequestException as e:
            # Network error - log but continue with other satellites
            st.warning(f"Failed to fetch satellite {catnr}: Network error - {e}")
            continue
        except Exception as e:
            # Any other error - log but continue
            st.warning(f"Unexpected error fetching satellite {catnr}: {e}")
            continue
    
    return satellites


def load_satellites_config(file_path: str = None) -> dict:
    """
    Load the satellites configuration file.
    
    The config file defines which satellites to track, their names, catalog numbers,
    and types (station, satellite, debris).
    
    Args:
        file_path: Path to satellites.json file. If None, uses 'satellites.json' in project root.
        
    Returns:
        dict: Configuration dictionary with 'tracked_satellites' list
        
    Raises:
        FileNotFoundError: If the config file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    # Default to satellites.json in project root
    if file_path is None:
        project_root = Path(__file__).parent.parent
        file_path = project_root / 'satellites.json'
    else:
        file_path = Path(file_path)
    
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"Satellites config file not found: {file_path}")
    
    # Read and parse the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config


def get_iss_data(use_local: bool = True):
    """
    Get ISS TLE data and calculate current position.
    
    Args:
        use_local: If True, use local JSON file; if False, download from API
        
    Returns:
        tuple: (position_dict, json_data, error_message)
    """
    try:
        # Load or download TLE data
        if use_local:
            json_data = load_iss_tle_from_file()
        else:
            json_data = download_iss_tle_json()
        
        # Parse TLE and calculate position
        satellite = parse_tle_from_json(json_data)
        position = calculate_iss_position(satellite)
        
        return position, json_data, None
        
    except Exception as e:
        return None, None, str(e)


def download_multiple_satellites(group: str = 'active', limit: int = 500):
    """
    Download TLE data for multiple satellites from CelesTrak.
    
    Args:
        group: CelesTrak group name ('active', 'stations', 'starlink', 'weather', etc.)
        limit: Maximum number of satellites to download (to avoid overwhelming the visualization)
        
    Returns:
        list: List of satellite dictionaries with TLE data
    """
    url = "https://celestrak.org/NORAD/elements/gp.php"
    params = {
        'GROUP': group,
        'FORMAT': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Limit the number of satellites
        if limit and len(data) > limit:
            data = data[:limit]
        
        return data
    except Exception as e:
        st.warning(f"Could not download satellite data: {e}")
        return []


def calculate_satellite_positions(satellites_data: list, current_time: datetime):
    """
    Calculate 3D positions for multiple satellites.
    
    Args:
        satellites_data: List of satellite dictionaries with TLE data
        current_time: Current datetime object
        
    Returns:
        list: List of (x, y, z, name, altitude) tuples
    """
    from skyfield.api import load
    
    ts = load.timescale()
    skyfield_time = ts.from_datetime(current_time)
    
    positions = []
    
    for sat_data in satellites_data:
        try:
            # Parse TLE from JSON data
            satellite = parse_tle_from_json(sat_data)
            
            # Calculate position
            geocentric = satellite.at(skyfield_time)
            subpoint = geocentric.subpoint()
            
            lat = subpoint.latitude.degrees
            lon = subpoint.longitude.degrees
            alt = subpoint.elevation.km
            
            # Convert to x, y, z
            x, y, z = lat_lon_alt_to_xyz(lat, lon, alt)
            
            name = sat_data.get('OBJECT_NAME', 'Unknown')
            
            # Extract catalog number (NORAD_CAT_ID is preferred, fallback to OBJECT_ID or TLE)
            catnr = None
            if 'NORAD_CAT_ID' in sat_data:
                try:
                    catnr = int(sat_data['NORAD_CAT_ID'])
                except (ValueError, TypeError):
                    pass
            
            # If NORAD_CAT_ID not available, try OBJECT_ID
            if catnr is None and 'OBJECT_ID' in sat_data:
                obj_id = sat_data['OBJECT_ID']
                try:
                    catnr = int(obj_id)
                except (ValueError, TypeError):
                    # OBJECT_ID might be international designator, try extracting from TLE
                    tle_line1 = sat_data.get('TLE_LINE1', '')
                    if tle_line1.startswith('1 '):
                        try:
                            catnr = int(tle_line1[2:7].strip())
                        except (ValueError, IndexError):
                            pass
            
            # If still no catalog number, skip this satellite
            if catnr is None:
                continue
            
            positions.append((x, y, z, name, alt, catnr))
        except Exception as e:
            # Skip satellites that can't be parsed
            continue
    
    return positions


def calculate_tracked_satellite_positions(tracked_satellites: list, satellites_tle_data: dict, current_time: datetime):
    """
    Calculate 3D positions for tracked satellites with their types.
    
    This function takes the tracked satellites config and their TLE data,
    then calculates their current positions. It also determines the type
    (station, satellite, debris) for color coding.
    
    Args:
        tracked_satellites: List of satellite config dicts with 'name', 'catnr', 'type'
        satellites_tle_data: Dict mapping catalog numbers to TLE data
        current_time: Current datetime object
        
    Returns:
        list: List of (x, y, z, name, altitude, sat_type, catnr, lat, lon) tuples
    """
    from skyfield.api import load
    
    ts = load.timescale()
    positions = []
    
    for sat_config in tracked_satellites:
        catnr = sat_config['catnr']
        sat_name = sat_config['name']
        sat_type = sat_config['type']
        
        # Get TLE data for this satellite
        tle_data = satellites_tle_data.get(catnr)
        if not tle_data:
            continue  # Skip if we don't have TLE data
        
        try:
            # Parse TLE from JSON data
            satellite = parse_tle_from_json(tle_data)
            
            # Calculate position
            geocentric = satellite.at(ts.from_datetime(current_time))
            subpoint = geocentric.subpoint()
            
            lat = subpoint.latitude.degrees
            lon = subpoint.longitude.degrees
            alt = subpoint.elevation.km
            
            # Check for NaN values
            if math.isnan(lat) or math.isnan(lon) or math.isnan(alt):
                st.warning(f"Position calculation returned NaN for {sat_name} (CATNR: {catnr})")
                continue
            
            # Convert to x, y, z
            x, y, z = lat_lon_alt_to_xyz(lat, lon, alt)
            
            # Check for NaN in converted coordinates
            if math.isnan(x) or math.isnan(y) or math.isnan(z):
                st.warning(f"Coordinate conversion returned NaN for {sat_name} (CATNR: {catnr})")
                continue
            
            # Return: (x, y, z, name, alt, sat_type, catnr) for 3D view
            # Also store lat/lon for 2D map use
            positions.append((x, y, z, sat_name, alt, sat_type, catnr, lat, lon))
        except Exception as e:
            # Log the error for debugging
            st.warning(f"Error calculating position for {sat_name} (CATNR: {catnr}): {e}")
            continue
    
    return positions


def calculate_distance_3d(pos1: tuple, pos2: tuple) -> float:
    """
    Calculate 3D Euclidean distance between two points.
    
    Args:
        pos1: (x, y, z) tuple for first point
        pos2: (x, y, z) tuple for second point
        
    Returns:
        float: Distance in kilometers
    """
    x1, y1, z1 = pos1
    x2, y2, z2 = pos2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)


def create_altitude_bands(earth_radius: float = 6371.0):
    """
    Create visualization for altitude bands (LEO, MEO, GEO).
    
    Args:
        earth_radius: Earth radius in kilometers
        
    Returns:
        list: List of Plotly traces for altitude bands
    """
    bands = []
    
    # LEO: 160-2000 km
    leo_radius = earth_radius + 2000
    leo_x, leo_y, leo_z = create_earth_sphere(leo_radius, resolution=30)
    bands.append(go.Surface(
        x=leo_x, y=leo_y, z=leo_z,
        colorscale=[[0, 'rgba(0, 100, 255, 0.1)'], [1, 'rgba(0, 100, 255, 0.1)']],
        showscale=False,
        name='LEO (160-2000 km)',
        opacity=0.15
    ))
    
    # MEO: 2000-35786 km (show at 10000 km for visibility)
    meo_radius = earth_radius + 10000
    meo_x, meo_y, meo_z = create_earth_sphere(meo_radius, resolution=30)
    bands.append(go.Surface(
        x=meo_x, y=meo_y, z=meo_z,
        colorscale=[[0, 'rgba(255, 200, 0, 0.1)'], [1, 'rgba(255, 200, 0, 0.1)']],
        showscale=False,
        name='MEO (2000-35786 km)',
        opacity=0.1
    ))
    
    return bands


def get_data_freshness_status(epoch_str: str) -> tuple[str, float, str]:
    """
    Check TLE data freshness and return status level.
    
    TLE data is typically valid for ~2 weeks. This function provides
    graduated warnings as data ages:
    - < 7 days: Fresh (green)
    - 7-10 days: Getting old (yellow warning)
    - 10-14 days: Old (orange warning)
    - > 14 days: Expired (red error)
    
    Args:
        epoch_str: Epoch string from TLE data
        
    Returns:
        tuple: (status_level, hours_old, message)
            status_level: 'fresh', 'warning', 'old', 'expired'
            hours_old: Age in hours
            message: Human-readable status message
    """
    try:
        from datetime import datetime
        epoch_dt = datetime.fromisoformat(epoch_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        # Handle timezone-aware comparison
        if epoch_dt.tzinfo is None:
            epoch_dt = epoch_dt.replace(tzinfo=timezone.utc)
        
        time_diff = now - epoch_dt
        hours_old = time_diff.total_seconds() / 3600.0
        days_old = hours_old / 24.0
        
        # Define thresholds (in hours)
        FRESH_THRESHOLD = 7 * 24  # 7 days
        WARNING_THRESHOLD = 10 * 24  # 10 days
        EXPIRED_THRESHOLD = 14 * 24  # 14 days
        
        if hours_old < FRESH_THRESHOLD:
            return 'fresh', hours_old, f"Data Fresh ({days_old:.1f} days old)"
        elif hours_old < WARNING_THRESHOLD:
            return 'warning', hours_old, f"Data Getting Old ({days_old:.1f} days old, update in {EXPIRED_THRESHOLD/24 - days_old:.1f} days)"
        elif hours_old < EXPIRED_THRESHOLD:
            return 'old', hours_old, f"Data Old ({days_old:.1f} days old, update soon - expires in {EXPIRED_THRESHOLD/24 - days_old:.1f} days)"
        else:
            return 'expired', hours_old, f"Data Expired ({days_old:.1f} days old - update required)"
    except:
        return 'expired', 999, "Unable to determine data age"


def create_map(
    latitude: float, 
    longitude: float, 
    altitude: float,
    all_satellites: Optional[List[Tuple[float, float, float, str, str, int]]] = None
):
    """
    Create a Folium map with satellite position markers.
    
    Args:
        latitude: Primary satellite (ISS) latitude in degrees (for centering)
        longitude: Primary satellite (ISS) longitude in degrees (for centering)
        altitude: Primary satellite (ISS) altitude in kilometers
        all_satellites: Optional list of (lat, lon, alt, name, sat_type, catnr) tuples
                      for all tracked satellites to display
        
    Returns:
        folium.Map: Map object with satellite markers
        
    Raises:
        ValueError: If latitude, longitude, or altitude contains NaN values
    """
    # Validate that position values are not NaN
    if math.isnan(latitude) or math.isnan(longitude) or math.isnan(altitude):
        raise ValueError(
            f"Invalid position values: latitude={latitude}, longitude={longitude}, altitude={altitude}. "
            "Position calculation may have failed. Try refreshing or using CelesTrak API data source."
        )
    
    # Create map centered on primary satellite (ISS) position
    m = folium.Map(
        location=[latitude, longitude],
        zoom_start=3,
        tiles='CartoDB dark_matter'  # Dark theme
    )
    
    # Color coding for satellite types
    type_colors = {
        'station': 'red',
        'satellite': 'blue',
        'debris': 'orange'
    }
    
    # Add markers for all tracked satellites if provided
    if all_satellites:
        for sat_data in all_satellites:
            # Handle both formats: (x, y, z, name, alt, sat_type, catnr, lat, lon) or (lat, lon, alt, name, sat_type, catnr)
            if len(sat_data) == 9:
                # New format with x, y, z and lat, lon
                x, y, z, sat_name, sat_alt, sat_type, catnr, sat_lat, sat_lon = sat_data
            elif len(sat_data) == 6:
                # Old format: (lat, lon, alt, name, sat_type, catnr)
                sat_lat, sat_lon, sat_alt, sat_name, sat_type, catnr = sat_data
            else:
                # Unexpected format, skip
                continue
            # Skip if position is invalid
            if math.isnan(sat_lat) or math.isnan(sat_lon) or math.isnan(sat_alt):
                continue
            
            # Determine color based on type
            color = type_colors.get(sat_type, 'gray')
            
            # Special styling for ISS (larger, more prominent)
            if catnr == 25544 or 'ISS' in sat_name.upper():
                radius = 12
                weight = 3
            else:
                radius = 8
                weight = 2
            
            # Add marker
            folium.CircleMarker(
                location=[sat_lat, sat_lon],
                radius=radius,
                popup=f'{sat_name}<br>Altitude: {sat_alt:.2f} km<br>Type: {sat_type}',
                tooltip=sat_name,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.8,
                weight=weight
            ).add_to(m)
    else:
        # Fallback: Just show ISS if no satellite list provided
        folium.CircleMarker(
            location=[latitude, longitude],
            radius=10,
            popup=f'ISS<br>Altitude: {altitude:.2f} km',
            tooltip='International Space Station',
            color='red',
            fill=True,
            fillColor='red',
            fillOpacity=0.8,
            weight=2
        ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: rgba(30, 30, 30, 0.8);
                border:2px solid grey; z-index:9999; font-size:14px;
                padding: 10px">
    <p><b>Satellite Types</b></p>
    <p><span style="color:red;">●</span> Stations</p>
    <p><span style="color:blue;">●</span> Satellites</p>
    <p><span style="color:orange;">●</span> Debris</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m


def lat_lon_alt_to_xyz(latitude: float, longitude: float, altitude: float, earth_radius: float = 6371.0) -> tuple[float, float, float]:
    """
    Convert latitude, longitude, and altitude to 3D Cartesian coordinates (x, y, z).
    
    Args:
        latitude: Latitude in degrees (-90 to 90)
        longitude: Longitude in degrees (-180 to 180)
        altitude: Altitude in kilometers above sea level
        earth_radius: Earth radius in kilometers (default: 6371 km)
        
    Returns:
        tuple: (x, y, z) coordinates in kilometers
    """
    # Convert degrees to radians
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    
    # Calculate radius from Earth center (Earth radius + altitude)
    r = earth_radius + altitude
    
    # Convert to Cartesian coordinates
    # x: points toward (0°N, 0°E) - intersection of equator and prime meridian
    # y: points toward (0°N, 90°E) - intersection of equator and 90°E meridian
    # z: points toward North Pole
    x = r * math.cos(lat_rad) * math.cos(lon_rad)
    y = r * math.cos(lat_rad) * math.sin(lon_rad)
    z = r * math.sin(lat_rad)
    
    return x, y, z


def calculate_orbit_path(satellite, start_datetime, duration_minutes: int = 90, step_minutes: int = 2):
    """
    Calculate ISS orbit path for the next N minutes.
    
    Args:
        satellite: Skyfield EarthSatellite object
        start_datetime: datetime object for start time
        duration_minutes: How many minutes into the future to calculate
        step_minutes: Time step between points (in minutes)
        
    Returns:
        list: List of (x, y, z) tuples representing orbit path
    """
    from skyfield.api import load
    
    ts = load.timescale()
    path_points = []
    
    # Calculate points along the orbit
    for minutes in range(0, duration_minutes + 1, step_minutes):
        # Calculate time for this point
        future_time = start_datetime + timedelta(minutes=minutes)
        skyfield_time = ts.from_datetime(future_time)
        
        # Calculate position at this time
        geocentric = satellite.at(skyfield_time)
        subpoint = geocentric.subpoint()
        
        # Convert to x, y, z
        lat = subpoint.latitude.degrees
        lon = subpoint.longitude.degrees
        alt = subpoint.elevation.km
        
        x, y, z = lat_lon_alt_to_xyz(lat, lon, alt)
        path_points.append((x, y, z))
    
    return path_points


def create_earth_sphere(earth_radius: float = 6371.0, resolution: int = 50):
    """
    Create a 3D sphere representing Earth.
    
    Args:
        earth_radius: Earth radius in kilometers
        resolution: Number of points for sphere resolution
        
    Returns:
        tuple: (x, y, z) arrays for sphere surface
    """
    # Create sphere using spherical coordinates
    theta = np.linspace(0, 2 * np.pi, resolution)  # Longitude
    phi = np.linspace(0, np.pi, resolution)       # Latitude
    
    theta, phi = np.meshgrid(theta, phi)
    
    # Convert to Cartesian coordinates
    x = earth_radius * np.sin(phi) * np.cos(theta)
    y = earth_radius * np.sin(phi) * np.sin(theta)
    z = earth_radius * np.cos(phi)
    
    return x, y, z


def create_3d_tracked_satellites_plot(
    iss_position: dict, 
    iss_satellite, 
    tracked_satellites: list,
    satellites_tle_data: dict,
    current_time: datetime,
    show_stations: bool = True,
    show_satellites: bool = True,
    show_debris: bool = True,
    proximity_radius_km: float = 1000.0,
    focus_mode: bool = False
):
    """
    Create a 3D Plotly plot showing Earth, ISS, and tracked satellites with color coding.
    
    This function creates a 3D visualization showing:
    - Earth as a semi-transparent gray sphere
    - ISS in red with its orbit path
    - Tracked satellites color-coded by type:
      * Stations (red) - like ISS
      * Satellites (blue) - operational satellites
      * Debris (orange) - space debris
    - Only shows objects within proximity_radius_km of ISS (or all tracked satellites in focus mode)
    
    Args:
        iss_position: Dictionary with ISS latitude, longitude, altitude
        iss_satellite: Skyfield EarthSatellite object for ISS
        tracked_satellites: List of satellite config dicts with 'name', 'catnr', 'type'
        satellites_tle_data: Dict mapping catalog numbers to TLE data
        current_time: Current datetime object
        show_stations: If True, show space stations
        show_satellites: If True, show satellites
        show_debris: If True, show debris
        proximity_radius_km: Radius in km around ISS to show other objects
        focus_mode: If True, show tracked satellites prominently with nearby objects as secondary
        
    Returns:
        tuple: (plotly.graph_objects.Figure, int, int, int) - (figure, shown_count, total_count, nearby_count)
    """
    earth_radius = 6371.0  # km
    
    # Convert ISS position to x, y, z
    iss_x, iss_y, iss_z = lat_lon_alt_to_xyz(
        iss_position['latitude'],
        iss_position['longitude'],
        iss_position['altitude'],
        earth_radius
    )
    iss_pos_3d = (iss_x, iss_y, iss_z)
    
    # Calculate ISS orbit path for next 90 minutes
    orbit_path = calculate_orbit_path(iss_satellite, current_time, duration_minutes=90, step_minutes=2)
    
    # Create Earth sphere
    earth_x, earth_y, earth_z = create_earth_sphere(earth_radius)
    
    # Calculate positions for all tracked satellites
    all_sat_positions = calculate_tracked_satellite_positions(
        tracked_satellites, 
        satellites_tle_data, 
        current_time
    )
    
    # Get tracked satellite catalog numbers for focus mode
    tracked_catnrs = {sat['catnr'] for sat in tracked_satellites}
    
    # In focus mode, calculate positions of all tracked satellites for proximity checks
    tracked_sat_positions_3d = {}
    if focus_mode:
        # Calculate 3D positions for all tracked satellites
        for x, y, z, name, alt, sat_type, catnr, lat, lon in all_sat_positions:
            if not (math.isnan(x) or math.isnan(y) or math.isnan(z)):
                tracked_sat_positions_3d[catnr] = (x, y, z)
    
    # Filter satellites by type and proximity
    # Primary: tracked satellites (in focus mode) or all (in normal mode)
    primary_stations_data = {'x': [], 'y': [], 'z': [], 'names': [], 'catnrs': []}
    primary_satellites_data = {'x': [], 'y': [], 'z': [], 'names': [], 'catnrs': []}
    primary_debris_data = {'x': [], 'y': [], 'z': [], 'names': [], 'catnrs': []}
    
    # Secondary: nearby objects (only in focus mode)
    secondary_data = {'x': [], 'y': [], 'z': [], 'names': []}
    
    # Total count should be based on configured satellites, not just successfully calculated ones
    total_count = len(tracked_satellites)
    shown_count = 0
    nearby_count = 0
    
    for x, y, z, name, alt, sat_type, catnr, lat, lon in all_sat_positions:
        if math.isnan(x) or math.isnan(y) or math.isnan(z):
            continue
        
        is_tracked = catnr in tracked_catnrs
        
        if focus_mode:
            # Focus mode: Show tracked satellites as primary, nearby objects as secondary
            if is_tracked:
                # This is a tracked satellite - show as primary
                shown_count += 1
                hover_text = f"{name}<br>Alt: {alt:.0f} km<br>Type: {sat_type}"
                
                if sat_type == 'station' and show_stations:
                    primary_stations_data['x'].append(x)
                    primary_stations_data['y'].append(y)
                    primary_stations_data['z'].append(z)
                    primary_stations_data['names'].append(hover_text)
                    primary_stations_data['catnrs'].append(catnr)
                elif sat_type == 'satellite' and show_satellites:
                    primary_satellites_data['x'].append(x)
                    primary_satellites_data['y'].append(y)
                    primary_satellites_data['z'].append(z)
                    primary_satellites_data['names'].append(hover_text)
                    primary_satellites_data['catnrs'].append(catnr)
                elif sat_type == 'debris' and show_debris:
                    primary_debris_data['x'].append(x)
                    primary_debris_data['y'].append(y)
                    primary_debris_data['z'].append(z)
                    primary_debris_data['names'].append(hover_text)
                    primary_debris_data['catnrs'].append(catnr)
            # Skip tracked satellites in this loop (they're handled above)
            # This loop only processes tracked satellites from all_sat_positions
        else:
            # Normal mode: Show all objects within proximity of ISS
            distance = calculate_distance_3d(iss_pos_3d, (x, y, z))
            
            if distance <= proximity_radius_km:
                shown_count += 1
                
                # Skip ISS itself (we'll show it separately)
                if catnr == 25544:
                    continue
                
                hover_text = f"{name}<br>Alt: {alt:.0f} km<br>Distance from ISS: {distance:.0f} km"
                
                if sat_type == 'station' and show_stations:
                    primary_stations_data['x'].append(x)
                    primary_stations_data['y'].append(y)
                    primary_stations_data['z'].append(z)
                    primary_stations_data['names'].append(hover_text)
                    primary_stations_data['catnrs'].append(catnr)
                elif sat_type == 'satellite' and show_satellites:
                    primary_satellites_data['x'].append(x)
                    primary_satellites_data['y'].append(y)
                    primary_satellites_data['z'].append(z)
                    primary_satellites_data['names'].append(hover_text)
                    primary_satellites_data['catnrs'].append(catnr)
                elif sat_type == 'debris' and show_debris:
                    primary_debris_data['x'].append(x)
                    primary_debris_data['y'].append(y)
                    primary_debris_data['z'].append(z)
                    primary_debris_data['names'].append(hover_text)
                    primary_debris_data['catnrs'].append(catnr)
    
    # In focus mode, fetch and process nearby objects from CelesTrak
    if focus_mode and tracked_sat_positions_3d:
        try:
            # Fetch additional satellites from CelesTrak for nearby objects
            nearby_satellites_data = download_multiple_satellites(group='active', limit=300)
            nearby_objects_positions = calculate_satellite_positions(nearby_satellites_data, current_time)
            
            # Filter to only show objects near tracked satellites
            for x, y, z, name, alt, catnr in nearby_objects_positions:
                if catnr in tracked_catnrs:
                    continue  # Skip tracked satellites
                
                if math.isnan(x) or math.isnan(y) or math.isnan(z):
                    continue
                
                # Check distance to nearest tracked satellite
                min_distance = float('inf')
                for tracked_pos in tracked_sat_positions_3d.values():
                    distance = calculate_distance_3d(tracked_pos, (x, y, z))
                    min_distance = min(min_distance, distance)
                
                if min_distance <= proximity_radius_km:
                    # Nearby object - show as secondary
                    nearby_count += 1
                    hover_text = f"{name}<br>Alt: {alt:.0f} km<br>Distance: {min_distance:.0f} km"
                    secondary_data['x'].append(x)
                    secondary_data['y'].append(y)
                    secondary_data['z'].append(z)
                    secondary_data['names'].append(hover_text)
        except Exception:
            # If fetching nearby objects fails, continue without them
            pass
    
    # Create the 3D plot
    fig = go.Figure()
    
    # Add Earth sphere (semi-transparent gray)
    fig.add_trace(go.Surface(
        x=earth_x,
        y=earth_y,
        z=earth_z,
        colorscale='Greys',
        showscale=False,
        opacity=0.3,
        name='Earth'
    ))
    
    # Add ISS orbit path
    if orbit_path:
        path_x = [p[0] for p in orbit_path]
        path_y = [p[1] for p in orbit_path]
        path_z = [p[2] for p in orbit_path]
        
        fig.add_trace(go.Scatter3d(
            x=path_x,
            y=path_y,
            z=path_z,
            mode='lines',
            line=dict(color='red', width=3),
            name='ISS Orbit Path (90 min)',
            hovertemplate='Orbit Path<extra></extra>'
        ))
    
    # Determine marker sizes based on focus mode
    if focus_mode:
        # Focus mode: Larger, brighter markers for tracked satellites
        primary_marker_size = 12
        primary_line_width = 2
        secondary_marker_size = 4
        secondary_opacity = 0.5
    else:
        # Normal mode: Standard sizes
        primary_marker_size = 8
        primary_line_width = 1
        secondary_marker_size = 4
        secondary_opacity = 0.5
    
    # Add primary stations (red) - tracked satellites in focus mode, or all in normal mode
    if primary_stations_data['x']:
        fig.add_trace(go.Scatter3d(
            x=primary_stations_data['x'],
            y=primary_stations_data['y'],
            z=primary_stations_data['z'],
            mode='markers+text' if focus_mode else 'markers',
            marker=dict(
                size=primary_marker_size,
                color='red',
                symbol='circle',
                line=dict(width=primary_line_width, color='darkred'),
                opacity=1.0
            ),
            text=[name.split('<br>')[0] for name in primary_stations_data['names']] if focus_mode else None,
            textposition='top center' if focus_mode else None,
            name='My Stations' if focus_mode else 'Stations',
            hovertemplate='%{customdata[0]}<extra></extra>',
            customdata=[[name] for name in primary_stations_data['names']]
        ))
    
    # Add primary satellites (blue)
    if primary_satellites_data['x']:
        fig.add_trace(go.Scatter3d(
            x=primary_satellites_data['x'],
            y=primary_satellites_data['y'],
            z=primary_satellites_data['z'],
            mode='markers+text' if focus_mode else 'markers',
            marker=dict(
                size=primary_marker_size if focus_mode else 6,
                color='blue',
                symbol='circle',
                line=dict(width=primary_line_width, color='darkblue'),
                opacity=1.0
            ),
            text=[name.split('<br>')[0] for name in primary_satellites_data['names']] if focus_mode else None,
            textposition='top center' if focus_mode else None,
            name='My Satellites' if focus_mode else 'Satellites',
            hovertemplate='%{customdata[0]}<extra></extra>',
            customdata=[[name] for name in primary_satellites_data['names']]
        ))
    
    # Add primary debris (orange)
    if primary_debris_data['x']:
        fig.add_trace(go.Scatter3d(
            x=primary_debris_data['x'],
            y=primary_debris_data['y'],
            z=primary_debris_data['z'],
            mode='markers+text' if focus_mode else 'markers',
            marker=dict(
                size=primary_marker_size if focus_mode else 5,
                color='orange',
                symbol='circle',
                line=dict(width=primary_line_width, color='darkorange'),
                opacity=1.0
            ),
            text=[name.split('<br>')[0] for name in primary_debris_data['names']] if focus_mode else None,
            textposition='top center' if focus_mode else None,
            name='My Debris' if focus_mode else 'Debris',
            hovertemplate='%{customdata[0]}<extra></extra>',
            customdata=[[name] for name in primary_debris_data['names']]
        ))
    
    # Add secondary objects (nearby objects in focus mode)
    if focus_mode and secondary_data['x']:
        fig.add_trace(go.Scatter3d(
            x=secondary_data['x'],
            y=secondary_data['y'],
            z=secondary_data['z'],
            mode='markers',
            marker=dict(
                size=secondary_marker_size,
                color='gray',
                symbol='circle',
                line=dict(width=0.5, color='darkgray'),
                opacity=secondary_opacity
            ),
            name='Nearby Objects',
            hovertemplate='%{customdata[0]}<extra></extra>',
            customdata=[[name] for name in secondary_data['names']]
        ))
    
    # Add ISS current position (red, larger and more prominent)
    # In focus mode, show with label; in normal mode, just marker
    iss_marker_size = 14 if focus_mode else 12
    fig.add_trace(go.Scatter3d(
        x=[iss_x],
        y=[iss_y],
        z=[iss_z],
        mode='markers+text' if focus_mode else 'markers',
        marker=dict(
            size=iss_marker_size,
            color='red',
            symbol='circle',
            line=dict(width=3 if focus_mode else 2, color='darkred')
        ),
        text=['ISS'] if focus_mode else None,
        textposition='top center' if focus_mode else None,
        name='ISS Current Position',
        hovertemplate=f'ISS<br>Lat: {iss_position["latitude"]:.2f}°<br>Lon: {iss_position["longitude"]:.2f}°<br>Alt: {iss_position["altitude"]:.2f} km<extra></extra>'
    ))
    
    # Set camera angle and layout
    axis_range = max(15000, proximity_radius_km * 2)  # Dynamic range based on proximity
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (km)', range=[-axis_range, axis_range], backgroundcolor='#0e1117', gridcolor='#333'),
            yaxis=dict(title='Y (km)', range=[-axis_range, axis_range], backgroundcolor='#0e1117', gridcolor='#333'),
            zaxis=dict(title='Z (km)', range=[-axis_range, axis_range], backgroundcolor='#0e1117', gridcolor='#333'),
            aspectmode='cube',
            camera=dict(
                eye=dict(x=2.0, y=2.0, z=1.5),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            ),
            bgcolor='#0e1117'
        ),
        title=dict(
            text='Multi-Satellite 3D View',
            font=dict(color='white', size=20)
        ),
        height=700,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font=dict(color='white')
    )
    
    return fig, shown_count, total_count, nearby_count


def create_3d_orbit_plot(position: dict, satellite, current_time, show_orbital_shell: bool = True, satellite_group: str = 'active', max_satellites: int = 500):
    """
    Create a 3D Plotly plot showing Earth, ISS position, orbit path, and orbital shell.
    
    Args:
        position: Dictionary with latitude, longitude, altitude
        satellite: Skyfield EarthSatellite object
        current_time: Current datetime object
        show_orbital_shell: If True, show multiple satellites as orbital shell
        satellite_group: CelesTrak group to download ('active', 'stations', 'starlink', etc.)
        max_satellites: Maximum number of satellites to display
        
    Returns:
        plotly.graph_objects.Figure: 3D plot figure
    """
    earth_radius = 6371.0  # km
    
    # Convert current ISS position to x, y, z
    iss_x, iss_y, iss_z = lat_lon_alt_to_xyz(
        position['latitude'],
        position['longitude'],
        position['altitude'],
        earth_radius
    )
    
    # Calculate orbit path for next 90 minutes
    from skyfield.api import load
    ts = load.timescale()
    skyfield_time = ts.from_datetime(current_time)
    
    orbit_path = calculate_orbit_path(satellite, current_time, duration_minutes=90, step_minutes=2)
    
    # Create Earth sphere
    earth_x, earth_y, earth_z = create_earth_sphere(earth_radius)
    
    # Create the 3D plot
    fig = go.Figure()
    
    # Add Earth sphere (semi-transparent gray)
    fig.add_trace(go.Surface(
        x=earth_x,
        y=earth_y,
        z=earth_z,
        colorscale='Greys',
        showscale=False,
        opacity=0.3,
        name='Earth'
    ))
    
    # Add orbital shell (multiple satellites) if enabled
    if show_orbital_shell:
        with st.spinner("Loading orbital shell data..."):
            # Download multiple satellites
            satellites_data = download_multiple_satellites(group=satellite_group, limit=max_satellites)
            
            if satellites_data:
                # Calculate positions for all satellites
                satellite_positions = calculate_satellite_positions(satellites_data, current_time)
                
                if satellite_positions:
                    # Separate ISS from other satellites
                    other_sats_x = []
                    other_sats_y = []
                    other_sats_z = []
                    other_sats_names = []
                    
                    for x, y, z, name, alt, norad_id in satellite_positions:
                        # Skip ISS (we'll show it separately in red)
                        if norad_id == '25544' or 'ISS' in name.upper():
                            continue
                        other_sats_x.append(x)
                        other_sats_y.append(y)
                        other_sats_z.append(z)
                        other_sats_names.append(f"{name} (Alt: {alt:.0f} km)")
                    
                    # Add all other satellites as white dots (orbital shell)
                    if other_sats_x:
                        fig.add_trace(go.Scatter3d(
                            x=other_sats_x,
                            y=other_sats_y,
                            z=other_sats_z,
                            mode='markers',
                            marker=dict(
                                size=3,
                                color='white',
                                symbol='circle',
                                opacity=0.8,
                                line=dict(width=0)
                            ),
                            name=f'Orbital Shell ({len(other_sats_x)} satellites)',
                            hovertemplate='%{text}<extra></extra>',
                            text=other_sats_names
                        ))
    
    # Add orbit path
    if orbit_path:
        path_x = [p[0] for p in orbit_path]
        path_y = [p[1] for p in orbit_path]
        path_z = [p[2] for p in orbit_path]
        
        fig.add_trace(go.Scatter3d(
            x=path_x,
            y=path_y,
            z=path_z,
            mode='lines',
            line=dict(color='red', width=3),
            name='ISS Orbit Path (90 min)',
            hovertemplate='Orbit Path<extra></extra>'
        ))
    
    # Add current ISS position (red dot, larger and more prominent)
    fig.add_trace(go.Scatter3d(
        x=[iss_x],
        y=[iss_y],
        z=[iss_z],
        mode='markers',
        marker=dict(
            size=12,
            color='red',
            symbol='circle',
            line=dict(width=2, color='darkred')
        ),
        name='ISS Current Position',
        hovertemplate=f'ISS<br>Lat: {position["latitude"]:.2f}°<br>Lon: {position["longitude"]:.2f}°<br>Alt: {position["altitude"]:.2f} km<extra></extra>'
    ))
    
    # Set camera angle to show Earth and orbit clearly
    # Adjust range based on whether orbital shell is shown
    if show_orbital_shell:
        # Wider range to show orbital shell (LEO extends to ~8,371 km from center)
        axis_range = 15000
        title_text = 'ISS 3D Orbit View - Orbital Shell'
    else:
        # Closer range for ISS-only view
        axis_range = 8000
        title_text = 'ISS 3D Orbit View'
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (km)', range=[-axis_range, axis_range], backgroundcolor='#0e1117', gridcolor='#333'),
            yaxis=dict(title='Y (km)', range=[-axis_range, axis_range], backgroundcolor='#0e1117', gridcolor='#333'),
            zaxis=dict(title='Z (km)', range=[-axis_range, axis_range], backgroundcolor='#0e1117', gridcolor='#333'),
            aspectmode='cube',
            camera=dict(
                eye=dict(x=2.0, y=2.0, z=1.5),  # Position camera to see Earth and orbit
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            ),
            bgcolor='#0e1117'
        ),
        title=dict(
            text=title_text,
            font=dict(color='white', size=20)
        ),
        height=700,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font=dict(color='white')
    )
    
    return fig


# Page configuration
st.set_page_config(
    page_title="SatWatch - ISS Tracker",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stSidebar {
        background-color: #1e1e1e;
    }
    h1 {
        color: #ffffff;
    }
    h2, h3 {
        color: #e0e0e0;
    }
    .stMetric {
        background-color: #262730;
    }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title("🛰️ SatWatch - ISS Tracker")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📊 ISS Status")
    
    # Data source selection
    use_local = st.radio(
        "Data Source",
        ["Local File", "CelesTrak API"],
        index=0,
        help="Choose to use local JSON file or download fresh data from CelesTrak"
    )
    
    # Get ISS data
    position, json_data, error = get_iss_data(use_local=(use_local == "Local File"))
    
    if error:
        st.error(f"❌ Error: {error}")
        st.stop()
    
    if position and json_data:
        # Load tracked satellites configuration
        try:
            satellites_config = load_satellites_config()
            tracked_satellites = satellites_config.get('tracked_satellites', [])
        except FileNotFoundError:
            st.warning("⚠️ satellites.json not found. Using ISS only.")
            tracked_satellites = []
        except Exception as e:
            st.warning(f"⚠️ Error loading satellites config: {e}")
            tracked_satellites = []
        
        # Fetch TLE data for tracked satellites
        satellites_tle_data = {}
        loaded_satellites = []  # Track which satellites loaded successfully
        if tracked_satellites:
            with st.spinner("Loading tracked satellites..."):
                catnr_list = [sat['catnr'] for sat in tracked_satellites]
                fetched_satellites = fetch_satellites(catnr_list)
                
                # Create a mapping of catalog number to TLE data
                for sat_data in fetched_satellites:
                    # Try to get NORAD catalog ID - it can be in different fields
                    # NORAD_CAT_ID is the preferred field (numeric string)
                    # OBJECT_ID might be international designator (e.g., '1998-067A')
                    catnr = None
                    
                    # First try NORAD_CAT_ID (preferred field)
                    if 'NORAD_CAT_ID' in sat_data:
                        try:
                            catnr = int(sat_data['NORAD_CAT_ID'])
                        except (ValueError, TypeError):
                            pass
                    
                    # If that didn't work, try OBJECT_ID (but it might be a designator)
                    if catnr is None and 'OBJECT_ID' in sat_data:
                        obj_id = sat_data['OBJECT_ID']
                        # Try to convert to int - if it fails, it's probably a designator
                        try:
                            catnr = int(obj_id)
                        except (ValueError, TypeError):
                            # OBJECT_ID is not numeric (likely international designator)
                            # Try to find the catalog number from the TLE line instead
                            tle_line1 = sat_data.get('TLE_LINE1', '')
                            if tle_line1 and len(tle_line1) >= 7:
                                # TLE line 1 has catalog number at positions 2-7 (1-indexed, so 1-6 in 0-indexed)
                                try:
                                    catnr = int(tle_line1[2:7].strip())
                                except (ValueError, IndexError):
                                    pass
                    
                    # If we still don't have a catalog number, skip this satellite
                    if catnr is None:
                        sat_name = sat_data.get('OBJECT_NAME', 'Unknown')
                        st.warning(f"Could not determine catalog number for {sat_name}, skipping")
                        continue
                    
                    satellites_tle_data[catnr] = sat_data
                    loaded_satellites.append(catnr)
                
                # Also add ISS data if it's in tracked satellites but not already loaded
                iss_catnr = 25544
                if iss_catnr in [sat['catnr'] for sat in tracked_satellites] and iss_catnr not in satellites_tle_data:
                    # Add ISS data from the main data source (already loaded)
                    satellites_tle_data[iss_catnr] = json_data
                    if iss_catnr not in loaded_satellites:
                        loaded_satellites.append(iss_catnr)
                
                # Show summary of loaded satellites
                if loaded_satellites:
                    st.success(f"✓ Loaded {len(loaded_satellites)} of {len(tracked_satellites)} satellites")
                    # Show which ones loaded
                    loaded_names = []
                    failed_names = []
                    for sat in tracked_satellites:
                        if sat['catnr'] in loaded_satellites:
                            loaded_names.append(sat['name'])
                        else:
                            failed_names.append(f"{sat['name']} ({sat['catnr']})")
                    if loaded_names:
                        st.caption(f"✓ Loaded: {', '.join(loaded_names)}")
                    if failed_names:
                        st.caption(f"⚠️ Failed: {', '.join(failed_names)}")
                else:
                    st.warning(f"⚠️ No satellites loaded. Check catalog numbers in satellites.json")
            
            # Store in session state for use in main content area
            st.session_state.tracked_satellites = tracked_satellites
            st.session_state.satellites_tle_data = satellites_tle_data
        else:
            # Clear session state if no tracked satellites
            st.session_state.tracked_satellites = []
            st.session_state.satellites_tle_data = {}
        # Current time
        current_time = datetime.now(timezone.utc)
        st.metric("Current Time (UTC)", current_time.strftime("%H:%M:%S"))
        st.caption(f"Date: {current_time.strftime('%Y-%m-%d')}")
        
        st.markdown("---")
        
        # ISS Position
        st.subheader("📍 Position")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Latitude", f"{position['latitude']:.4f}°")
        with col2:
            st.metric("Longitude", f"{position['longitude']:.4f}°")
        
        st.metric("Altitude", f"{position['altitude']:.2f} km")
        
        st.markdown("---")
        
        # TLE Data Info
        st.subheader("📡 TLE Data")
        epoch = json_data.get('EPOCH', 'Unknown')
        st.text(f"Epoch: {epoch}")
        
        # Data freshness with graduated warnings
        status_level, hours_old, status_message = get_data_freshness_status(epoch)
        
        if status_level == 'fresh':
            st.success(f"✅ {status_message}")
        elif status_level == 'warning':
            st.warning(f"⚠️ {status_message}")
        elif status_level == 'old':
            st.warning(f"⚠️ {status_message}")
        else:  # expired
            st.error(f"❌ {status_message}")
        
        st.caption("TLE data is typically valid for ~2 weeks")
        
        st.markdown("---")
        
        # Satellite Info
        st.subheader("🛰️ Satellite Info")
        st.text(f"Name: {json_data.get('OBJECT_NAME', 'Unknown')}")
        st.text(f"NORAD ID: {json_data.get('NORAD_CAT_ID', 'Unknown')}")
        
        st.markdown("---")
        
        # Multi-Satellite Tracking Filters
        if tracked_satellites:
            st.subheader("🔍 Multi-Satellite Filters")
            
            # Type filters (checkboxes)
            show_stations = st.checkbox(
                "Show Stations",
                value=st.session_state.get('show_stations', True),
                help="Display space stations (red)",
                key='show_stations_checkbox'
            )
            st.session_state.show_stations = show_stations
            
            show_satellites = st.checkbox(
                "Show Satellites",
                value=st.session_state.get('show_satellites', True),
                help="Display operational satellites (blue)",
                key='show_satellites_checkbox'
            )
            st.session_state.show_satellites = show_satellites
            
            show_debris = st.checkbox(
                "Show Debris",
                value=st.session_state.get('show_debris', True),
                help="Display space debris (orange)",
                key='show_debris_checkbox'
            )
            st.session_state.show_debris = show_debris
            
            st.markdown("---")
            
            # Proximity radius slider
            proximity_radius = st.slider(
                "Proximity Radius (km)",
                min_value=100,
                max_value=5000,
                value=st.session_state.get('proximity_radius', 1000),
                step=100,
                help="Show objects within this distance from ISS",
                key='proximity_radius_slider'
            )
            st.session_state.proximity_radius = proximity_radius
            
            st.caption(f"Tracking {len(tracked_satellites)} satellites")
            
            st.markdown("---")
            
            # Focus Mode toggle
            focus_mode = st.checkbox(
                "Focus on my satellites",
                value=st.session_state.get('focus_mode', False),
                help="When ON: Show your tracked satellites prominently with nearby objects as secondary. When OFF: Show all objects equally.",
                key='focus_mode_checkbox'
            )
            st.session_state.focus_mode = focus_mode
        else:
            # Default values if no tracked satellites
            show_stations = True
            show_satellites = True
            show_debris = True
            proximity_radius = 1000
            focus_mode = False
            st.session_state.show_stations = show_stations
            st.session_state.show_satellites = show_satellites
            st.session_state.show_debris = show_debris
            st.session_state.proximity_radius = proximity_radius
            st.session_state.focus_mode = focus_mode
        
        st.markdown("---")
        
        # 3D View Options (for orbital shell)
        st.subheader("🌐 Orbital Shell Options")
        show_orbital_shell = st.checkbox(
            "Show Orbital Shell",
            value=st.session_state.get('show_orbital_shell', False),
            help="Display multiple satellites as a 'space highway' around Earth",
            key='show_orbital_shell_checkbox'
        )
        st.session_state.show_orbital_shell = show_orbital_shell
        
        if show_orbital_shell:
            satellite_group = st.selectbox(
                "Satellite Group",
                ['active', 'stations', 'starlink', 'weather', 'noaa', 'goes', 'last-30-days'],
                index=0,
                help="Choose which group of satellites to display",
                key='satellite_group_select'
            )
            st.session_state.satellite_group = satellite_group
            
            max_satellites = st.slider(
                "Max Satellites",
                min_value=50,
                max_value=1000,
                value=st.session_state.get('max_satellites', 500),
                step=50,
                help="Maximum number of satellites to display (more = slower loading)",
                key='max_satellites_slider'
            )
            st.session_state.max_satellites = max_satellites
        else:
            satellite_group = 'active'
            max_satellites = 500
            st.session_state.satellite_group = satellite_group
            st.session_state.max_satellites = max_satellites

# Main content area
if position and json_data:
    # Get tracked satellites data from session state (set in sidebar)
    tracked_satellites = st.session_state.get('tracked_satellites', [])
    satellites_tle_data = st.session_state.get('satellites_tle_data', {})
    show_stations = st.session_state.get('show_stations', True)
    show_satellites = st.session_state.get('show_satellites', True)
    show_debris = st.session_state.get('show_debris', True)
    proximity_radius = st.session_state.get('proximity_radius', 1000)
    focus_mode = st.session_state.get('focus_mode', False)
    
    # Create tabs for 2D map and 3D orbit view
    tab1, tab2 = st.tabs(["🗺️ 2D Map View", "🌐 3D Orbit View"])
    
    with tab1:
        st.subheader("🌍 Tracked Satellites (2D Map)")
        
        # Validate position values before creating map
        if (math.isnan(position['latitude']) or 
            math.isnan(position['longitude']) or 
            math.isnan(position['altitude'])):
            st.error(
                "❌ **Position Calculation Failed**\n\n"
                "The ISS position could not be calculated. This may be due to:\n"
                "- Invalid or corrupted TLE data\n"
                "- TLE data that is too old or expired\n"
                "- Error in position calculation\n\n"
                "**Try:**\n"
                "1. Switch to 'CelesTrak API' data source in the sidebar\n"
                "2. Refresh the page\n"
                "3. Check that TLE data is valid"
            )
        else:
            # Calculate positions for all tracked satellites
            all_sat_positions = []
            nearby_sat_positions = []
            
            if tracked_satellites and satellites_tle_data:
                try:
                    all_sat_positions = calculate_tracked_satellite_positions(
                        tracked_satellites,
                        satellites_tle_data,
                        current_time
                    )
                    
                    # In focus mode, also fetch nearby objects
                    if focus_mode:
                        # Fetch additional satellites from CelesTrak for nearby objects
                        try:
                            nearby_satellites_data = download_multiple_satellites(
                                group='active', 
                                limit=200  # Reasonable limit for nearby objects
                            )
                            
                            # Calculate positions for nearby satellites
                            nearby_positions = calculate_satellite_positions(
                                nearby_satellites_data, 
                                current_time
                            )
                            
                            # Filter to only show objects near tracked satellites
                            tracked_catnrs = {sat['catnr'] for sat in tracked_satellites}
                            tracked_positions_3d = {}
                            for sat_data in all_sat_positions:
                                # Unpack: (x, y, z, name, alt, sat_type, catnr, lat, lon)
                                x, y, z, name, alt, sat_type, catnr, lat, lon = sat_data
                                if not (math.isnan(x) or math.isnan(y) or math.isnan(z)):
                                    tracked_positions_3d[catnr] = (x, y, z)
                            
                            for x, y, z, name, alt, catnr in nearby_positions:
                                if catnr in tracked_catnrs:
                                    continue  # Skip tracked satellites
                                
                                # Check distance to nearest tracked satellite
                                min_distance = float('inf')
                                for tracked_pos in tracked_positions_3d.values():
                                    distance = calculate_distance_3d(tracked_pos, (x, y, z))
                                    min_distance = min(min_distance, distance)
                                
                                if min_distance <= proximity_radius:
                                    nearby_sat_positions.append((x, y, z, name, alt, catnr))
                        except Exception as e:
                            st.warning(f"Could not fetch nearby objects: {e}")
                            
                except Exception as e:
                    st.warning(f"Could not calculate all satellite positions: {e}")
            
            # Create and display map
            try:
                # Convert all_sat_positions to format expected by create_map: (lat, lon, alt, name, sat_type, catnr)
                map_satellites = None
                if all_sat_positions:
                    map_satellites = []
                    for sat_pos in all_sat_positions:
                        # Unpack: (x, y, z, name, alt, sat_type, catnr, lat, lon)
                        x, y, z, name, alt, sat_type, catnr, lat, lon = sat_pos
                        if not (math.isnan(lat) or math.isnan(lon) or math.isnan(alt)):
                            map_satellites.append((lat, lon, alt, name, sat_type, catnr))
                
                # Create map - in focus mode, show tracked satellites prominently
                # Nearby objects are shown in 3D view, not on 2D map for simplicity
                map_obj = create_map(
                    position['latitude'],
                    position['longitude'],
                    position['altitude'],
                    all_satellites=map_satellites
                )
                
                # Use a fixed key so the map doesn't get recreated on every rerun
                # The map will update its position internally without full recreation
                map_data = st_folium(
                    map_obj, 
                    width=1200, 
                    height=600, 
                    key="iss_tracker_map",  # Fixed key prevents recreation
                    returned_objects=[]
                )
                
                # Additional info below map
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"**Last Update:** {position['timestamp']}")
                with col2:
                    if tracked_satellites:
                        if focus_mode:
                            st.info(f"**Tracking {len(tracked_satellites)} satellites, {len(nearby_sat_positions)} nearby objects**")
                        else:
                            st.info(f"**Tracked Satellites:** {len(tracked_satellites)}")
                    else:
                        st.info(f"**Speed:** ~7.66 km/s (orbital velocity)")
                with col3:
                    st.info(f"**Orbit Period:** ~92 minutes")
                
                # Show satellite list if we have tracked satellites
                if tracked_satellites and all_sat_positions:
                    st.markdown("---")
                    st.subheader("📋 Tracked Satellites")
                    
                    # Create a table showing all tracked satellites
                    sat_data = []
                    for sat_pos in all_sat_positions:
                        # Unpack: (x, y, z, name, alt, sat_type, catnr, lat, lon)
                        x, y, z, sat_name, sat_alt, sat_type, catnr, sat_lat, sat_lon = sat_pos
                        if not (math.isnan(sat_lat) or math.isnan(sat_lon) or math.isnan(sat_alt)):
                            sat_data.append({
                                'Name': sat_name,
                                'Type': sat_type.title(),
                                'Latitude': f"{sat_lat:.4f}°",
                                'Longitude': f"{sat_lon:.4f}°",
                                'Altitude': f"{sat_alt:.2f} km",
                                'CATNR': catnr
                            })
                    
                    if sat_data:
                        try:
                            import pandas as pd
                            df = pd.DataFrame(sat_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        except ImportError:
                            # Fallback if pandas not available - show as markdown table
                            st.markdown("| Name | Type | Latitude | Longitude | Altitude | CATNR |")
                            st.markdown("|------|------|----------|-----------|----------|-------|")
                            for sat in sat_data:
                                st.markdown(f"| {sat['Name']} | {sat['Type']} | {sat['Latitude']} | {sat['Longitude']} | {sat['Altitude']} | {sat['CATNR']} |")
            except ValueError as e:
                st.error(f"❌ **Map Creation Failed**: {str(e)}")
            except Exception as e:
                st.error(f"❌ **Unexpected Error**: {str(e)}")
                st.info("Try refreshing the page or switching to CelesTrak API data source.")
    
    with tab2:
        st.subheader("🌐 Multi-Satellite 3D Orbit View")
        
        # Validate position values before creating 3D plot
        if (math.isnan(position['latitude']) or 
            math.isnan(position['longitude']) or 
            math.isnan(position['altitude'])):
            st.error(
                "❌ **Position Calculation Failed**\n\n"
                "The ISS position could not be calculated. This may be due to:\n"
                "- Invalid or corrupted TLE data\n"
                "- TLE data that is too old or expired\n"
                "- Error in position calculation\n\n"
                "**Try:**\n"
                "1. Switch to 'CelesTrak API' data source in the sidebar\n"
                "2. Refresh the page\n"
                "3. Check that TLE data is valid"
            )
        else:
            # Get satellite object for orbit calculation
            try:
                satellite = parse_tle_from_json(json_data)
                current_time = datetime.now(timezone.utc)
                
                # Check if we have tracked satellites to show
                if tracked_satellites and satellites_tle_data:
                    # Use the new multi-satellite visualization
                    focus_mode = st.session_state.get('focus_mode', False)
                    
                    fig_3d, shown_count, total_count, nearby_count = create_3d_tracked_satellites_plot(
                        position,
                        satellite,
                        tracked_satellites,
                        satellites_tle_data,
                        current_time,
                        show_stations=show_stations,
                        show_satellites=show_satellites,
                        show_debris=show_debris,
                        proximity_radius_km=proximity_radius,
                        focus_mode=focus_mode
                    )
                    
                    # Display count based on focus mode
                    if focus_mode:
                        st.info(f"**Tracking {shown_count} satellites, {nearby_count} nearby objects** (within {proximity_radius} km)")
                    else:
                        st.info(f"**Showing {shown_count} of {total_count} tracked objects** (within {proximity_radius} km of ISS)")
                    
                    # Debug information to help diagnose issues
                    if shown_count == 0 and total_count > 1:
                        with st.expander("🔍 Debug Information - Why are satellites not showing?", expanded=True):
                            # Calculate positions for debug info
                            debug_all_sat_positions = calculate_tracked_satellite_positions(
                                tracked_satellites, 
                                satellites_tle_data, 
                                current_time
                            )
                            
                            st.write(f"**Configuration:**")
                            st.write(f"- Tracked satellites in config: {len(tracked_satellites)}")
                            st.write(f"- Satellites with TLE data loaded: {len(satellites_tle_data)}")
                            st.write(f"- Positions successfully calculated: {len(debug_all_sat_positions)}")
                            st.write(f"- Proximity radius: {proximity_radius} km")
                            st.write("")
                            
                            st.write(f"**Satellite Details:**")
                            for sat_config in tracked_satellites:
                                catnr = sat_config['catnr']
                                name = sat_config['name']
                                sat_type = sat_config['type']
                                
                                has_tle = catnr in satellites_tle_data
                                type_enabled = (show_stations and sat_type == 'station') or \
                                             (show_satellites and sat_type == 'satellite') or \
                                             (show_debris and sat_type == 'debris')
                                
                                st.write(f"**{name}** (CATNR: {catnr}, Type: {sat_type})")
                                
                                if not has_tle:
                                    st.error(f"  ✗ No TLE data loaded - satellite fetch may have failed")
                                elif not type_enabled:
                                    st.warning(f"  ⚠ Type filter disabled - {sat_type} type is not shown")
                                else:
                                    # Calculate position and distance
                                    try:
                                        sat_tle = satellites_tle_data[catnr]
                                        
                                        # Check if TLE data has required fields
                                        if 'TLE_LINE1' not in sat_tle or 'TLE_LINE2' not in sat_tle:
                                            st.error(f"  ✗ Missing TLE_LINE1 or TLE_LINE2 in TLE data")
                                            st.write(f"  - Available fields: {list(sat_tle.keys())}")
                                            continue
                                        
                                        sat_obj = parse_tle_from_json(sat_tle)
                                        from skyfield.api import load
                                        ts = load.timescale()
                                        skyfield_time = ts.from_datetime(current_time)
                                        geocentric = sat_obj.at(skyfield_time)
                                        subpoint = geocentric.subpoint()
                                        
                                        lat = subpoint.latitude.degrees
                                        lon = subpoint.longitude.degrees
                                        alt = subpoint.elevation.km
                                        
                                        # Check for NaN
                                        if math.isnan(lat) or math.isnan(lon) or math.isnan(alt):
                                            st.error(f"  ✗ Position calculation returned NaN")
                                            st.write(f"  - Lat: {lat}, Lon: {lon}, Alt: {alt}")
                                            st.write(f"  - TLE_LINE1: {sat_tle.get('TLE_LINE1', 'Missing')[:50]}...")
                                            continue
                                        
                                        sat_x, sat_y, sat_z = lat_lon_alt_to_xyz(lat, lon, alt)
                                        
                                        # Check for NaN in converted coordinates
                                        if math.isnan(sat_x) or math.isnan(sat_y) or math.isnan(sat_z):
                                            st.error(f"  ✗ Coordinate conversion returned NaN")
                                            continue
                                        
                                        # Calculate distance from ISS
                                        iss_x, iss_y, iss_z = lat_lon_alt_to_xyz(
                                            position['latitude'],
                                            position['longitude'],
                                            position['altitude']
                                        )
                                        distance = calculate_distance_3d((iss_x, iss_y, iss_z), (sat_x, sat_y, sat_z))
                                        
                                        within_radius = distance <= proximity_radius
                                        
                                        st.write(f"  - Position: ({sat_x:.0f}, {sat_y:.0f}, {sat_z:.0f}) km")
                                        st.write(f"  - Altitude: {alt:.0f} km")
                                        st.write(f"  - Distance from ISS: **{distance:.0f} km**")
                                        
                                        if within_radius:
                                            st.success(f"  ✓ Within {proximity_radius} km radius - should be visible")
                                        else:
                                            st.warning(f"  ⚠ Outside {proximity_radius} km radius (need {distance - proximity_radius:.0f} km more)")
                                            
                                    except Exception as e:
                                        st.error(f"  ✗ Error calculating position: {e}")
                                        import traceback
                                        st.code(traceback.format_exc())
                                
                                st.write("")
                    
                    # Display the 3D plot
                    st.plotly_chart(fig_3d, use_container_width=True)
                    
                    # Info about 3D view
                    st.info("**3D View Features:**")
                    st.markdown("""
                    - **Earth**: Semi-transparent gray sphere (radius: 6,371 km)
                    - **ISS Position**: Red dot showing current location
                    - **Orbit Path**: Red line showing predicted path for next 90 minutes
                    - **Stations**: Red markers (space stations)
                    - **Satellites**: Blue markers (operational satellites)
                    - **Debris**: Orange markers (space debris)
                    - **Interactive**: Rotate, zoom, and pan to explore the 3D view
                    - **Proximity Filter**: Only objects within the selected radius are shown
                    """)
                else:
                    # Fall back to orbital shell view if no tracked satellites
                    show_shell = st.session_state.get('show_orbital_shell', False)
                    sat_group = st.session_state.get('satellite_group', 'active')
                    max_sats = st.session_state.get('max_satellites', 500)
                    
                    # Create 3D orbit plot with orbital shell
                    fig_3d = create_3d_orbit_plot(
                        position, 
                        satellite, 
                        current_time,
                        show_orbital_shell=show_shell,
                        satellite_group=sat_group,
                        max_satellites=max_sats
                    )
                    
                    # Display the 3D plot
                    st.plotly_chart(fig_3d, use_container_width=True)
                    
                    # Info about 3D view
                    st.info("**3D View Features:**")
                    features_text = """
                    - **Earth**: Semi-transparent gray sphere (radius: 6,371 km)
                    - **ISS Position**: Red dot showing current location
                    - **Orbit Path**: Red line showing predicted path for next 90 minutes
                    - **Interactive**: Rotate, zoom, and pan to explore the 3D view
                    """
                    if show_shell:
                        features_text += f"\n- **Orbital Shell**: White dots showing {max_sats} satellites from '{sat_group}' group"
                    st.markdown(features_text)
                    
                    if not tracked_satellites:
                        st.warning("⚠️ No tracked satellites configured. Add satellites to `satellites.json` to see multi-satellite tracking.")
            
            except Exception as e:
                st.error(f"Error creating 3D view: {e}")
                st.info("Make sure you have plotly installed: `pip install plotly`")
    
    # Auto-refresh indicator (below tabs)
    st.markdown("---")
    
    # Initialize refresh tracking
    if 'last_refresh_time' not in st.session_state:
        st.session_state.last_refresh_time = datetime.now(timezone.utc).timestamp()
    
    # Calculate time since last refresh
    current_timestamp = datetime.now(timezone.utc).timestamp()
    elapsed = current_timestamp - st.session_state.last_refresh_time
    
    # Show countdown
    remaining_seconds = max(0, 10 - int(elapsed))
    refresh_placeholder = st.empty()
    with refresh_placeholder:
        st.caption(f"🔄 Auto-refreshing in {remaining_seconds} seconds...")
    
    # Only rerun if 10 seconds have passed AND we haven't rerun recently
    if elapsed >= 10:
        st.session_state.last_refresh_time = current_timestamp
        # Use rerun with a small delay to prevent rapid loops
        import time
        time.sleep(0.5)  # Small delay to stabilize
        st.rerun()
else:
    st.error("Unable to load ISS position data. Please check your data source.")
