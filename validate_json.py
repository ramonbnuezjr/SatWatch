#!/usr/bin/env python3
"""
Quick script to validate the JSON TLE file structure.
"""

import json
from pathlib import Path

def validate_json_file(file_path: str):
    """Validate the JSON file structure."""
    file_path = Path(file_path)
    
    print(f"Validating: {file_path}")
    print(f"File exists: {file_path.exists()}")
    
    if not file_path.exists():
        print("❌ File does not exist!")
        return
    
    # Check file size
    size = file_path.stat().st_size
    print(f"File size: {size} bytes")
    
    if size == 0:
        print("❌ File is empty!")
        return
    
    try:
        # Read and parse JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("✓ Valid JSON format")
        print(f"Data type: {type(data).__name__}")
        
        # Check if it's an array
        if isinstance(data, list):
            print(f"✓ Array with {len(data)} entries")
            
            # Find ISS
            iss_entries = [s for s in data if s.get('NORAD_CAT_ID') == 25544 or 'ISS' in s.get('OBJECT_NAME', '').upper()]
            
            if iss_entries:
                iss = iss_entries[0]
                print(f"\n✓ ISS found: {iss.get('OBJECT_NAME')}")
                print(f"  NORAD ID: {iss.get('NORAD_CAT_ID')}")
                print(f"  OBJECT_ID: {iss.get('OBJECT_ID')}")
                
                # Check for required fields
                print("\nField validation:")
                has_tle1 = 'TLE_LINE1' in iss
                has_tle2 = 'TLE_LINE2' in iss
                has_elements = all(k in iss for k in ['MEAN_MOTION', 'ECCENTRICITY', 'INCLINATION', 
                                                       'RA_OF_ASC_NODE', 'ARG_OF_PERICENTER', 'MEAN_ANOMALY'])
                
                print(f"  TLE_LINE1: {'✓' if has_tle1 else '✗ MISSING'}")
                print(f"  TLE_LINE2: {'✓' if has_tle2 else '✗ MISSING'}")
                print(f"  Orbital elements: {'✓' if has_elements else '✗ MISSING'}")
                
                if not (has_tle1 and has_tle2):
                    print("\n⚠️  WARNING: Missing TLE_LINE1 and TLE_LINE2 fields!")
                    print("   The script needs these fields to work with Skyfield.")
                    print("   You have individual orbital elements, but need TLE lines.")
                    print("\n   Solution options:")
                    print("   1. Get JSON with TLE lines from: https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json")
                    print("   2. Or update the script to construct TLE lines from orbital elements")
                else:
                    print("\n✓ All required fields present!")
                    
            else:
                print("✗ ISS not found in array")
        elif isinstance(data, dict):
            print("✓ Single object format")
            print(f"  OBJECT_NAME: {data.get('OBJECT_NAME', 'N/A')}")
        else:
            print(f"✗ Unexpected format: {type(data)}")
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        print(f"   Error at line {e.lineno}, column {e.colno}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    validate_json_file("data/iss_tle.json")
