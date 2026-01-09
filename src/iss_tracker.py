#!/usr/bin/env python3
"""
ISS Position Tracker

This script downloads the current TLE (Two-Line Element) data for the
International Space Station from CelesTrak and calculates its current
position using the Skyfield library.

Author: SatWatch Project
"""

import requests
from skyfield.api import load, EarthSatellite
from datetime import datetime


def download_iss_tle() -> str:
    """
    Download the current TLE data for the ISS from CelesTrak.
    
    The ISS has NORAD ID 25544. CelesTrak provides TLE data in a
    format where each satellite has 3 lines: name, line 1, line 2.
    
    Returns:
        str: The TLE data as a string (3 lines)
        
    Raises:
        requests.RequestException: If the download fails
    """
    # CelesTrak URL for space stations (includes ISS)
    url = "https://celestrak.org/NORAD/elements/stations.txt"
    
    # Download the TLE data
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # Raise an error if download failed
    
    # Get the text content
    tle_data = response.text
    
    # Find the ISS entry (NORAD ID 25544)
    lines = tle_data.strip().split('\n')
    for i, line in enumerate(lines):
        # ISS name line typically contains "ISS" or "INTERNATIONAL SPACE STATION"
        if 'ISS' in line.upper() and i + 2 < len(lines):
            # Return the 3-line TLE entry (name, line1, line2)
            return '\n'.join([lines[i], lines[i+1], lines[i+2]])
    
    # If ISS not found, raise an error
    raise ValueError("ISS TLE data not found in downloaded file")


def parse_tle(tle_string: str) -> EarthSatellite:
    """
    Parse TLE string into a Skyfield EarthSatellite object.
    
    Args:
        tle_string: TLE data as a 3-line string
        
    Returns:
        EarthSatellite: Skyfield satellite object ready for calculations
    """
    # Split the TLE into its 3 lines
    lines = tle_string.strip().split('\n')
    
    # Skyfield expects: name, line1, line2
    name = lines[0].strip()
    line1 = lines[1].strip()
    line2 = lines[2].strip()
    
    # Create the satellite object from TLE data
    satellite = EarthSatellite(line1, line2, name, load.timescale())
    
    return satellite


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


def main():
    """
    Main function that orchestrates the ISS tracking process.
    
    Steps:
    1. Download TLE data from CelesTrak
    2. Parse the TLE data into a Skyfield satellite object
    3. Calculate the current position
    4. Display the result
    """
    try:
        # Step 1: Download the TLE data
        print("Downloading ISS TLE data from CelesTrak...")
        tle_data = download_iss_tle()
        print("✓ TLE data downloaded successfully\n")
        
        # Step 2: Parse the TLE data
        print("Parsing TLE data...")
        iss = parse_tle(tle_data)
        print("✓ TLE data parsed successfully\n")
        
        # Step 3: Calculate current position
        print("Calculating current ISS position...")
        position = calculate_iss_position(iss)
        print("✓ Position calculated successfully\n")
        
        # Step 4: Display the result
        print(format_position(position))
        
    except requests.RequestException as e:
        print(f"❌ Error downloading TLE data: {e}")
        print("Please check your internet connection and try again.")
    except ValueError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Please check that all dependencies are installed correctly.")


# This allows the script to be run directly
if __name__ == "__main__":
    main()

