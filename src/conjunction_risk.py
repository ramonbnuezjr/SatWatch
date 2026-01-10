#!/usr/bin/env python3
"""
Conjunction Risk Calculator

This module provides functions to calculate collision risk (conjunction analysis)
between two satellites using SGP4 propagation.

Author: SatWatch Project
"""

import math
from datetime import datetime, timezone, timedelta
from skyfield.api import load, EarthSatellite
from typing import Dict, Tuple, Optional


def calculate_conjunction_risk(
    sat1_tle: dict, 
    sat2_tle: dict, 
    hours_ahead: int = 48,
    step_minutes: int = 1
) -> Dict:
    """
    Calculate conjunction risk between two satellites.
    
    Propagates both satellites forward in time and calculates the minimum
    distance between them. Flags risk levels based on distance thresholds.
    
    Args:
        sat1_tle: TLE data dictionary for first satellite (must have TLE_LINE1, TLE_LINE2)
        sat2_tle: TLE data dictionary for second satellite (must have TLE_LINE1, TLE_LINE2)
        hours_ahead: Number of hours into the future to analyze (default: 48)
        step_minutes: Time step between calculations in minutes (default: 1)
        
    Returns:
        dict: Dictionary containing:
            - min_distance_km: Minimum distance in kilometers
            - min_distance_time: UTC datetime when minimum distance occurs
            - risk_level: "NORMAL", "HIGH RISK", or "CRITICAL"
            - risk_message: Human-readable risk description
            - sat1_name: Name of first satellite
            - sat2_name: Name of second satellite
            - total_steps: Number of time steps analyzed
            
    Raises:
        ValueError: If TLE data is missing required fields
        Exception: If satellite propagation fails
    """
    from iss_tracker_json import parse_tle_from_json
    
    # Validate TLE data
    for sat_name, sat_data in [("sat1", sat1_tle), ("sat2", sat2_tle)]:
        if 'TLE_LINE1' not in sat_data or 'TLE_LINE2' not in sat_data:
            raise ValueError(
                f"{sat_name} missing TLE_LINE1 or TLE_LINE2. "
                "TLE lines are required for position calculation."
            )
    
    # Parse TLE data into Skyfield satellite objects
    try:
        satellite1 = parse_tle_from_json(sat1_tle)
        satellite2 = parse_tle_from_json(sat2_tle)
    except Exception as e:
        raise ValueError(f"Failed to parse TLE data: {e}") from e
    
    # Get satellite names
    sat1_name = sat1_tle.get('OBJECT_NAME', 'Unknown')
    sat2_name = sat2_tle.get('OBJECT_NAME', 'Unknown')
    
    # Initialize Skyfield timescale
    ts = load.timescale()
    
    # Start from current time
    start_time = datetime.now(timezone.utc)
    skyfield_start = ts.from_datetime(start_time)
    
    # Calculate number of steps
    total_minutes = hours_ahead * 60
    num_steps = total_minutes // step_minutes
    
    # Initialize tracking variables
    min_distance = float('inf')
    min_distance_time = None
    min_distance_pos1 = None
    min_distance_pos2 = None
    
    # Propagate both satellites forward and calculate distances
    for step in range(num_steps + 1):
        # Calculate time for this step
        minutes_forward = step * step_minutes
        current_datetime = start_time + timedelta(minutes=minutes_forward)
        skyfield_time = ts.from_datetime(current_datetime)
        
        try:
            # Get positions of both satellites at this time
            pos1 = satellite1.at(skyfield_time)
            pos2 = satellite2.at(skyfield_time)
            
            # Calculate 3D distance between satellites
            # Skyfield positions are in AU (astronomical units), convert to km
            # 1 AU = 149,597,870.7 km
            distance_vector = pos2 - pos1
            distance_au = distance_vector.distance().au
            distance_km = distance_au * 149597870.7
            
            # Track minimum distance
            if distance_km < min_distance:
                min_distance = distance_km
                min_distance_time = current_datetime
                min_distance_pos1 = pos1
                min_distance_pos2 = pos2
                
        except Exception as e:
            # If propagation fails at a specific time, continue to next step
            # This can happen if TLE data is invalid for that time period
            continue
    
    # Determine risk level
    if min_distance < 1.0:
        risk_level = "CRITICAL"
        risk_message = (
            f"CRITICAL: Satellites will be {min_distance:.3f} km apart "
            f"at {min_distance_time.strftime('%Y-%m-%d %H:%M:%S UTC')}. "
            f"Immediate action required!"
        )
    elif min_distance < 5.0:
        risk_level = "HIGH RISK"
        risk_message = (
            f"HIGH RISK: Satellites will be {min_distance:.3f} km apart "
            f"at {min_distance_time.strftime('%Y-%m-%d %H:%M:%S UTC')}. "
            f"Close approach detected - monitoring recommended."
        )
    else:
        risk_level = "NORMAL"
        risk_message = (
            f"NORMAL: Minimum distance of {min_distance:.3f} km "
            f"at {min_distance_time.strftime('%Y-%m-%d %H:%M:%S UTC')}. "
            f"No immediate risk detected."
        )
    
    # Build result dictionary
    result = {
        'min_distance_km': round(min_distance, 3),
        'min_distance_time': min_distance_time,
        'risk_level': risk_level,
        'risk_message': risk_message,
        'sat1_name': sat1_name,
        'sat2_name': sat2_name,
        'total_steps': num_steps + 1,
        'analysis_period_hours': hours_ahead,
        'step_size_minutes': step_minutes
    }
    
    # Add position information at closest approach if available
    if min_distance_pos1 is not None and min_distance_pos2 is not None:
        try:
            # Get subpoints (lat/lon/alt) for both satellites at closest approach
            subpoint1 = min_distance_pos1.subpoint()
            subpoint2 = min_distance_pos2.subpoint()
            
            result['sat1_position_at_closest'] = {
                'latitude': round(subpoint1.latitude.degrees, 4),
                'longitude': round(subpoint1.longitude.degrees, 4),
                'altitude_km': round(subpoint1.elevation.km, 2)
            }
            
            result['sat2_position_at_closest'] = {
                'latitude': round(subpoint2.latitude.degrees, 4),
                'longitude': round(subpoint2.longitude.degrees, 4),
                'altitude_km': round(subpoint2.elevation.km, 2)
            }
        except Exception:
            # If position calculation fails, continue without it
            pass
    
    return result


def format_conjunction_report(result: Dict) -> str:
    """
    Format conjunction risk result as a human-readable report.
    
    Args:
        result: Dictionary returned by calculate_conjunction_risk()
        
    Returns:
        str: Formatted report string
    """
    lines = []
    lines.append("=" * 70)
    lines.append("CONJUNCTION RISK ANALYSIS")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Satellite 1: {result['sat1_name']}")
    lines.append(f"Satellite 2: {result['sat2_name']}")
    lines.append("")
    lines.append(f"Analysis Period: {result['analysis_period_hours']} hours")
    lines.append(f"Time Steps: {result['total_steps']} steps ({result['step_size_minutes']} min intervals)")
    lines.append("")
    lines.append("-" * 70)
    lines.append(f"RISK LEVEL: {result['risk_level']}")
    lines.append("-" * 70)
    lines.append("")
    lines.append(result['risk_message'])
    lines.append("")
    lines.append(f"Minimum Distance: {result['min_distance_km']:.3f} km")
    lines.append(f"Time of Closest Approach: {result['min_distance_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")
    
    # Add position information if available
    if 'sat1_position_at_closest' in result:
        lines.append("Position at Closest Approach:")
        lines.append(f"  {result['sat1_name']}:")
        pos1 = result['sat1_position_at_closest']
        lines.append(f"    Lat: {pos1['latitude']:.4f}°, Lon: {pos1['longitude']:.4f}°, Alt: {pos1['altitude_km']:.2f} km")
        
        if 'sat2_position_at_closest' in result:
            lines.append(f"  {result['sat2_name']}:")
            pos2 = result['sat2_position_at_closest']
            lines.append(f"    Lat: {pos2['latitude']:.4f}°, Lon: {pos2['longitude']:.4f}°, Alt: {pos2['altitude_km']:.2f} km")
        lines.append("")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


if __name__ == "__main__":
    """
    Example usage of conjunction risk calculator.
    """
    import sys
    from pathlib import Path
    
    # Add src directory to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    from iss_tracker_json import load_iss_tle_from_file, download_iss_tle_json
    
    print("Conjunction Risk Calculator - Example")
    print("=" * 70)
    print()
    
    # Example: Compare ISS with itself (should show 0 km distance)
    # In practice, you'd compare two different satellites
    try:
        print("Loading ISS TLE data...")
        iss_tle = load_iss_tle_from_file()
        print(f"✓ Loaded: {iss_tle.get('OBJECT_NAME', 'Unknown')}")
        print()
        
        # For demonstration, compare ISS with itself
        # (In real usage, you'd load two different satellites)
        print("Calculating conjunction risk...")
        print("(Note: Comparing ISS with itself for demonstration)")
        print()
        
        result = calculate_conjunction_risk(iss_tle, iss_tle, hours_ahead=48)
        
        print(format_conjunction_report(result))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
