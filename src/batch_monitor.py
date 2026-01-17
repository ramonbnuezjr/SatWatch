#!/usr/bin/env python3
"""
Batch Conjunction Monitor

Monitors all tracked satellites for conjunction risks by checking every pair.
This is Phase 1 of the alerting system - automated risk detection.

Author: SatWatch Project
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict
from conjunction_risk import calculate_conjunction_risk


def load_tracked_satellites() -> List[Dict]:
    """
    Load tracked satellites from satellites.json configuration.
    
    Returns:
        list: List of satellite configuration dictionaries
    """
    import json
    from pathlib import Path
    
    # Load satellites.json directly to avoid Streamlit dependencies
    project_root = Path(__file__).parent.parent
    config_file = project_root / 'satellites.json'
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('tracked_satellites', [])
    except FileNotFoundError:
        print("Error: satellites.json not found")
        return []
    except Exception as e:
        print(f"Error loading satellites config: {e}")
        return []


def fetch_all_satellite_tles(tracked_satellites: List[Dict]) -> Dict[int, Dict]:
    """
    Fetch TLE data for all tracked satellites.
    
    Args:
        tracked_satellites: List of satellite config dicts with 'catnr'
        
    Returns:
        dict: Mapping of catalog number to TLE data dictionary
    """
    import requests
    
    if not tracked_satellites:
        return {}
    
    satellites_tle_data = {}
    catnr_list = [sat['catnr'] for sat in tracked_satellites]
    
    # Fetch each satellite individually (standalone version, no Streamlit)
    for catnr in catnr_list:
        try:
            url = "https://celestrak.org/NORAD/elements/gp.php"
            params = {
                'CATNR': catnr,
                'FORMAT': '3le'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            if not response.text or not response.text.strip():
                print(f"⚠️  No data returned for satellite {catnr}")
                continue
            
            # Parse 3LE format (three lines: name, line1, line2)
            lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
            
            if len(lines) < 3:
                print(f"⚠️  Invalid 3LE format for satellite {catnr}: Expected 3 lines, got {len(lines)}")
                continue
            
            name_line = lines[0]
            tle_line1 = lines[1]
            tle_line2 = lines[2]
            
            # Validate TLE line format
            if not tle_line1.startswith('1 ') or not tle_line2.startswith('2 '):
                print(f"⚠️  Invalid TLE format for satellite {catnr}")
                continue
            
            # Extract catalog number from TLE line 1
            try:
                norad_cat_id = int(tle_line1[2:7].strip())
            except (ValueError, IndexError):
                print(f"⚠️  Could not extract catalog number for satellite {catnr}")
                continue
            
            # Create satellite data dictionary
            satellite_data = {
                'OBJECT_NAME': name_line,
                'TLE_LINE1': tle_line1,
                'TLE_LINE2': tle_line2,
                'NORAD_CAT_ID': str(norad_cat_id),
                'OBJECT_ID': str(norad_cat_id)
            }
            
            satellites_tle_data[catnr] = satellite_data
                
        except requests.RequestException as e:
            print(f"⚠️  Failed to fetch satellite {catnr}: {e}")
            continue
        except Exception as e:
            print(f"⚠️  Unexpected error fetching satellite {catnr}: {e}")
            continue
    
    return satellites_tle_data


def monitor_all_pairs(
    tracked_satellites: List[Dict],
    satellites_tle_data: Dict[int, Dict],
    hours_ahead: int = 48,
    min_risk_level: str = "NORMAL"
) -> List[Dict]:
    """
    Monitor all satellite pairs for conjunction risks.
    
    Checks every unique pair of satellites and runs conjunction analysis.
    Only returns results that meet or exceed the minimum risk level.
    
    Args:
        tracked_satellites: List of satellite config dicts
        satellites_tle_data: Dict mapping catalog numbers to TLE data
        hours_ahead: Hours into future to analyze (default: 48)
        min_risk_level: Minimum risk level to report ("NORMAL", "HIGH RISK", "CRITICAL")
        
    Returns:
        list: List of conjunction risk results (only risks meeting threshold)
    """
    risk_levels = {"NORMAL": 0, "HIGH RISK": 1, "CRITICAL": 2}
    min_level = risk_levels.get(min_risk_level, 0)
    
    results = []
    total_pairs = 0
    
    # Check every unique pair (avoid duplicates: A-B is same as B-A)
    for i, sat1_config in enumerate(tracked_satellites):
        catnr1 = sat1_config['catnr']
        sat1_tle = satellites_tle_data.get(catnr1)
        
        if not sat1_tle:
            print(f"⚠️  Skipping {sat1_config['name']} - no TLE data")
            continue
        
        # Only check pairs we haven't checked yet (i+1 to avoid duplicates)
        for j, sat2_config in enumerate(tracked_satellites[i+1:], start=i+1):
            catnr2 = sat2_config['catnr']
            sat2_tle = satellites_tle_data.get(catnr2)
            
            if not sat2_tle:
                continue
            
            total_pairs += 1
            
            try:
                # Calculate conjunction risk
                result = calculate_conjunction_risk(
                    sat1_tle, 
                    sat2_tle, 
                    hours_ahead=hours_ahead
                )
                
                # Check if risk level meets threshold
                result_level = risk_levels.get(result['risk_level'], 0)
                if result_level >= min_level:
                    results.append(result)
                    
            except Exception as e:
                print(f"⚠️  Error checking {sat1_config['name']} vs {sat2_config['name']}: {e}")
                continue
    
    print(f"✓ Checked {total_pairs} satellite pairs")
    return results


def save_results(results: List[Dict], output_file: str = None) -> Path:
    """
    Save monitoring results to JSON file.
    
    Args:
        results: List of conjunction risk results
        output_file: Path to output file (default: data/conjunction_results.json)
        
    Returns:
        Path: Path to saved file
    """
    if output_file is None:
        project_root = Path(__file__).parent.parent
        output_file = project_root / 'data' / 'conjunction_results.json'
    else:
        output_file = Path(output_file)
    
    # Ensure data directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare output data
    output_data = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_risks': len(results),
        'results': results
    }
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
    
    return output_file


def format_batch_report(results: List[Dict]) -> str:
    """
    Format batch monitoring results as a human-readable report.
    
    Args:
        results: List of conjunction risk results
        
    Returns:
        str: Formatted report
    """
    if not results:
        return "✓ No conjunction risks detected in the analysis period."
    
    lines = []
    lines.append("=" * 70)
    lines.append("BATCH CONJUNCTION MONITORING REPORT")
    lines.append("=" * 70)
    lines.append(f"Analysis Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"Total Risks Detected: {len(results)}")
    lines.append("")
    
    # Group by risk level
    critical = [r for r in results if r['risk_level'] == 'CRITICAL']
    high_risk = [r for r in results if r['risk_level'] == 'HIGH RISK']
    normal = [r for r in results if r['risk_level'] == 'NORMAL']
    
    if critical:
        lines.append("🚨 CRITICAL RISKS (Distance < 1 km)")
        lines.append("-" * 70)
        for result in critical:
            lines.append(f"  {result['sat1_name']} ↔ {result['sat2_name']}")
            lines.append(f"    Distance: {result['min_distance_km']:.3f} km")
            lines.append(f"    Time: {result['min_distance_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
            lines.append("")
    
    if high_risk:
        lines.append("⚠️  HIGH RISK (Distance < 5 km)")
        lines.append("-" * 70)
        for result in high_risk:
            lines.append(f"  {result['sat1_name']} ↔ {result['sat2_name']}")
            lines.append(f"    Distance: {result['min_distance_km']:.3f} km")
            lines.append(f"    Time: {result['min_distance_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
            lines.append("")
    
    if normal:
        lines.append("ℹ️  NORMAL RISKS (Distance ≥ 5 km)")
        lines.append("-" * 70)
        for result in normal[:10]:  # Show first 10 normal risks
            lines.append(f"  {result['sat1_name']} ↔ {result['sat2_name']}: {result['min_distance_km']:.3f} km")
        if len(normal) > 10:
            lines.append(f"  ... and {len(normal) - 10} more")
        lines.append("")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


def main():
    """
    Main function to run batch conjunction monitoring.
    """
    print("SatWatch Batch Conjunction Monitor")
    print("=" * 70)
    print()
    
    # Load tracked satellites
    print("Loading tracked satellites...")
    tracked_satellites = load_tracked_satellites()
    
    if not tracked_satellites:
        print("❌ No satellites configured. Add satellites to satellites.json")
        return
    
    print(f"✓ Found {len(tracked_satellites)} tracked satellites:")
    for sat in tracked_satellites:
        print(f"  - {sat['name']} (CATNR: {sat['catnr']}, Type: {sat['type']})")
    print()
    
    # Fetch TLE data
    print("Fetching TLE data from CelesTrak...")
    satellites_tle_data = fetch_all_satellite_tles(tracked_satellites)
    
    if not satellites_tle_data:
        print("❌ Failed to fetch TLE data for any satellites")
        return
    
    print(f"✓ Fetched TLE data for {len(satellites_tle_data)} satellites")
    print()
    
    # Monitor all pairs
    print("Monitoring all satellite pairs for conjunction risks...")
    print("(This may take a few minutes...)")
    print()
    
    results = monitor_all_pairs(
        tracked_satellites,
        satellites_tle_data,
        hours_ahead=48,
        min_risk_level="NORMAL"  # Report all risks
    )
    
    print()
    
    # Display results
    print(format_batch_report(results))
    
    # Save results
    if results:
        output_file = save_results(results)
        print(f"✓ Results saved to: {output_file}")
    else:
        print("✓ No risks detected - no results file created")


if __name__ == "__main__":
    main()
