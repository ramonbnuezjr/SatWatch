#!/usr/bin/env python3
"""
ISS Position Tracker (JSON Version)

This script downloads TLE data for the ISS from CelesTrak's JSON API
and calculates its current position using the Skyfield library.

Author: SatWatch Project
"""

import json
import os
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from skyfield.api import load, EarthSatellite


def extract_epoch_from_tle_line1(tle_line1: str) -> str:
    """
    Extract the epoch datetime from TLE Line 1.
    
    TLE Line 1 format: epoch is at characters 18-32 as YYDDD.DDDDDDDD
    - YY = year (00-56 = 2000-2056, 57-99 = 1957-1999)
    - DDD = day of year
    - .DDDDDDDD = fractional part of the day
    
    Args:
        tle_line1: TLE Line 1 string
        
    Returns:
        str: ISO format datetime string, or None if parsing fails
    """
    try:
        # Extract epoch portion (characters 18-32)
        epoch_str = tle_line1[18:32].strip()
        
        # Parse year (2-digit)
        year_2digit = int(epoch_str[:2])
        # Year convention: 00-56 = 2000-2056, 57-99 = 1957-1999
        if year_2digit >= 57:
            year = 1900 + year_2digit
        else:
            year = 2000 + year_2digit
        
        # Parse day of year and fractional day
        day_fraction = float(epoch_str[2:])
        day_of_year = int(day_fraction)
        fractional_day = day_fraction - day_of_year
        
        # Convert to datetime
        # Start with January 1 of the year, then add days
        epoch_dt = datetime(year, 1, 1, tzinfo=timezone.utc) + \
                   timedelta(days=day_of_year - 1 + fractional_day)
        
        return epoch_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    except Exception:
        return None


def load_iss_tle_from_file(file_path: str = None) -> dict:
    """
    Load TLE data for the ISS from a local JSON file.
    
    If no file path is provided, looks for 'iss_tle.json' in the data/ directory.
    
    Args:
        file_path: Path to the JSON file. If None, uses 'data/iss_tle.json'
        
    Returns:
        dict: JSON data containing TLE information for the ISS
        
    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        ValueError: If ISS data is not found in the file
        json.JSONDecodeError: If the file is not valid JSON
    """
    # Default to data/iss_tle.json if no path provided
    if file_path is None:
        # Get the project root directory (parent of src/)
        project_root = Path(__file__).parent.parent
        file_path = project_root / 'data' / 'iss_tle.json'
    
    # Convert to Path object if it's a string
    file_path = Path(file_path)
    
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    # Read and parse the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both array format and single object format
    if isinstance(data, list):
        # If it's an array, find the ISS entry
        for satellite in data:
            if (satellite.get('OBJECT_ID') == '25544' or 
                'ISS' in satellite.get('OBJECT_NAME', '').upper()):
                return satellite
        raise ValueError("ISS TLE data not found in JSON file")
    elif isinstance(data, dict):
        # If it's a single object, check if it's the ISS
        if (data.get('OBJECT_ID') == '25544' or 
            'ISS' in data.get('OBJECT_NAME', '').upper()):
            return data
        raise ValueError("JSON file does not contain ISS data")
    else:
        raise ValueError("Invalid JSON format: Expected array or object")


def download_iss_tle_json() -> dict:
    """
    Download the current TLE data for the ISS from CelesTrak.
    
    Tries multiple formats and methods with fallbacks:
    1. JSON format (GROUP=stations)
    2. 3LE format (CATNR=25544) - more reliable, less likely to be rate-limited
    3. Raises error if all methods fail
    
    Returns:
        dict: JSON data containing TLE information for the ISS
        
    Raises:
        requests.RequestException: If all download attempts fail
        ValueError: If ISS data is not found
    """
    headers = {
        'User-Agent': 'SatWatch/1.0 (Educational/Research Project)'
    }
    url = "https://celestrak.org/NORAD/elements/gp.php"
    
    # Method 1: Try 3LE format by catalog number (most reliable, less likely to be rate-limited)
    try:
        params_3le = {
            'CATNR': 25544,  # ISS catalog number
            'FORMAT': '3le'
        }
        response = requests.get(url, params=params_3le, timeout=10, headers=headers)
        
        if response.status_code == 200 and response.text:
            # Parse 3LE format (three lines: name, TLE line 1, TLE line 2)
            lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
            if len(lines) >= 3:
                name_line = lines[0]
                tle_line1 = lines[1]
                tle_line2 = lines[2]
                
                # Validate TLE format
                if tle_line1.startswith('1 ') and tle_line2.startswith('2 '):
                    # Extract epoch from TLE Line 1
                    epoch = extract_epoch_from_tle_line1(tle_line1)
                    
                    # Convert to JSON-like format
                    return {
                        'OBJECT_NAME': name_line,
                        'OBJECT_ID': '25544',
                        'NORAD_CAT_ID': '25544',
                        'TLE_LINE1': tle_line1,
                        'TLE_LINE2': tle_line2,
                        'EPOCH': epoch
                    }
    except Exception:
        pass  # Fall through to next method
    
    # Method 2: Try JSON format (GROUP=stations) - may be rate-limited
    try:
        params_json = {
            'GROUP': 'stations',
            'FORMAT': 'json'
        }
        response = requests.get(url, params=params_json, timeout=10, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Find the ISS entry (NORAD ID 25544)
            for satellite in data:
                if (satellite.get('OBJECT_ID') == '25544' or 
                    satellite.get('NORAD_CAT_ID') == '25544' or
                    'ISS' in satellite.get('OBJECT_NAME', '').upper()):
                    return satellite
    except Exception:
        pass  # Fall through to error
    
    # If all methods failed, raise an error
    raise requests.RequestException(
        "Could not download ISS TLE data from CelesTrak. "
        "The service may be temporarily unavailable or rate-limiting requests. "
        "Try again in a few moments, or use local file mode."
    )


def format_tle_line1(norad_id: int, classification: str, element_set_no: int, 
                     epoch_dt, mean_motion_dot: float, bstar: float) -> str:
    """
    Format TLE Line 1 according to standard TLE format.
    
    Format: 1 NNNNNU NNNNNAAA NNNNN.NNNNNNNN +.NNNNNNNN +NNNNN-N +NNNNN-N N NNNNN
    """
    # Calculate day of year
    day_of_year = epoch_dt.timetuple().tm_yday
    year_short = epoch_dt.year % 100
    
    # Format epoch as YYDDD.DDDDDDDD
    fractional_day = (epoch_dt.hour * 3600 + epoch_dt.minute * 60 + epoch_dt.second) / 86400.0
    epoch_str = f"{year_short:02d}{day_of_year:03d}.{fractional_day:8.8f}"[:14]
    
    # Format mean motion dot (rev/day^2) - convert to rev/day^2 format
    mm_dot_str = f"{mean_motion_dot:+.8f}"[:10]
    
    # Format BSTAR (drag term) - convert to scientific notation format
    bstar_exp = int(abs(bstar) * 1e5)
    bstar_sign = '-' if bstar < 0 else '+'
    bstar_str = f"{bstar_sign}{bstar_exp:05d}"
    
    # Build line 1
    line1 = (f"1 {norad_id:05d}{classification} "
             f"{element_set_no:04d}A "
             f"{epoch_str:<14} "
             f"{mm_dot_str} "
             f"00000+0 "
             f"{bstar_str}-0 "
             f"0 "
             f"{element_set_no:05d}")
    
    return line1.ljust(69)


def format_tle_line2(norad_id: int, inclination: float, raan: float,
                     eccentricity: float, arg_perigee: float, mean_anomaly: float,
                     mean_motion: float, rev_at_epoch: int) -> str:
    """
    Format TLE Line 2 according to standard TLE format.
    
    Format: 2 NNNNN NNN.NNNN NNN.NNNN NNNNNNN NNN.NNNN NNN.NNNN NN.NNNNNNNNNNNNNN
    """
    # Format eccentricity (multiply by 1e7, no decimal point)
    ecc_str = f"{int(eccentricity * 1e7):07d}"
    
    # Build line 2
    line2 = (f"2 {norad_id:05d} "
             f"{inclination:8.4f} "
             f"{raan:8.4f} "
             f"{ecc_str} "
             f"{arg_perigee:8.4f} "
             f"{mean_anomaly:8.4f} "
             f"{mean_motion:11.8f}"
             f"{rev_at_epoch:05d}")
    
    return line2.ljust(69)


def create_satellite_from_elements(json_data: dict) -> EarthSatellite:
    """
    Create a Skyfield EarthSatellite from individual orbital elements.
    
    Constructs proper TLE lines from orbital elements and creates an EarthSatellite.
    
    Args:
        json_data: Dictionary containing orbital elements
        
    Returns:
        EarthSatellite: Skyfield satellite object ready for calculations
    """
    from datetime import datetime
    
    # Extract orbital elements
    epoch_str = json_data.get('EPOCH', '')
    mean_motion = json_data.get('MEAN_MOTION', 0.0)  # revolutions per day
    mean_motion_dot = json_data.get('MEAN_MOTION_DOT', 0.0)  # rev/day^2
    bstar = json_data.get('BSTAR', 0.0)  # drag coefficient
    eccentricity = json_data.get('ECCENTRICITY', 0.0)
    inclination = json_data.get('INCLINATION', 0.0)  # degrees
    raan = json_data.get('RA_OF_ASC_NODE', 0.0)  # degrees
    arg_perigee = json_data.get('ARG_OF_PERICENTER', 0.0)  # degrees
    mean_anomaly = json_data.get('MEAN_ANOMALY', 0.0)  # degrees
    element_set_no = json_data.get('ELEMENT_SET_NO', 999)
    norad_id = json_data.get('NORAD_CAT_ID', 25544)
    classification = json_data.get('CLASSIFICATION_TYPE', 'U')
    rev_at_epoch = json_data.get('REV_AT_EPOCH', 0)
    name = json_data.get('OBJECT_NAME', 'ISS')
    
    # Parse epoch
    try:
        epoch_dt = datetime.fromisoformat(epoch_str.replace('Z', '+00:00'))
    except Exception as e:
        raise ValueError(f"Invalid EPOCH format: {epoch_str}") from e
    
    # Format TLE lines
    line1 = format_tle_line1(norad_id, classification, element_set_no, 
                             epoch_dt, mean_motion_dot, bstar)
    line2 = format_tle_line2(norad_id, inclination, raan, eccentricity,
                            arg_perigee, mean_anomaly, mean_motion, rev_at_epoch)
    
    # Create the satellite object
    ts = load.timescale()
    satellite = EarthSatellite(line1, line2, name, ts)
    
    return satellite


def parse_tle_from_json(json_data: dict) -> EarthSatellite:
    """
    Parse TLE data from JSON into a Skyfield EarthSatellite object.
    
    Supports two JSON formats:
    1. JSON with TLE_LINE1 and TLE_LINE2 (preferred)
    2. JSON with individual orbital elements (will construct TLE lines)
    
    Args:
        json_data: Dictionary containing TLE data or orbital elements
        
    Returns:
        EarthSatellite: Skyfield satellite object ready for calculations
    """
    name = json_data.get('OBJECT_NAME', 'ISS').strip()
    
    # Try to get TLE lines directly (preferred method)
    line1 = json_data.get('TLE_LINE1', '').strip()
    line2 = json_data.get('TLE_LINE2', '').strip()
    
    # If TLE lines are present, use them directly
    if line1 and line2:
        # Validate TLE line format (line1 should start with "1 ", line2 with "2 ")
        if not line1.startswith('1 ') or not line2.startswith('2 '):
            raise ValueError(f"Invalid TLE format in JSON data")
        
        # Create the satellite object from TLE data
        ts = load.timescale()
        satellite = EarthSatellite(line1, line2, name, ts)
        return satellite
    
    # If TLE lines are missing, create satellite from orbital elements
    # Check if we have the required orbital elements
    required_fields = ['MEAN_MOTION', 'ECCENTRICITY', 'INCLINATION', 
                      'RA_OF_ASC_NODE', 'ARG_OF_PERICENTER', 'MEAN_ANOMALY', 'EPOCH']
    
    if all(field in json_data for field in required_fields):
        print("  Creating satellite from orbital elements...")
        return create_satellite_from_elements(json_data)
    else:
        missing = [f for f in required_fields if f not in json_data]
        raise ValueError(
            f"Invalid JSON data: Missing TLE_LINE1/TLE_LINE2 and missing "
            f"orbital elements: {', '.join(missing)}"
        )


def calculate_iss_position(satellite: EarthSatellite) -> dict:
    """
    Calculate the current position of the ISS.
    
    Args:
        satellite: Skyfield EarthSatellite object
        
    Returns:
        dict: Dictionary containing latitude, longitude, altitude, and timestamp
    """
    # Load the timescale (needed for time calculations)
    ts = load.timescale()
    
    # Get the current time
    current_time = ts.now()
    
    # Calculate the satellite's position at the current time
    # 'at()' returns the satellite's position in space
    geocentric = satellite.at(current_time)
    
    # Convert to geographic coordinates (latitude, longitude, altitude)
    # 'subpoint()' gives us the point on Earth directly below the satellite
    subpoint = geocentric.subpoint()
    
    # Extract the values
    latitude = subpoint.latitude.degrees  # Degrees (-90 to 90)
    longitude = subpoint.longitude.degrees  # Degrees (-180 to 180)
    altitude = subpoint.elevation.km  # Kilometers above sea level
    
    return {
        'latitude': latitude,
        'longitude': longitude,
        'altitude': altitude,
        'timestamp': current_time.utc_strftime('%Y-%m-%d %H:%M:%S UTC')
    }


def format_position(position: dict) -> str:
    """
    Format the position data into a human-readable string.
    
    Args:
        position: Dictionary with latitude, longitude, altitude, timestamp
        
    Returns:
        str: Formatted string for display
    """
    # Format with nice spacing and units
    output = f"""
╔═══════════════════════════════════════════════════════════╗
║              INTERNATIONAL SPACE STATION (ISS)            ║
║                    Current Position                        ║
╠═══════════════════════════════════════════════════════════╣
║  Time:        {position['timestamp']:<45}  ║
║  Latitude:    {position['latitude']:>8.4f}°{'':<38}  ║
║  Longitude:   {position['longitude']:>8.4f}°{'':<38}  ║
║  Altitude:    {position['altitude']:>8.2f} km{'':<38}  ║
╚═══════════════════════════════════════════════════════════╝
"""
    return output


def main(use_local_file: bool = False, json_file_path: str = None):
    """
    Main function that orchestrates the ISS tracking process using JSON.
    
    Can either download from CelesTrak API or load from a local JSON file.
    
    Args:
        use_local_file: If True, load from local file instead of downloading
        json_file_path: Path to local JSON file (optional, defaults to data/iss_tle.json)
    
    Steps:
    1. Load or download TLE data (JSON format)
    2. Parse the JSON data to extract TLE lines
    3. Create Skyfield satellite object from TLE lines
    4. Calculate the current position
    5. Display the result
    """
    try:
        # Step 1: Load or download the JSON TLE data
        if use_local_file:
            print(f"Loading ISS TLE data from local JSON file...")
            if json_file_path:
                print(f"  File: {json_file_path}")
            json_data = load_iss_tle_from_file(json_file_path)
            print("✓ JSON TLE data loaded successfully")
        else:
            print("Downloading ISS TLE data from CelesTrak (JSON format)...")
            json_data = download_iss_tle_json()
            print("✓ JSON TLE data downloaded successfully")
        
        print(f"  Satellite: {json_data.get('OBJECT_NAME', 'Unknown')}")
        print(f"  NORAD ID: {json_data.get('OBJECT_ID', 'Unknown')}")
        print(f"  Epoch: {json_data.get('EPOCH', 'Unknown')}\n")
        
        # Step 2: Parse the JSON data to extract TLE lines
        print("Parsing TLE data from JSON...")
        iss = parse_tle_from_json(json_data)
        print("✓ TLE data parsed successfully\n")
        
        # Step 3: Calculate current position
        print("Calculating current ISS position...")
        position = calculate_iss_position(iss)
        print("✓ Position calculated successfully\n")
        
        # Step 4: Display the result
        print(format_position(position))
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nTo use a local JSON file:")
        print("  1. Place your JSON file in the 'data/' directory")
        print("  2. Name it 'iss_tle.json' or specify the path")
        print("  3. Run: python src/iss_tracker_json.py --local")
    except requests.RequestException as e:
        print(f"❌ Error downloading TLE data: {e}")
        print("Please check your internet connection and try again.")
        print("\nTip: You can use a local JSON file with --local flag")
    except ValueError as e:
        print(f"❌ Error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        print("The JSON file may be corrupted or invalid.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Please check that all dependencies are installed correctly.")


# This allows the script to be run directly
if __name__ == "__main__":
    import sys
    
    # Check for command-line arguments
    use_local = '--local' in sys.argv or '-l' in sys.argv
    
    # Find custom file path if provided
    json_file = None
    for i, arg in enumerate(sys.argv):
        if arg in ['--file', '-f'] and i + 1 < len(sys.argv):
            json_file = sys.argv[i + 1]
            break
    
    main(use_local_file=use_local, json_file_path=json_file)
