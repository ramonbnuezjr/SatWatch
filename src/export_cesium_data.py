#!/usr/bin/env python3
"""
Export Satellite Positions for Cesium Visualization

This script generates time-series position data for satellites using
the existing SatWatch TLE processing infrastructure. The output JSON
is compatible with the Cesium visualization frontend.

Output Format:
{
  "epoch": "2026-01-17T21:00:00Z",
  "satellites": [
    {
      "id": "25544",
      "name": "ISS",
      "type": "station",
      "positions": [
        { "time": "2026-01-17T21:00:00Z", "lat": 14.3, "lon": -96.5, "alt_km": 414 }
      ]
    }
  ]
}

Author: SatWatch Project
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from skyfield.api import load, EarthSatellite
from iss_tracker_json import parse_tle_from_json


def calculate_positions_over_time(
    satellite: EarthSatellite,
    start_time: datetime,
    duration_minutes: int = 90,
    step_seconds: int = 60
) -> List[Dict]:
    """
    Calculate satellite positions over a time period.
    
    Args:
        satellite: Skyfield EarthSatellite object
        start_time: Start datetime (UTC)
        duration_minutes: Duration to propagate in minutes
        step_seconds: Time step between position samples in seconds
        
    Returns:
        list: List of position dictionaries with time, lat, lon, alt_km
    """
    ts = load.timescale()
    positions = []
    
    num_steps = (duration_minutes * 60) // step_seconds + 1
    
    for i in range(num_steps):
        # Calculate time for this step
        current_time = start_time + timedelta(seconds=i * step_seconds)
        skyfield_time = ts.from_datetime(current_time)
        
        try:
            # Calculate position
            geocentric = satellite.at(skyfield_time)
            subpoint = geocentric.subpoint()
            
            lat = subpoint.latitude.degrees
            lon = subpoint.longitude.degrees
            alt_km = subpoint.elevation.km
            
            # Skip if NaN
            if any(map(lambda x: x != x, [lat, lon, alt_km])):  # NaN check
                continue
            
            positions.append({
                'time': current_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'lat': round(lat, 4),
                'lon': round(lon, 4),
                'alt_km': round(alt_km, 1)
            })
            
        except Exception as e:
            # Skip positions that can't be calculated
            print(f"Warning: Could not calculate position at {current_time}: {e}")
            continue
    
    return positions


def export_satellite_data(
    satellites_config: List[Dict],
    tle_data: Dict[int, Dict],
    start_time: datetime,
    duration_minutes: int = 90,
    step_seconds: int = 60,
    output_path: Optional[str] = None
) -> Dict:
    """
    Export satellite position data for Cesium visualization.
    
    Args:
        satellites_config: List of satellite configs with name, catnr, type
        tle_data: Dict mapping catalog numbers to TLE data
        start_time: Start datetime (UTC)
        duration_minutes: Duration to propagate
        step_seconds: Time step between samples
        output_path: Optional path to write JSON output
        
    Returns:
        dict: Position data in Cesium format
    """
    output = {
        'epoch': start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'generated_by': 'SatWatch export_cesium_data.py',
        'duration_minutes': duration_minutes,
        'step_seconds': step_seconds,
        'satellites': []
    }
    
    for sat_config in satellites_config:
        catnr = sat_config['catnr']
        name = sat_config['name']
        sat_type = sat_config['type']
        
        # Get TLE data
        if catnr not in tle_data:
            print(f"Warning: No TLE data for {name} (CATNR: {catnr})")
            continue
        
        tle = tle_data[catnr]
        
        try:
            # Parse TLE into Skyfield satellite
            satellite = parse_tle_from_json(tle)
            
            # Calculate positions
            positions = calculate_positions_over_time(
                satellite,
                start_time,
                duration_minutes,
                step_seconds
            )
            
            if positions:
                output['satellites'].append({
                    'id': str(catnr),
                    'name': name,
                    'type': sat_type,
                    'positions': positions
                })
                print(f"Exported {name}: {len(positions)} positions")
            else:
                print(f"Warning: No valid positions for {name}")
                
        except Exception as e:
            print(f"Error processing {name}: {e}")
            continue
    
    # Write to file if path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        print(f"\nExported to: {output_path}")
    
    return output


def load_satellites_config(config_path: str = None) -> List[Dict]:
    """
    Load satellites configuration from JSON file.
    
    Args:
        config_path: Path to satellites.json (defaults to project root)
        
    Returns:
        list: List of satellite configuration dictionaries
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent
        config_path = project_root / 'satellites.json'
    else:
        config_path = Path(config_path)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config.get('tracked_satellites', [])


def fetch_tle_data(catnr_list: List[int]) -> Dict[int, Dict]:
    """
    Fetch TLE data for satellites from CelesTrak using 3LE format.
    
    The 3LE format provides actual TLE lines which work better with Skyfield.
    
    Args:
        catnr_list: List of NORAD catalog numbers
        
    Returns:
        dict: Mapping of catalog number to TLE data
    """
    import requests
    
    tle_data = {}
    
    for catnr in catnr_list:
        try:
            # Use 3LE format to get actual TLE lines
            url = "https://celestrak.org/NORAD/elements/gp.php"
            params = {'CATNR': catnr, 'FORMAT': '3le'}
            headers = {'User-Agent': 'SatWatch/1.0 (Educational/Research Project)'}
            
            response = requests.get(url, params=params, timeout=10, headers=headers)
            response.raise_for_status()
            
            # Parse 3LE format (three lines: name, TLE line 1, TLE line 2)
            lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
            
            if len(lines) >= 3:
                name_line = lines[0]
                tle_line1 = lines[1]
                tle_line2 = lines[2]
                
                # Validate TLE format
                if tle_line1.startswith('1 ') and tle_line2.startswith('2 '):
                    sat_data = {
                        'OBJECT_NAME': name_line,
                        'TLE_LINE1': tle_line1,
                        'TLE_LINE2': tle_line2,
                        'NORAD_CAT_ID': catnr
                    }
                    tle_data[catnr] = sat_data
                    print(f"Fetched TLE for CATNR {catnr}: {name_line}")
                else:
                    print(f"Warning: Invalid TLE format for CATNR {catnr}")
            else:
                print(f"Warning: Incomplete 3LE data for CATNR {catnr}")
            
        except Exception as e:
            print(f"Warning: Could not fetch TLE for CATNR {catnr}: {e}")
    
    return tle_data


def main():
    """
    Main function to export satellite position data for Cesium.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Export satellite positions for Cesium visualization'
    )
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=90,
        help='Duration in minutes (default: 90)'
    )
    parser.add_argument(
        '-s', '--step',
        type=int,
        default=60,
        help='Step size in seconds (default: 60)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output file path (default: cesium/satellite-positions.json)'
    )
    parser.add_argument(
        '-t', '--time',
        type=str,
        default=None,
        help='Start time in ISO format (default: now)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SatWatch Cesium Data Export")
    print("=" * 60)
    print()
    
    # Load satellites configuration
    print("Loading satellite configuration...")
    satellites_config = load_satellites_config()
    print(f"Found {len(satellites_config)} satellites in config")
    print()
    
    # Fetch TLE data
    print("Fetching TLE data from CelesTrak...")
    catnr_list = [sat['catnr'] for sat in satellites_config]
    tle_data = fetch_tle_data(catnr_list)
    print(f"Fetched TLE data for {len(tle_data)} satellites")
    print()
    
    # Determine start time
    if args.time:
        start_time = datetime.fromisoformat(args.time.replace('Z', '+00:00'))
    else:
        start_time = datetime.now(timezone.utc)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        project_root = Path(__file__).parent.parent
        output_path = project_root / 'cesium' / 'satellite-positions.json'
    
    # Export data
    print(f"Generating positions from {start_time.isoformat()}...")
    print(f"Duration: {args.duration} minutes, Step: {args.step} seconds")
    print()
    
    export_satellite_data(
        satellites_config=satellites_config,
        tle_data=tle_data,
        start_time=start_time,
        duration_minutes=args.duration,
        step_seconds=args.step,
        output_path=output_path
    )
    
    print()
    print("=" * 60)
    print("Export complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
