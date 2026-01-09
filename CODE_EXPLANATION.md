# ISS Tracker Code Explanation

This document explains every line of code in `src/iss_tracker.py` for beginners.

**Note**: There are two versions of the ISS tracker:
- `src/iss_tracker.py` - Uses text format TLE from CelesTrak
- `src/iss_tracker_json.py` - Uses JSON format (supports both API and local files)

This document explains the text format version. For JSON format details, see [JSON_APPROACH_EXPLANATION.md](JSON_APPROACH_EXPLANATION.md).

## Installation Commands

Before running the script, install the required packages:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install skyfield requests numpy
```

## Line-by-Line Code Explanation

### Imports (Lines 12-14)

```python
import requests
from skyfield.api import load, EarthSatellite
from datetime import datetime
```

**What this does:**
- `requests`: Library for making HTTP requests to download TLE data from the internet
- `skyfield.api`: The Skyfield library for astronomical calculations
  - `load`: Used to load time scales and TLE data
  - `EarthSatellite`: A class that represents a satellite orbiting Earth
- `datetime`: For working with dates and times (currently imported but not used in this script - reserved for future features like historical tracking or time-based queries)

---

### Function: `download_iss_tle()` (Lines 17-49)

```python
def download_iss_tle() -> str:
```

**Purpose:** Downloads the current TLE data for the ISS from CelesTrak.

**Line-by-line breakdown:**

```python
url = "https://celestrak.org/NORAD/elements/stations.txt"
```
- Sets the URL where we'll download TLE data
- CelesTrak is a trusted source for satellite orbital data
- This file contains TLE data for space stations (including the ISS)

```python
response = requests.get(url, timeout=10)
```
- Makes an HTTP GET request to download the file
- `timeout=10` means if it takes longer than 10 seconds, give up
- `response` contains the downloaded data

```python
response.raise_for_status()
```
- Checks if the download was successful
- If the server returned an error (like 404 or 500), this raises an exception
- This prevents us from trying to use bad data

```python
tle_data = response.text
```
- Extracts the text content from the response
- TLE files are plain text files

```python
lines = tle_data.strip().split('\n')
```
- `strip()` removes extra whitespace from the beginning and end
- `split('\n')` splits the text into individual lines
- `lines` is now a list where each element is one line of the file

```python
for i, line in enumerate(lines):
```
- Loops through each line in the file
- `enumerate()` gives us both the line number (`i`) and the line content (`line`)

```python
if 'ISS' in line.upper() and i + 2 < len(lines):
```
- `line.upper()` converts the line to uppercase (so "iss" or "ISS" both work)
- Checks if "ISS" appears in the line (this is the satellite name)
- `i + 2 < len(lines)` ensures we have at least 2 more lines after this one (TLE needs 3 lines total)

```python
return '\n'.join([lines[i], lines[i+1], lines[i+2]])
```
- If we found the ISS, return all 3 lines (name, line 1, line 2)
- `'\n'.join()` puts the lines back together with newlines between them

```python
raise ValueError("ISS TLE data not found in downloaded file")
```
- If we looped through the entire file and didn't find ISS, raise an error
- This prevents the program from continuing with invalid data

---

### Function: `parse_tle()` (Lines 52-73)

```python
def parse_tle(tle_string: str) -> EarthSatellite:
```

**Purpose:** Converts the TLE string into a Skyfield satellite object that can calculate positions.

**Line-by-line breakdown:**

```python
lines = tle_string.strip().split('\n')
```
- Splits the TLE string into 3 separate lines

```python
name = lines[0].strip()
line1 = lines[1].strip()
line2 = lines[2].strip()
```
- Extracts each line:
  - `name`: The satellite name (e.g., "ISS (ZARYA)")
  - `line1`: First line of orbital elements
  - `line2`: Second line of orbital elements
- `.strip()` removes any extra spaces

```python
satellite = EarthSatellite(line1, line2, name, load.timescale())
```
- Creates a Skyfield `EarthSatellite` object
- This object knows how to calculate the satellite's position at any time
- `load.timescale()` creates a time scale object (needed for time calculations)

```python
return satellite
```
- Returns the satellite object so we can use it later

---

### Function: `calculate_iss_position()` (Lines 76-110)

```python
def calculate_iss_position(satellite: EarthSatellite) -> dict:
```

**Purpose:** Calculates where the ISS is right now (latitude, longitude, altitude).

**Line-by-line breakdown:**

```python
ts = load.timescale()
```
- Creates a timescale object
- Skyfield needs this to work with dates and times accurately

```python
current_time = ts.now()
```
- Gets the current time
- This is a Skyfield Time object, not a regular Python datetime

```python
geocentric = satellite.at(current_time)
```
- Calculates the satellite's position in 3D space at the current time
- "Geocentric" means relative to Earth's center
- This gives us X, Y, Z coordinates in space

```python
subpoint = geocentric.subpoint()
```
- Converts the 3D position to a point on Earth's surface
- "Subpoint" is the point directly below the satellite
- This gives us latitude, longitude, and altitude

```python
latitude = subpoint.latitude.degrees
longitude = subpoint.longitude.degrees
altitude = subpoint.elevation.km
```
- Extracts the values we want:
  - `latitude`: How far north/south (-90° to +90°)
  - `longitude`: How far east/west (-180° to +180°)
  - `altitude`: Height above sea level in kilometers

```python
return {
    'latitude': latitude,
    'longitude': longitude,
    'altitude': altitude,
    'timestamp': current_time.utc_strftime('%Y-%m-%d %H:%M:%S UTC')
}
```
- Returns a dictionary with all the position data
- The timestamp is formatted as a readable string (e.g., "2024-05-15 14:30:45 UTC")

---

### Function: `format_position()` (Lines 113-135)

```python
def format_position(position: dict) -> str:
```

**Purpose:** Makes the position data look nice when printed.

**Line-by-line breakdown:**

```python
output = f"""
╔═══════════════════════════════════════════════════════════╗
║              INTERNATIONAL SPACE STATION (ISS)            ║
...
```
- Creates a formatted string with box-drawing characters
- `f"""..."""` is an f-string (formatted string) that allows variables inside
- The box characters (╔, ║, ╚) create a nice border

```python
║  Time:        {position['timestamp']:<45}  ║
```
- `{position['timestamp']:<45}` inserts the timestamp
- `:<45` means left-align and pad to 45 characters wide

```python
║  Latitude:    {position['latitude']:>8.4f}°{'':<38}  ║
```
- `{position['latitude']:>8.4f}` formats the latitude:
  - `>8` means right-align in 8 characters
  - `.4f` means show 4 decimal places
  - The `°` symbol is the degree symbol
- `{'':<38}` adds empty space to fill the line

---

### Function: `main()` (Lines 138-174)

```python
def main():
```

**Purpose:** The main function that runs the entire process.

**Line-by-line breakdown:**

```python
try:
```
- Starts a try-except block to catch errors gracefully

```python
print("Downloading ISS TLE data from CelesTrak...")
tle_data = download_iss_tle()
print("✓ TLE data downloaded successfully\n")
```
- Step 1: Download the TLE data
- Prints progress messages so the user knows what's happening
- `\n` adds a blank line

```python
print("Parsing TLE data...")
iss = parse_tle(tle_data)
print("✓ TLE data parsed successfully\n")
```
- Step 2: Convert the TLE string into a satellite object

```python
print("Calculating current ISS position...")
position = calculate_iss_position(iss)
print("✓ Position calculated successfully\n")
```
- Step 3: Calculate where the ISS is right now

```python
print(format_position(position))
```
- Step 4: Display the formatted result

```python
except requests.RequestException as e:
    print(f"❌ Error downloading TLE data: {e}")
```
- Catches errors from the `requests` library (network problems)
- `f"..."` is an f-string that includes the error message

```python
except ValueError as e:
    print(f"❌ Error: {e}")
```
- Catches errors when ISS data isn't found

```python
except Exception as e:
    print(f"❌ Unexpected error: {e}")
```
- Catches any other unexpected errors
- This is a safety net

---

### Script Entry Point (Lines 178-179)

```python
if __name__ == "__main__":
    main()
```

**What this does:**
- `__name__` is a special Python variable
- When you run the script directly, `__name__` equals `"__main__"`
- This means: "Only run `main()` if someone is running this file directly"
- This allows the file to be imported as a module without automatically running the code

---

## How to Run the Script

1. **Open your terminal** (Terminal on Mac, Command Prompt or PowerShell on Windows)

2. **Navigate to the project directory:**
   ```bash
   cd "/Users/ramonbnuezjr/AI Projects/satwatch"
   ```

3. **Install dependencies** (if you haven't already):
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the script:**
   ```bash
   python src/iss_tracker.py
   ```

   Or on some systems:
   ```bash
   python3 src/iss_tracker.py
   ```

5. **Expected output:**
   ```
   Downloading ISS TLE data from CelesTrak...
   ✓ TLE data downloaded successfully

   Parsing TLE data...
   ✓ TLE data parsed successfully

   Calculating current ISS position...
   ✓ Position calculated successfully

   ╔═══════════════════════════════════════════════════════════╗
   ║              INTERNATIONAL SPACE STATION (ISS)            ║
   ║                    Current Position                        ║
   ╠═══════════════════════════════════════════════════════════╣
   ║  Time:        2024-05-15 14:30:45 UTC                     ║
   ║  Latitude:     51.6442°                                    ║
   ║  Longitude:   -0.1234°                                     ║
   ║  Altitude:   408.50 km                                     ║
   ╚═══════════════════════════════════════════════════════════╝
   ```

## Troubleshooting

**Error: "ModuleNotFoundError: No module named 'requests'"**
- Solution: Run `pip install -r requirements.txt`

**Error: "Connection timeout" or network errors**
- Solution: Check your internet connection and try again

**Error: "ISS TLE data not found"**
- Solution: The CelesTrak file format may have changed. Check the URL is still valid.

**Error: "Permission denied"**
- Solution: Make sure you have write permissions in the directory, or run with appropriate permissions.

## Key Concepts Explained

### TLE (Two-Line Element) Format
- A standard format for describing satellite orbits
- Contains orbital parameters that allow calculation of position at any time
- Updated regularly (every few days) as orbits change slightly

### Skyfield Library
- A Python library for astronomical calculations
- Can calculate positions of planets, stars, and satellites
- Uses precise mathematical models of orbital mechanics

### Geographic Coordinates
- **Latitude**: Distance north/south of the equator (-90° to +90°)
- **Longitude**: Distance east/west of the Prime Meridian (-180° to +180°)
- **Altitude**: Height above sea level (in kilometers for satellites)

