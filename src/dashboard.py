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
import time
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
from pathlib import Path


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
            # Add User-Agent header to avoid 403 errors
            headers = {
                'User-Agent': 'SatWatch/1.0 (Educational/Research Project)'
            }
            response = requests.get(url, params=params, timeout=10, headers=headers)
            
            # Handle 403 Forbidden errors
            if response.status_code == 403:
                # Try JSON format as fallback
                params_json = params.copy()
                params_json['FORMAT'] = 'json'
                response_json = requests.get(url, params=params_json, timeout=10, headers=headers)
                if response_json.status_code == 200:
                    # Parse JSON response
                    json_data = response_json.json()
                    if json_data and len(json_data) > 0:
                        sat_data = json_data[0]
                        # Extract TLE lines if available
                        tle_line1 = sat_data.get('TLE_LINE1', '')
                        tle_line2 = sat_data.get('TLE_LINE2', '')
                        if tle_line1 and tle_line2:
                            name_line = sat_data.get('OBJECT_NAME', 'Unknown')
                            # Create satellite data in same format as 3LE
                            satellite_data = {
                                'OBJECT_NAME': name_line,
                                'TLE_LINE1': tle_line1,
                                'TLE_LINE2': tle_line2,
                                'NORAD_CAT_ID': str(catnr),
                                'OBJECT_ID': str(catnr)
                            }
                            satellites.append(satellite_data)
                            continue
                
                # If both formats fail, show warning but don't stop
                st.warning(f"⚠️ Satellite {catnr} returned 403 Forbidden. This satellite may not be available in CelesTrak database or access may be restricted. Skipping this satellite.")
                continue
            
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
                
        except requests.HTTPError as e:
            # Handle HTTP errors (including 403)
            if e.response and e.response.status_code == 403:
                st.warning(f"⚠️  Satellite {catnr} access forbidden (403). This satellite may not be publicly available in CelesTrak or may require authentication.")
            else:
                status_code = e.response.status_code if e.response else "Unknown"
                st.warning(f"⚠️  Failed to fetch satellite {catnr}: HTTP {status_code} - {e}")
            continue
        except requests.RequestException as e:
            # Network error - log but continue with other satellites
            # Check if it's a 403 error in the message
            if "403" in str(e) or "Forbidden" in str(e):
                st.warning(f"⚠️  Satellite {catnr} access forbidden (403). This satellite may not be publicly available in CelesTrak or may require authentication.")
            else:
                st.warning(f"⚠️  Failed to fetch satellite {catnr}: Network error - {e}")
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


def calculate_position_at_time(satellite: EarthSatellite, target_time: datetime) -> dict:
    """
    Calculate satellite position at a specific time.
    
    This function calculates the satellite's position at any given time,
    enabling historical and future position viewing.
    
    Args:
        satellite: Skyfield EarthSatellite object
        target_time: datetime object (timezone-aware, UTC) for the desired time
        
    Returns:
        dict: Dictionary containing latitude, longitude, altitude, and timestamp
    """
    from skyfield.api import load
    
    # Load the timescale
    ts = load.timescale()
    
    # Convert datetime to Skyfield time
    skyfield_time = ts.from_datetime(target_time)
    
    # Calculate the satellite's position at the target time
    geocentric = satellite.at(skyfield_time)
    
    # Convert to geographic coordinates
    subpoint = geocentric.subpoint()
    
    # Extract the values
    latitude = subpoint.latitude.degrees
    longitude = subpoint.longitude.degrees
    altitude = subpoint.elevation.km
    
    return {
        'latitude': latitude,
        'longitude': longitude,
        'altitude': altitude,
        'timestamp': target_time.strftime('%Y-%m-%d %H:%M:%S UTC')
    }


def get_iss_data(use_local: bool = True, target_time: datetime = None):
    """
    Get ISS TLE data and calculate position at specified time.
    
    Args:
        use_local: If True, use local JSON file; if False, download from API
        target_time: If provided, calculate position at this time; if None, use current time
        
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
        
        # Calculate position at specified time or current time
        if target_time is not None:
            position = calculate_position_at_time(satellite, target_time)
        else:
            position = calculate_iss_position(satellite)
        
        return position, json_data, None
        
    except Exception as e:
        return None, None, str(e)


def download_multiple_satellites(group: str = 'active', limit: int = 50):
    """
    Download TLE data for multiple satellites from CelesTrak.
    
    Optimized for near real-time performance (30-100 objects, 200-500ms).
    Uses 3LE format to ensure TLE lines are available for position calculations.
    
    Args:
        group: CelesTrak group name ('active', 'stations', 'starlink', 'weather', etc.)
        limit: Maximum number of satellites to download (30-100 recommended for speed)
        
    Returns:
        list: List of satellite dictionaries with TLE data (OBJECT_NAME, TLE_LINE1, TLE_LINE2, NORAD_CAT_ID)
    """
    url = "https://celestrak.org/NORAD/elements/gp.php"
    params = {
        'GROUP': group,
        'FORMAT': '3le'  # Use 3LE format for reliable TLE lines
    }
    
    try:
        headers = {'User-Agent': 'SatWatch/1.0 (Educational/Research Project)'}
        
        # Add small delay to avoid rate limiting (CelesTrak may throttle rapid requests)
        time.sleep(0.5)  # 500ms delay to be respectful to CelesTrak
        
        # Reduced timeout for faster failure (5s instead of 60s)
        response = requests.get(url, params=params, timeout=5, headers=headers)
        
        # Handle 403 Forbidden (rate limiting)
        if response.status_code == 403:
            raise requests.RequestException(
                "CelesTrak is rate-limiting requests. Please wait a few minutes and try again, "
                "or reduce the traffic density slider."
            )
        
        response.raise_for_status()
        
        # Parse 3LE format (three lines per satellite: name, TLE line 1, TLE line 2)
        # Optimized parsing - stop early when limit reached
        lines = response.text.strip().split('\n')
        satellites = []
        
        i = 0
        while i < len(lines) and len(satellites) < limit:
            # Skip empty lines
            while i < len(lines) and not lines[i].strip():
                i += 1
            
            if i + 2 < len(lines):
                name_line = lines[i].strip()
                tle_line1 = lines[i + 1].strip()
                tle_line2 = lines[i + 2].strip()
                
                # Quick validation - check TLE line format
                if tle_line1.startswith('1 ') and tle_line2.startswith('2 '):
                    # Extract catalog number from TLE line 1 (positions 2-7)
                    try:
                        catnr = int(tle_line1[2:7])
                        satellites.append({
                            'OBJECT_NAME': name_line,
                            'TLE_LINE1': tle_line1,
                            'TLE_LINE2': tle_line2,
                            'NORAD_CAT_ID': str(catnr),
                            'OBJECT_ID': str(catnr)
                        })
                    except (ValueError, IndexError):
                        pass  # Skip invalid TLE
                
                i += 3  # Move to next satellite
            else:
                break
        
        return satellites
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


def load_conjunction_results() -> dict:
    """
    Load conjunction monitoring results from JSON file.
    
    Returns:
        dict: Conjunction results with timestamp and results list, or None if file doesn't exist
    """
    project_root = Path(__file__).parent.parent
    results_file = project_root / 'data' / 'conjunction_results.json'
    
    try:
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.warning(f"Could not load conjunction results: {e}")
    
    return None


def get_satellite_risks(conjunction_results: dict, catnr: int, sat_name: str) -> list:
    """
    Get all conjunction risks for a specific satellite.
    
    Args:
        conjunction_results: Conjunction results dictionary
        catnr: Catalog number of the satellite
        sat_name: Name of the satellite
        
    Returns:
        list: List of risk dictionaries for this satellite
    """
    if not conjunction_results or 'results' not in conjunction_results:
        return []
    
    risks = []
    for result in conjunction_results['results']:
        # Check if this satellite is involved in this conjunction
        sat1_name = result.get('sat1_name', '')
        sat2_name = result.get('sat2_name', '')
        
        if sat_name in sat1_name or sat_name in sat2_name:
            # Determine the other satellite
            other_sat = sat2_name if sat_name in sat1_name else sat1_name
            risks.append({
                'risk_level': result.get('risk_level', 'NORMAL'),
                'distance_km': result.get('min_distance_km', 0),
                'time': result.get('min_distance_time', ''),
                'other_satellite': other_sat,
                'position_at_closest': result.get('sat1_position_at_closest' if sat_name in sat1_name else 'sat2_position_at_closest', {})
            })
    
    return risks


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


def calculate_orbital_parameters(tle_data: dict) -> dict:
    """
    Calculate orbital parameters from TLE data.
    
    Extracts and calculates key orbital parameters that are useful for
    understanding a satellite's orbit characteristics.
    
    Args:
        tle_data: Dictionary containing TLE_LINE1, TLE_LINE2, and optionally
                  pre-parsed orbital elements from CelesTrak JSON format
        
    Returns:
        dict: Orbital parameters including:
            - inclination: Orbital inclination in degrees
            - eccentricity: Orbital eccentricity (0 = circular, 1 = parabolic)
            - period_minutes: Orbital period in minutes
            - apogee_km: Apogee altitude in km (highest point)
            - perigee_km: Perigee altitude in km (lowest point)
            - semi_major_axis_km: Semi-major axis in km
            - mean_motion: Revolutions per day
            - raan: Right Ascension of Ascending Node in degrees
            - arg_perigee: Argument of Perigee in degrees
    """
    # Earth's radius in km
    EARTH_RADIUS_KM = 6378.137
    # Earth's gravitational parameter (km³/s²)
    MU = 398600.4418
    
    params = {}
    
    try:
        # Try to get values from pre-parsed JSON fields first (CelesTrak format)
        if 'INCLINATION' in tle_data:
            params['inclination'] = float(tle_data['INCLINATION'])
        if 'ECCENTRICITY' in tle_data:
            params['eccentricity'] = float(tle_data['ECCENTRICITY'])
        if 'MEAN_MOTION' in tle_data:
            params['mean_motion'] = float(tle_data['MEAN_MOTION'])
        if 'RA_OF_ASC_NODE' in tle_data:
            params['raan'] = float(tle_data['RA_OF_ASC_NODE'])
        if 'ARG_OF_PERICENTER' in tle_data:
            params['arg_perigee'] = float(tle_data['ARG_OF_PERICENTER'])
        
        # If not available, parse from TLE lines
        tle_line2 = tle_data.get('TLE_LINE2', '')
        if tle_line2 and len(tle_line2) >= 69:
            # TLE Line 2 format (0-indexed positions):
            # 8-16: Inclination (degrees)
            # 17-25: RAAN (degrees)
            # 26-33: Eccentricity (decimal point assumed)
            # 34-42: Argument of Perigee (degrees)
            # 43-51: Mean Anomaly (degrees)
            # 52-63: Mean Motion (revs/day)
            
            if 'inclination' not in params:
                try:
                    params['inclination'] = float(tle_line2[8:16].strip())
                except (ValueError, IndexError):
                    pass
            
            if 'raan' not in params:
                try:
                    params['raan'] = float(tle_line2[17:25].strip())
                except (ValueError, IndexError):
                    pass
            
            if 'eccentricity' not in params:
                try:
                    # Eccentricity in TLE has implied decimal point
                    ecc_str = tle_line2[26:33].strip()
                    params['eccentricity'] = float('0.' + ecc_str)
                except (ValueError, IndexError):
                    pass
            
            if 'arg_perigee' not in params:
                try:
                    params['arg_perigee'] = float(tle_line2[34:42].strip())
                except (ValueError, IndexError):
                    pass
            
            if 'mean_motion' not in params:
                try:
                    params['mean_motion'] = float(tle_line2[52:63].strip())
                except (ValueError, IndexError):
                    pass
        
        # Calculate derived parameters if we have mean motion
        if 'mean_motion' in params and params['mean_motion'] > 0:
            mean_motion = params['mean_motion']
            
            # Orbital period in minutes
            params['period_minutes'] = 1440.0 / mean_motion  # 1440 = minutes per day
            
            # Semi-major axis using Kepler's third law
            # T = 2π√(a³/μ) => a = (μ(T/2π)²)^(1/3)
            period_seconds = params['period_minutes'] * 60
            params['semi_major_axis_km'] = (MU * (period_seconds / (2 * math.pi))**2)**(1/3)
            
            # Calculate apogee and perigee if we have eccentricity
            if 'eccentricity' in params:
                ecc = params['eccentricity']
                sma = params['semi_major_axis_km']
                
                # Apogee = a(1+e) - Earth_radius
                # Perigee = a(1-e) - Earth_radius
                params['apogee_km'] = sma * (1 + ecc) - EARTH_RADIUS_KM
                params['perigee_km'] = sma * (1 - ecc) - EARTH_RADIUS_KM
        
        return params
        
    except Exception as e:
        # Return whatever we managed to calculate
        params['error'] = str(e)
        return params


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
    Create a 3D sphere representing Earth with realistic coloring.
    
    Args:
        earth_radius: Earth radius in kilometers
        resolution: Number of points for sphere resolution
        
    Returns:
        tuple: (x, y, z, colors) arrays for sphere surface with color data
    """
    # Create sphere using spherical coordinates
    theta = np.linspace(0, 2 * np.pi, resolution)  # Longitude
    phi = np.linspace(0, np.pi, resolution)       # Latitude
    
    theta, phi = np.meshgrid(theta, phi)
    
    # Convert to Cartesian coordinates
    x = earth_radius * np.sin(phi) * np.cos(theta)
    y = earth_radius * np.sin(phi) * np.sin(theta)
    z = earth_radius * np.cos(phi)
    
    # Create realistic Earth coloring based on latitude/longitude patterns
    # This creates an approximation of Earth's appearance
    colors = np.zeros_like(phi)
    
    # Convert phi to latitude (-90 to 90) and theta to longitude (-180 to 180)
    lat = 90 - np.degrees(phi)  # phi=0 is north pole, phi=pi is south pole
    lon = np.degrees(theta) - 180  # Center on prime meridian
    
    # Base ocean color (value ~0.3 for blue)
    colors[:] = 0.3
    
    # Approximate continental patterns
    # North America (lat 25-70, lon -170 to -50)
    na_mask = (lat > 25) & (lat < 70) & (lon > -170) & (lon < -50)
    colors[na_mask] = 0.55
    
    # South America (lat -55 to 15, lon -80 to -35)
    sa_mask = (lat > -55) & (lat < 15) & (lon > -80) & (lon < -35)
    colors[sa_mask] = 0.5
    
    # Europe (lat 35-70, lon -10 to 40)
    eu_mask = (lat > 35) & (lat < 70) & (lon > -10) & (lon < 40)
    colors[eu_mask] = 0.55
    
    # Africa (lat -35 to 37, lon -20 to 55)
    af_mask = (lat > -35) & (lat < 37) & (lon > -20) & (lon < 55)
    colors[af_mask] = 0.6
    
    # Asia (lat 5-75, lon 40 to 180)
    as_mask = (lat > 5) & (lat < 75) & (lon > 40) & (lon < 180)
    colors[as_mask] = 0.55
    
    # Australia (lat -45 to -10, lon 110 to 155)
    au_mask = (lat > -45) & (lat < -10) & (lon > 110) & (lon < 155)
    colors[au_mask] = 0.6
    
    # Antarctica (lat < -60)
    ant_mask = lat < -60
    colors[ant_mask] = 0.95
    
    # Arctic ice (lat > 75)
    arc_mask = lat > 75
    colors[arc_mask] = 0.9
    
    # Add some variation/noise for texture
    noise = np.random.uniform(-0.05, 0.05, colors.shape)
    colors = np.clip(colors + noise, 0, 1)
    
    return x, y, z, colors


def get_earth_colorscale():
    """
    Return a custom colorscale for realistic Earth rendering.
    
    Returns:
        list: Plotly colorscale for Earth visualization
    """
    return [
        [0.0, 'rgb(10, 30, 60)'],      # Deep ocean (dark blue)
        [0.25, 'rgb(30, 80, 140)'],    # Ocean (medium blue)
        [0.35, 'rgb(50, 120, 180)'],   # Shallow water (light blue)
        [0.45, 'rgb(80, 120, 80)'],    # Coastal/lowland (green)
        [0.55, 'rgb(100, 140, 80)'],   # Plains (light green)
        [0.65, 'rgb(140, 130, 90)'],   # Highland (tan)
        [0.75, 'rgb(120, 100, 70)'],   # Mountains (brown)
        [0.85, 'rgb(180, 180, 180)'],  # Snow/high altitude (light gray)
        [0.95, 'rgb(240, 245, 255)'],  # Ice caps (white)
        [1.0, 'rgb(255, 255, 255)'],   # Bright ice (pure white)
    ]


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
    focus_mode: bool = False,
    conjunction_results: dict = None,
    satellite_visibility: dict = None
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
    
    # Create Earth sphere with realistic colors
    earth_x, earth_y, earth_z, earth_colors = create_earth_sphere(earth_radius, resolution=80)
    
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
        
        # Check visibility - skip if satellite is hidden
        if satellite_visibility and catnr in satellite_visibility:
            if not satellite_visibility[catnr]:
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
    
    # Add Earth sphere with realistic coloring
    fig.add_trace(go.Surface(
        x=earth_x,
        y=earth_y,
        z=earth_z,
        surfacecolor=earth_colors,
        colorscale=get_earth_colorscale(),
        showscale=False,
        opacity=1.0,
        name='Earth',
        lighting=dict(
            ambient=0.6,
            diffuse=0.8,
            specular=0.2,
            roughness=0.9,
            fresnel=0.1
        ),
        lightposition=dict(x=10000, y=10000, z=10000)
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
    
    # Build risk map for satellites
    risk_map = {}  # catnr -> highest risk level
    conjunction_pairs = []  # List of (sat1_catnr, sat2_catnr, risk_level, distance)
    
    if conjunction_results and 'results' in conjunction_results:
        for result in conjunction_results['results']:
            sat1_name = result.get('sat1_name', '')
            sat2_name = result.get('sat2_name', '')
            risk_level = result.get('risk_level', 'NORMAL')
            distance = result.get('min_distance_km', 0)
            
            # Find catalog numbers for these satellites
            sat1_catnr = None
            sat2_catnr = None
            for sat in tracked_satellites:
                if sat['name'] in sat1_name or sat1_name in sat['name']:
                    sat1_catnr = sat['catnr']
                if sat['name'] in sat2_name or sat2_name in sat['name']:
                    sat2_catnr = sat['catnr']
            
            if sat1_catnr and sat2_catnr:
                # Update risk map
                for catnr in [sat1_catnr, sat2_catnr]:
                    current_risk = risk_map.get(catnr, 'NORMAL')
                    risk_priority = {'CRITICAL': 2, 'HIGH RISK': 1, 'NORMAL': 0}
                    if risk_priority.get(risk_level, 0) > risk_priority.get(current_risk, 0):
                        risk_map[catnr] = risk_level
                
                # Store conjunction pair
                conjunction_pairs.append((sat1_catnr, sat2_catnr, risk_level, distance))
    
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
    
    # Helper function to get marker color and glow based on risk
    def get_marker_style(catnr, base_color, base_size):
        risk = risk_map.get(catnr, 'NORMAL')
        if risk == 'CRITICAL':
            # Red pulsing glow effect (larger size, red color)
            return {
                'size': base_size * 1.5,
                'color': 'red',
                'symbol': 'circle',
                'line': dict(width=primary_line_width * 2, color='darkred'),
                'opacity': 1.0
            }
        elif risk == 'HIGH RISK':
            # Orange highlight
            return {
                'size': base_size * 1.2,
                'color': 'orange',
                'symbol': 'circle',
                'line': dict(width=primary_line_width * 1.5, color='darkorange'),
                'opacity': 1.0
            }
        else:
            return {
                'size': base_size,
                'color': base_color,
                'symbol': 'circle',
                'line': dict(width=primary_line_width, color=f'dark{base_color}' if base_color != 'gray' else 'darkgray'),
                'opacity': 1.0
            }
    
    # Add primary stations (red) - tracked satellites in focus mode, or all in normal mode
    # Separate by risk level for different styling
    if primary_stations_data['x']:
        # Group by risk level
        critical_stations = {'x': [], 'y': [], 'z': [], 'names': []}
        high_risk_stations = {'x': [], 'y': [], 'z': [], 'names': []}
        normal_stations = {'x': [], 'y': [], 'z': [], 'names': []}
        
        for i, catnr in enumerate(primary_stations_data['catnrs']):
            risk = risk_map.get(catnr, 'NORMAL')
            if risk == 'CRITICAL':
                critical_stations['x'].append(primary_stations_data['x'][i])
                critical_stations['y'].append(primary_stations_data['y'][i])
                critical_stations['z'].append(primary_stations_data['z'][i])
                critical_stations['names'].append(primary_stations_data['names'][i])
            elif risk == 'HIGH RISK':
                high_risk_stations['x'].append(primary_stations_data['x'][i])
                high_risk_stations['y'].append(primary_stations_data['y'][i])
                high_risk_stations['z'].append(primary_stations_data['z'][i])
                high_risk_stations['names'].append(primary_stations_data['names'][i])
            else:
                normal_stations['x'].append(primary_stations_data['x'][i])
                normal_stations['y'].append(primary_stations_data['y'][i])
                normal_stations['z'].append(primary_stations_data['z'][i])
                normal_stations['names'].append(primary_stations_data['names'][i])
        
        # Add CRITICAL risk stations (red, larger, pulsing effect)
        if critical_stations['x']:
            fig.add_trace(go.Scatter3d(
                x=critical_stations['x'],
                y=critical_stations['y'],
                z=critical_stations['z'],
                mode='markers+text' if focus_mode else 'markers',
                marker=dict(
                    size=primary_marker_size * 1.5,
                    color='red',
                    symbol='circle',
                    line=dict(width=primary_line_width * 2, color='darkred'),
                    opacity=1.0
                ),
                text=[name.split('<br>')[0] for name in critical_stations['names']] if focus_mode else None,
                textposition='top center' if focus_mode else None,
                name='🚨 CRITICAL RISK Stations',
                hovertemplate='%{customdata[0]}<extra></extra>',
                customdata=[[name] for name in critical_stations['names']]
            ))
        
        # Add HIGH RISK stations (orange, larger)
        if high_risk_stations['x']:
            fig.add_trace(go.Scatter3d(
                x=high_risk_stations['x'],
                y=high_risk_stations['y'],
                z=high_risk_stations['z'],
                mode='markers+text' if focus_mode else 'markers',
                marker=dict(
                    size=primary_marker_size * 1.2,
                    color='orange',
                    symbol='circle',
                    line=dict(width=primary_line_width * 1.5, color='darkorange'),
                    opacity=1.0
                ),
                text=[name.split('<br>')[0] for name in high_risk_stations['names']] if focus_mode else None,
                textposition='top center' if focus_mode else None,
                name='⚠️ HIGH RISK Stations',
                hovertemplate='%{customdata[0]}<extra></extra>',
                customdata=[[name] for name in high_risk_stations['names']]
            ))
        
        # Add normal stations
        if normal_stations['x']:
            fig.add_trace(go.Scatter3d(
                x=normal_stations['x'],
                y=normal_stations['y'],
                z=normal_stations['z'],
                mode='markers+text' if focus_mode else 'markers',
                marker=dict(
                    size=primary_marker_size,
                    color='red',
                    symbol='circle',
                    line=dict(width=primary_line_width, color='darkred'),
                    opacity=1.0
                ),
                text=[name.split('<br>')[0] for name in normal_stations['names']] if focus_mode else None,
                textposition='top center' if focus_mode else None,
                name='My Stations' if focus_mode else 'Stations',
                hovertemplate='%{customdata[0]}<extra></extra>',
                customdata=[[name] for name in normal_stations['names']]
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
    
    # Add conjunction lines between pairs
    if conjunction_pairs and all_sat_positions:
        # Build position map
        pos_map = {}
        for sat_pos in all_sat_positions:
            x, y, z, name, alt, sat_type, catnr, lat, lon = sat_pos
            if not (math.isnan(x) or math.isnan(y) or math.isnan(z)):
                pos_map[catnr] = (x, y, z)
        
        # Draw lines for each conjunction pair
        for sat1_catnr, sat2_catnr, risk_level, distance in conjunction_pairs:
            if sat1_catnr in pos_map and sat2_catnr in pos_map:
                pos1 = pos_map[sat1_catnr]
                pos2 = pos_map[sat2_catnr]
                
                # Determine line color based on risk
                if risk_level == 'CRITICAL':
                    line_color = 'red'
                    line_width = 3
                elif risk_level == 'HIGH RISK':
                    line_color = 'orange'
                    line_width = 2
                else:
                    line_color = 'yellow'
                    line_width = 1
                
                fig.add_trace(go.Scatter3d(
                    x=[pos1[0], pos2[0]],
                    y=[pos1[1], pos2[1]],
                    z=[pos1[2], pos2[2]],
                    mode='lines',
                    line=dict(color=line_color, width=line_width, dash='dash'),
                    name=f'Conjunction: {risk_level}',
                    showlegend=False,
                    hovertemplate=f'{risk_level} Risk<br>Distance: {distance:.3f} km<extra></extra>'
                ))
    
    # Set camera angle and layout
    # Use a reasonable range that shows Earth and satellites clearly
    axis_range = max(20000, proximity_radius_km * 2)  # Ensure Earth (6371 km) is visible
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, range=[-axis_range, axis_range], backgroundcolor='#0e1117'),
            yaxis=dict(visible=False, range=[-axis_range, axis_range], backgroundcolor='#0e1117'),
            zaxis=dict(visible=False, range=[-axis_range, axis_range], backgroundcolor='#0e1117'),
            aspectmode='cube',
            camera=dict(
                eye=dict(x=0.35, y=0.35, z=0.3),  # Maximized Earth view for demo
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            ),
            bgcolor='#0e1117'
        ),
        title=None,
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
    
    # Create Earth sphere with realistic colors
    earth_x, earth_y, earth_z, earth_colors = create_earth_sphere(earth_radius, resolution=80)
    
    # Create the 3D plot
    fig = go.Figure()
    
    # Add Earth sphere with realistic coloring
    fig.add_trace(go.Surface(
        x=earth_x,
        y=earth_y,
        z=earth_z,
        surfacecolor=earth_colors,
        colorscale=get_earth_colorscale(),
        showscale=False,
        opacity=1.0,
        name='Earth',
        lighting=dict(
            ambient=0.6,
            diffuse=0.8,
            specular=0.2,
            roughness=0.9,
            fresnel=0.1
        ),
        lightposition=dict(x=10000, y=10000, z=10000)
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
            xaxis=dict(visible=False, range=[-axis_range, axis_range], backgroundcolor='#0e1117'),
            yaxis=dict(visible=False, range=[-axis_range, axis_range], backgroundcolor='#0e1117'),
            zaxis=dict(visible=False, range=[-axis_range, axis_range], backgroundcolor='#0e1117'),
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

# Clean Header
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; margin-bottom: 1rem;">
    <div style="font-size: 1.5rem; font-weight: bold;">🛰️ SatWatch</div>
    <div style="color: #00ff00; font-size: 0.9rem;">● Live</div>
</div>
""", unsafe_allow_html=True)

# Initialize time session state BEFORE sidebar (so it's available for data loading)
if 'live_mode' not in st.session_state:
    st.session_state.live_mode = True
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.now(timezone.utc).date()
if 'selected_hour' not in st.session_state:
    st.session_state.selected_hour = datetime.now(timezone.utc).hour
if 'selected_minute' not in st.session_state:
    st.session_state.selected_minute = datetime.now(timezone.utc).minute

# Calculate the target time based on session state
if st.session_state.live_mode:
    target_time = datetime.now(timezone.utc)
else:
    target_time = datetime(
        year=st.session_state.selected_date.year,
        month=st.session_state.selected_date.month,
        day=st.session_state.selected_date.day,
        hour=st.session_state.selected_hour,
        minute=st.session_state.selected_minute,
        second=0,
        tzinfo=timezone.utc
    )

# Store in session state for other components
st.session_state.selected_time = target_time

# Sidebar
with st.sidebar:
    st.header("📊 ISS Status")
    
    # Data source: CelesTrak API (default)
    # Developer note: Change use_local=True to use local file instead
    # This is useful for offline testing or when API is unavailable
    use_local = False  # Set to True for local file mode
    
    # Get ISS data (pass target_time for position calculation)
    position, json_data, error = get_iss_data(use_local=use_local, target_time=target_time)
    
    if error:
        st.error(f"❌ Error: {error}")
        
        # Check if local file exists as fallback
        import os
        local_file = Path(__file__).parent.parent / 'data' / 'iss_tle.json'
        if local_file.exists():
            st.info("💡 **Tip**: A local TLE file exists. To use it, edit `src/dashboard.py` line 1827 and change `use_local = False` to `use_local = True`")
        else:
            st.info("💡 **Tip**: CelesTrak may be rate-limiting requests. Wait a few minutes and refresh, or download fresh TLE data manually.")
        
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
        # ========================================
        # TIME CONTROLS (UI Phase 1)
        # ========================================
        st.subheader("⏱️ Time Controls")
        
        # Live mode toggle (session state already initialized before sidebar)
        live_mode = st.toggle(
            "🟢 LIVE MODE",
            value=st.session_state.live_mode,
            help="When enabled, shows real-time satellite positions. Disable to view positions at any date/time."
        )
        
        # Check if live mode changed
        if live_mode != st.session_state.live_mode:
            st.session_state.live_mode = live_mode
            st.rerun()  # Rerun to recalculate positions with new time
        
        if live_mode:
            # Live mode - show current time
            st.success(f"**🟢 LIVE** - {target_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        else:
            # Historical/Future mode - show date/time pickers
            st.warning("**📅 VIEWING SELECTED TIME** - Not live data")
            
            # Date picker
            selected_date = st.date_input(
                "Select Date",
                value=st.session_state.selected_date,
                help="Choose a date to view satellite positions"
            )
            
            # Time picker using columns for hour and minute
            time_col1, time_col2 = st.columns(2)
            with time_col1:
                selected_hour = st.number_input(
                    "Hour (UTC)",
                    min_value=0,
                    max_value=23,
                    value=st.session_state.selected_hour,
                    help="Hour in UTC (0-23)"
                )
            with time_col2:
                selected_minute = st.number_input(
                    "Minute",
                    min_value=0,
                    max_value=59,
                    value=st.session_state.selected_minute,
                    help="Minute (0-59)"
                )
            
            # Check if date/time changed and rerun if needed
            time_changed = (
                selected_date != st.session_state.selected_date or
                selected_hour != st.session_state.selected_hour or
                selected_minute != st.session_state.selected_minute
            )
            
            if time_changed:
                st.session_state.selected_date = selected_date
                st.session_state.selected_hour = selected_hour
                st.session_state.selected_minute = selected_minute
                st.rerun()  # Rerun to recalculate positions with new time
            
            # Show selected time prominently
            st.info(f"**Viewing:** {target_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            # Quick time navigation buttons
            nav_col1, nav_col2, nav_col3 = st.columns(3)
            with nav_col1:
                if st.button("◀ -1 Hour", use_container_width=True):
                    new_time = target_time - timedelta(hours=1)
                    st.session_state.selected_date = new_time.date()
                    st.session_state.selected_hour = new_time.hour
                    st.session_state.selected_minute = new_time.minute
                    st.rerun()
            with nav_col2:
                if st.button("🔴 Go Live", use_container_width=True, type="primary"):
                    st.session_state.live_mode = True
                    st.rerun()
            with nav_col3:
                if st.button("+1 Hour ▶", use_container_width=True):
                    new_time = target_time + timedelta(hours=1)
                    st.session_state.selected_date = new_time.date()
                    st.session_state.selected_hour = new_time.hour
                    st.session_state.selected_minute = new_time.minute
                    st.rerun()
            
            # Show time difference from now
            now = datetime.now(timezone.utc)
            time_diff = target_time - now
            if time_diff.total_seconds() > 0:
                st.caption(f"🔮 Viewing {abs(time_diff.days)} days, {abs(time_diff.seconds // 3600)} hours into the **future**")
            else:
                st.caption(f"📜 Viewing {abs(time_diff.days)} days, {abs(time_diff.seconds // 3600)} hours into the **past**")
        
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
        
        # SEARCH SECTION (matching reference images)
        st.subheader("🔍 SEARCH")
        search_query = st.text_input(
            "Search our space catalog",
            value=st.session_state.get('search_query', ''),
            key='search_input',
            placeholder="Search by name or NORAD ID..."
        )
        st.session_state.search_query = search_query
        
        # Filter satellites based on search
        filtered_satellites = tracked_satellites
        if search_query:
            query_lower = search_query.lower()
            filtered_satellites = [
                sat for sat in tracked_satellites
                if query_lower in sat['name'].lower() or str(sat['catnr']) == search_query
            ]
        
        # "My Satellites" quick filter button
        watched_satellites = st.session_state.get('watched_satellites', [])
        if watched_satellites:
            if st.button("⭐ My Satellites", key="my_satellites_btn", use_container_width=True, type="primary"):
                # Filter to only watched satellites
                filtered_satellites = [sat for sat in tracked_satellites if sat['catnr'] in watched_satellites]
                st.session_state.search_query = ""  # Clear search when using this filter
                st.rerun()
        
        st.markdown("---")
        
        # SPACE OBJECTS SECTION (expandable, matching reference images)
        if tracked_satellites:
            with st.expander("🛰️ Space Objects", expanded=True):
                # Toggle to show/hide all space objects
                show_space_objects = st.toggle(
                    "Show Space Objects",
                    value=st.session_state.get('show_space_objects', True),
                    key='show_space_objects_toggle'
                )
                st.session_state.show_space_objects = show_space_objects
                
                # Filter to starred only checkbox
                show_starred_only = st.checkbox(
                    "Show Starred Space Objects Only",
                    value=st.session_state.get('show_starred_only', False),
                    key='show_starred_only_checkbox'
                )
                st.session_state.show_starred_only = show_starred_only
                
                # Initialize visibility state if not exists
                if 'satellite_visibility' not in st.session_state:
                    st.session_state.satellite_visibility = {sat['catnr']: True for sat in tracked_satellites}
                
                # Load conjunction results for risk indicators
                conjunction_results = load_conjunction_results()
                
                # Display filtered satellites
                display_satellites = filtered_satellites
                if show_starred_only:
                    display_satellites = [sat for sat in display_satellites if sat['catnr'] in watched_satellites]
                
                if display_satellites and show_space_objects:
                    # ========================================
                    # GROUP BY TYPE (UI Phase 4)
                    # ========================================
                    # Separate satellites by type
                    starred_sats = [sat for sat in display_satellites if sat['catnr'] in watched_satellites]
                    stations = [sat for sat in display_satellites if sat.get('type') == 'station' and sat['catnr'] not in watched_satellites]
                    satellites = [sat for sat in display_satellites if sat.get('type') == 'satellite' and sat['catnr'] not in watched_satellites]
                    debris = [sat for sat in display_satellites if sat.get('type') == 'debris' and sat['catnr'] not in watched_satellites]
                    other = [sat for sat in display_satellites if sat.get('type') not in ['station', 'satellite', 'debris'] and sat['catnr'] not in watched_satellites]
                    
                    # Helper function to render satellite entry
                    def render_satellite_entry(sat, prefix=""):
                        catnr = sat['catnr']
                        name = sat['name']
                        sat_type = sat.get('type', 'satellite')
                        
                        is_selected = st.session_state.get('selected_satellite') == catnr
                        is_watched = catnr in watched_satellites
                        is_visible = st.session_state.satellite_visibility.get(catnr, True)
                        
                        # Get risk indicator
                        risks = get_satellite_risks(conjunction_results, catnr, name)
                        risk_indicator = "🟢"
                        if risks:
                            max_risk = max([r['risk_level'] for r in risks], key=lambda x: {'CRITICAL': 2, 'HIGH RISK': 1, 'NORMAL': 0}.get(x, 0))
                            if max_risk == 'CRITICAL':
                                risk_indicator = "🔴"
                            elif max_risk == 'HIGH RISK':
                                risk_indicator = "🟠"
                        
                        col1, col2, col3, col4 = st.columns([1, 3, 1, 1])
                        
                        with col1:
                            visibility_icon = "👁️" if is_visible else "👁️‍🗨️"
                            if st.button(visibility_icon, key=f"{prefix}vis_{catnr}", help="Toggle visibility"):
                                st.session_state.satellite_visibility[catnr] = not is_visible
                                st.rerun()
                        
                        with col2:
                            button_style = "primary" if is_selected else "secondary"
                            if st.button(name, key=f"{prefix}select_{catnr}", use_container_width=True, type=button_style):
                                st.session_state.selected_satellite = catnr
                                st.rerun()
                        
                        with col3:
                            star_icon = "⭐" if is_watched else "☆"
                            if st.button(star_icon, key=f"{prefix}star_{catnr}", help="Add to watched list"):
                                watched = st.session_state.get('watched_satellites', [])
                                if is_watched:
                                    watched.remove(catnr)
                                else:
                                    if catnr not in watched:
                                        watched.append(catnr)
                                st.session_state.watched_satellites = watched
                                st.rerun()
                        
                        with col4:
                            st.markdown(risk_indicator)
                    
                    # Render starred satellites first (pinned to top)
                    if starred_sats:
                        st.markdown("**⭐ Favorites**")
                        for sat in starred_sats:
                            render_satellite_entry(sat, "fav_")
                        st.markdown("")
                    
                    # Render stations
                    if stations:
                        with st.expander(f"🏠 Stations ({len(stations)})", expanded=True):
                            for sat in stations:
                                render_satellite_entry(sat, "sta_")
                    
                    # Render satellites
                    if satellites:
                        with st.expander(f"🛰️ Satellites ({len(satellites)})", expanded=True):
                            for sat in satellites:
                                render_satellite_entry(sat, "sat_")
                    
                    # Render debris
                    if debris:
                        with st.expander(f"💥 Debris ({len(debris)})", expanded=False):
                            for sat in debris:
                                render_satellite_entry(sat, "deb_")
                    
                    # Render other types
                    if other:
                        with st.expander(f"📡 Other ({len(other)})", expanded=False):
                            for sat in other:
                                render_satellite_entry(sat, "oth_")
                
                elif not display_satellites:
                    st.caption("No satellites match your search.")
                elif not show_space_objects:
                    st.caption("Space objects are hidden.")
        
        st.markdown("---")
        
        # WATCHED SATELLITES LIST (compact version)
        if watched_satellites:
            with st.expander("⭐ My Satellites", expanded=False):
                for watched_catnr in watched_satellites:
                    sat_info = None
                    for sat in tracked_satellites:
                        if sat['catnr'] == watched_catnr:
                            sat_info = sat
                            break
                    
                    if sat_info:
                        # Get risk indicator
                        risks = get_satellite_risks(conjunction_results, watched_catnr, sat_info['name'])
                        risk_color = "🟢"
                        if risks:
                            max_risk = max([r['risk_level'] for r in risks], key=lambda x: {'CRITICAL': 2, 'HIGH RISK': 1, 'NORMAL': 0}.get(x, 0))
                            if max_risk == 'CRITICAL':
                                risk_color = "🔴"
                            elif max_risk == 'HIGH RISK':
                                risk_color = "🟠"
                        
                        if st.button(f"{risk_color} {sat_info['name']}", key=f"watch_btn_{watched_catnr}", use_container_width=True):
                            st.session_state.selected_satellite = watched_catnr
                            st.rerun()
        
        st.markdown("---")
        
        # ========================================
        # SPACE TRAFFIC STATISTICS (Option 3)
        # ========================================
        st.subheader("📊 Space Traffic Statistics")
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        with stats_col1:
            st.metric("Tracked Objects", "25,000+", help="Objects larger than 10cm tracked by NORAD")
        with stats_col2:
            st.metric("Debris Pieces", "~500,000", help="Estimated pieces of debris 1-10cm in size")
        with stats_col3:
            st.metric("ISS Maneuvers/Year", "~2", help="Average collision avoidance maneuvers performed by ISS")
        
        st.caption("💡 **The Challenge**: LEO is becoming increasingly crowded. Every launch adds to the debris cloud.")
        st.markdown("---")
        
        # ========================================
        # SHOW FULL TRAFFIC TOGGLE (Option 1)
        # ========================================
        show_full_traffic = st.checkbox(
            "🚀 Show Full Traffic (Demo Mode)",
            value=st.session_state.get('show_full_traffic', True),  # Default: enabled for demo
            help="Display additional active satellites to visualize space traffic density. Loads in <1 second.",
            key='show_full_traffic_checkbox'
        )
        st.session_state.show_full_traffic = show_full_traffic
        
        # Traffic density slider (only show when full traffic is enabled)
        traffic_count = 50  # Default: 50 objects for near real-time
        if show_full_traffic:
            traffic_count = st.slider(
                "Traffic Density",
                min_value=30,
                max_value=100,
                value=st.session_state.get('traffic_count', 50),
                step=10,
                help="Number of additional satellites to display (30-100). Lower = faster load.",
                key='traffic_count_slider'
            )
            st.session_state.traffic_count = traffic_count
            st.caption(f"⚡ Loading {traffic_count} satellites (~200-500ms)")
        
        st.markdown("---")
        
        # VIEW FILTERS (in expander, matching reference images)
        if tracked_satellites:
            with st.expander("⚙️ View Filters", expanded=False):
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
                    max_value=10000,
                    value=st.session_state.get('proximity_radius', 5000),
                    step=100,
                    help="Show objects within this distance",
                    key='proximity_radius_slider'
                )
                st.session_state.proximity_radius = proximity_radius
                
                st.markdown("---")
                
                # Focus Mode toggle (ON by default for demo)
                focus_mode = st.checkbox(
                    "Focus on my satellites",
                    value=st.session_state.get('focus_mode', True),
                    help="When ON: Show your tracked satellites prominently with nearby objects as secondary. When OFF: Show all objects equally.",
                    key='focus_mode_checkbox'
                )
                st.session_state.focus_mode = focus_mode
                
                st.caption(f"Tracking {len(tracked_satellites)} satellites")
        else:
            # Default values if no tracked satellites
            show_stations = True
            show_satellites = True
            show_debris = True
            proximity_radius = 5000  # Larger radius for demo
            focus_mode = True  # ON by default for demo
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
    proximity_radius = st.session_state.get('proximity_radius', 5000)
    focus_mode = st.session_state.get('focus_mode', True)
    
    # Load conjunction results
    conjunction_results = load_conjunction_results()
    
    # Initialize watched satellites if not set
    if 'watched_satellites' not in st.session_state:
        st.session_state.watched_satellites = []
    
    # Initialize selected satellite if not set
    if 'selected_satellite' not in st.session_state:
        st.session_state.selected_satellite = None
    
    # Get the selected time from session state (set before sidebar)
    current_time = st.session_state.get('selected_time', datetime.now(timezone.utc))
    
    # Calculate positions for all tracked satellites (needed for profile panel and views)
    all_sat_positions = []
    if tracked_satellites and satellites_tle_data:
        try:
            all_sat_positions = calculate_tracked_satellite_positions(
                tracked_satellites,
                satellites_tle_data,
                current_time
            )
        except Exception as e:
            all_sat_positions = []
    
    # Main content layout: 3D view on left, profile panel on right (matching reference images)
    main_col1, main_col2 = st.columns([2, 1])
    
    # Satellite Profile Panel (right sidebar, matching reference images)
    selected_catnr = st.session_state.get('selected_satellite')
    with main_col2:
        if selected_catnr:
            # Find satellite info
            sat_info = None
            sat_tle_data = None
            for sat in tracked_satellites:
                if sat['catnr'] == selected_catnr:
                    sat_info = sat
                    sat_tle_data = satellites_tle_data.get(selected_catnr)
                    break
            
            if sat_info and sat_tle_data:
                # Profile Panel Header (matching reference images)
                profile_header_col1, profile_header_col2 = st.columns([4, 1])
                with profile_header_col1:
                    st.subheader("🛰️ SATELLITE PROFILE")
                    st.markdown(f"**{sat_info['name']}**")
                    st.caption(f"NORAD ID: {selected_catnr}")
                with profile_header_col2:
                    # Star button to add to watched list
                    is_watched = selected_catnr in st.session_state.get('watched_satellites', [])
                    star_icon = "⭐" if is_watched else "☆"
                    if st.button(star_icon, key=f"star_{selected_catnr}", help="Add to watched list"):
                        watched = st.session_state.get('watched_satellites', [])
                        if is_watched:
                            watched.remove(selected_catnr)
                        else:
                            if selected_catnr not in watched:
                                watched.append(selected_catnr)
                        st.session_state.watched_satellites = watched
                        st.rerun()
                    # Close button
                    if st.button("✕", key=f"close_{selected_catnr}", help="Close profile"):
                        st.session_state.selected_satellite = None
                        st.rerun()
                
                st.markdown("---")
            
            # General Information
            st.markdown("**General Information**")
            st.write(f"**Object Type:** {sat_info['type'].title()}")
            st.write(f"**Mission Type:** Not Available")  # Placeholder - could be added to satellites.json
            st.write(f"**Country:** Not Available")  # Placeholder
            st.write(f"**Sector:** Not Available")  # Placeholder
                
            # Current Position
            st.subheader("📍 Current Position")
            # Use pre-calculated positions
            if all_sat_positions:
                for sat_pos in all_sat_positions:
                    x, y, z, name, alt, sat_type, catnr, lat, lon = sat_pos
                    if catnr == selected_catnr:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Latitude", f"{lat:.4f}°")
                        with col2:
                            st.metric("Longitude", f"{lon:.4f}°")
                        with col3:
                            st.metric("Altitude", f"{alt:.2f} km")
                        break
            
            st.markdown("---")
            
            # TLE Freshness
            st.subheader("📡 TLE Data")
            epoch = sat_tle_data.get('EPOCH', 'Unknown')
            if epoch != 'Unknown':
                status_level, hours_old, status_message = get_data_freshness_status(epoch)
                if status_level == 'fresh':
                    st.success(f"✅ {status_message}")
                elif status_level == 'warning':
                    st.warning(f"⚠️ {status_message}")
                elif status_level == 'old':
                    st.warning(f"⚠️ {status_message}")
                else:
                    st.error(f"❌ {status_message}")
            else:
                st.info("TLE epoch information not available")
            
            st.markdown("---")
            
            # ========================================
            # ORBITAL DATA SECTION (UI Phase 3)
            # ========================================
            with st.expander("🌍 Orbital Data", expanded=True):
                orbital_params = calculate_orbital_parameters(sat_tle_data)
                
                if orbital_params and 'inclination' in orbital_params:
                    # Primary orbital parameters
                    st.markdown("**Orbital Parameters**")
                    
                    # Inclination and Eccentricity row
                    orb_col1, orb_col2 = st.columns(2)
                    with orb_col1:
                        inc = orbital_params.get('inclination', 0)
                        st.metric("Inclination", f"{inc:.2f}°")
                        # Orbit type hint
                        if inc < 10:
                            st.caption("Near-equatorial")
                        elif inc > 80 and inc < 100:
                            st.caption("Polar orbit")
                        elif abs(inc - 98.7) < 5:
                            st.caption("Sun-synchronous")
                    
                    with orb_col2:
                        ecc = orbital_params.get('eccentricity', 0)
                        st.metric("Eccentricity", f"{ecc:.6f}")
                        if ecc < 0.01:
                            st.caption("Near-circular")
                        elif ecc < 0.1:
                            st.caption("Slightly elliptical")
                        else:
                            st.caption("Elliptical")
                    
                    # Period and Semi-major axis row
                    orb_col3, orb_col4 = st.columns(2)
                    with orb_col3:
                        period = orbital_params.get('period_minutes', 0)
                        if period > 0:
                            hours = int(period // 60)
                            mins = int(period % 60)
                            st.metric("Orbital Period", f"{hours}h {mins}m")
                            # Orbit altitude hint
                            if period < 100:
                                st.caption("Low Earth Orbit")
                            elif period < 720:
                                st.caption("LEO/MEO")
                            elif period > 1400 and period < 1450:
                                st.caption("Geostationary")
                    
                    with orb_col4:
                        mm = orbital_params.get('mean_motion', 0)
                        if mm > 0:
                            st.metric("Revs/Day", f"{mm:.4f}")
                    
                    # Apogee and Perigee row
                    st.markdown("**Altitude Range**")
                    orb_col5, orb_col6 = st.columns(2)
                    with orb_col5:
                        apogee = orbital_params.get('apogee_km', 0)
                        if apogee > 0:
                            st.metric("Apogee", f"{apogee:.1f} km")
                    
                    with orb_col6:
                        perigee = orbital_params.get('perigee_km', 0)
                        if perigee > 0:
                            st.metric("Perigee", f"{perigee:.1f} km")
                    
                    # Advanced parameters (collapsible)
                    with st.expander("Advanced Parameters", expanded=False):
                        adv_col1, adv_col2 = st.columns(2)
                        with adv_col1:
                            raan = orbital_params.get('raan', None)
                            if raan is not None:
                                st.metric("RAAN", f"{raan:.2f}°")
                            
                            sma = orbital_params.get('semi_major_axis_km', None)
                            if sma is not None:
                                st.metric("Semi-major Axis", f"{sma:.1f} km")
                        
                        with adv_col2:
                            arg_p = orbital_params.get('arg_perigee', None)
                            if arg_p is not None:
                                st.metric("Arg. of Perigee", f"{arg_p:.2f}°")
                else:
                    st.info("Orbital parameters not available for this satellite")
            
            st.markdown("---")
            
            # Conjunction Status
            st.subheader("⚠️ Conjunction Status")
            risks = get_satellite_risks(conjunction_results, selected_catnr, sat_info['name'])
            
            if risks:
                # Find highest risk
                max_risk = max(risks, key=lambda r: {'CRITICAL': 2, 'HIGH RISK': 1, 'NORMAL': 0}.get(r['risk_level'], 0))
                
                if max_risk['risk_level'] == 'CRITICAL':
                    st.error(f"🚨 **CRITICAL RISK**")
                elif max_risk['risk_level'] == 'HIGH RISK':
                    st.warning(f"⚠️ **HIGH RISK**")
                else:
                    st.info(f"ℹ️ **NORMAL RISK**")
                
                st.write(f"**Closest Object:** {max_risk['other_satellite']}")
                st.write(f"**Distance:** {max_risk['distance_km']:.3f} km")
                
                # Parse time string
                try:
                    if isinstance(max_risk['time'], str):
                        risk_time = datetime.fromisoformat(max_risk['time'].replace('Z', '+00:00'))
                        st.write(f"**Time of Closest Approach:** {risk_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                except:
                    st.write(f"**Time of Closest Approach:** {max_risk['time']}")
                
                # Show all risks if multiple
                if len(risks) > 1:
                    with st.expander(f"View all {len(risks)} conjunction risks"):
                        for i, risk in enumerate(risks, 1):
                            st.write(f"**{i}. {risk['other_satellite']}** - {risk['distance_km']:.3f} km ({risk['risk_level']})")
            else:
                st.success("✅ No conjunction risks detected")
        else:
            # Empty state - don't show placeholder message, keep UI clean
            pass
    
    # 3D Orbit View (main content, in left column)
    with main_col1:
        # Compact status bar
        live_mode = st.session_state.get('live_mode', True)
        if live_mode:
            time_status = f"🟢 LIVE · {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        else:
            now = datetime.now(timezone.utc)
            time_diff = current_time - now
            if time_diff.total_seconds() > 0:
                time_status = f"📅 {current_time.strftime('%Y-%m-%d %H:%M')} UTC · {abs(time_diff.days)}d {abs(time_diff.seconds // 3600)}h ahead"
            else:
                time_status = f"📅 {current_time.strftime('%Y-%m-%d %H:%M')} UTC · {abs(time_diff.days)}d {abs(time_diff.seconds // 3600)}h ago"
        st.caption(time_status)
        
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
            
                # Check if we have tracked satellites to show
                if tracked_satellites and satellites_tle_data:
                    # Use the new multi-satellite visualization
                    focus_mode = st.session_state.get('focus_mode', True)
                    show_full_traffic = st.session_state.get('show_full_traffic', False)
                    
                    # Get satellite visibility state
                    satellite_visibility = st.session_state.get('satellite_visibility', {})
                    
                    # If full traffic mode is enabled, fetch additional satellites (with caching)
                    full_traffic_data = {}
                    if show_full_traffic:
                        traffic_count = st.session_state.get('traffic_count', 50)
                        
                        # Check if we have cached data for this count
                        cache_key = f'full_traffic_data_{traffic_count}'
                        cached_traffic = st.session_state.get(cache_key)
                        cached_count = st.session_state.get('cached_traffic_count')
                        
                        # Only fetch if we don't have cached data or count changed
                        if cached_traffic and cached_count == traffic_count:
                            # Use cached data - no refetch needed
                            full_traffic_data = cached_traffic
                        else:
                            # Fetch fresh data
                            try:
                                # Fetch active satellites from CelesTrak (optimized for speed)
                                full_traffic_list = download_multiple_satellites(group='active', limit=traffic_count)
                                
                                # Convert to the format expected by the visualization
                                for sat_data in full_traffic_list:
                                    if 'TLE_LINE1' in sat_data and 'TLE_LINE2' in sat_data:
                                        # Extract catalog number
                                        try:
                                            catnr = int(sat_data.get('NORAD_CAT_ID', sat_data.get('OBJECT_ID', '0')))
                                            if catnr > 0:
                                                full_traffic_data[catnr] = sat_data
                                        except (ValueError, TypeError):
                                            continue
                                
                                # Cache the data for future reruns
                                st.session_state[cache_key] = full_traffic_data
                                st.session_state['cached_traffic_count'] = traffic_count
                            except Exception as e:
                                # If fetch fails, try to use cached data if available
                                if cached_traffic:
                                    full_traffic_data = cached_traffic
                                    st.warning(f"Using cached traffic data (fetch failed: {e})")
                                else:
                                    st.warning(f"Could not load full traffic data: {e}")
                    else:
                        # Clear cache when full traffic is disabled
                        if 'cached_traffic_count' in st.session_state:
                            del st.session_state['cached_traffic_count']
                            # Clear all cached traffic keys
                            keys_to_remove = [k for k in st.session_state.keys() if k.startswith('full_traffic_data_')]
                            for key in keys_to_remove:
                                del st.session_state[key]
                    
                    # Merge full traffic data with tracked satellites (tracked take priority)
                    combined_tle_data = {**full_traffic_data, **satellites_tle_data}
                    
                    # Create expanded tracked list for full traffic mode
                    if show_full_traffic:
                        # Add all full traffic satellites to tracked list for visualization
                        expanded_tracked = list(tracked_satellites)
                        for catnr, sat_data in full_traffic_data.items():
                            # Skip if already in tracked list
                            if catnr not in [s['catnr'] for s in tracked_satellites]:
                                expanded_tracked.append({
                                    'name': sat_data.get('OBJECT_NAME', f'Satellite {catnr}'),
                                    'catnr': catnr,
                                    'type': 'satellite'  # Default type
                                })
                        visualization_tracked = expanded_tracked
                    else:
                        visualization_tracked = tracked_satellites
                    
                    fig_3d, shown_count, total_count, nearby_count = create_3d_tracked_satellites_plot(
                        position,
                        satellite,
                        visualization_tracked,
                        combined_tle_data,
                        current_time,
                        show_stations=show_stations,
                        show_satellites=show_satellites,
                        show_debris=show_debris,
                        proximity_radius_km=proximity_radius,
                        focus_mode=focus_mode,
                        conjunction_results=conjunction_results,
                        satellite_visibility=satellite_visibility
                    )
                    
                    # Show the 3D plot first (main focus)
                    st.plotly_chart(fig_3d, use_container_width=True, key="3d_plot")
                    
                    # Compact satellite count caption below
                    if focus_mode:
                        st.caption(f"Tracking {shown_count} satellites · {nearby_count} nearby objects within {proximity_radius} km")
                    else:
                        st.caption(f"Showing {shown_count} of {total_count} objects within {proximity_radius} km")
                    
                    # Minimal status (only show if there are active risks)
                    active_risks = 0
                    if conjunction_results and 'results' in conjunction_results:
                        active_risks = len([r for r in conjunction_results['results'] if r.get('risk_level') in ['CRITICAL', 'HIGH RISK']])
                    
                    if active_risks > 0:
                        st.warning(f"⚠️ {active_risks} active conjunction risk(s) detected")
                    
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
                    st.plotly_chart(fig_3d, use_container_width=True, key="3d_plot_alt")
                    
                    # Status Bar at bottom
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    # Last conjunction check
                    if conjunction_results and 'timestamp' in conjunction_results:
                        try:
                            check_time = datetime.fromisoformat(conjunction_results['timestamp'].replace('Z', '+00:00'))
                            time_ago = current_time - check_time.replace(tzinfo=timezone.utc)
                            hours_ago = time_ago.total_seconds() / 3600
                            if hours_ago < 1:
                                time_str = f"{int(time_ago.total_seconds() / 60)} minutes ago"
                            else:
                                time_str = f"{hours_ago:.1f} hours ago"
                        except:
                            time_str = conjunction_results['timestamp']
                    else:
                        time_str = "Never"
                    
                    with col1:
                        st.caption(f"**Last conjunction check:** {time_str}")
                    
                    # Next check (placeholder for Phase 3)
                    with col2:
                        st.caption("**Next check:** Scheduled (Phase 3)")
                    
                    # Tracking stats
                    active_risks = 0
                    if conjunction_results and 'results' in conjunction_results:
                        active_risks = len([r for r in conjunction_results['results'] if r.get('risk_level') in ['CRITICAL', 'HIGH RISK']])
                    
                    with col3:
                        st.caption(f"**Tracking:** 0 objects | {active_risks} active risks")
                    
                    with col4:
                        if active_risks > 0:
                            st.warning(f"⚠️ {active_risks} active risk(s) detected")
                        else:
                            st.success("✅ No active risks")
                        
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
