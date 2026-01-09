# Data Directory

This directory stores JSON TLE (Two-Line Element) data files for satellites.

## File Location

Place your JSON TLE files here. The default filename is `iss_tle.json`.

## JSON File Format

Your JSON file should contain ISS TLE data. The script supports two formats:

### Format 1: Array of Objects (Current Format)
This is what CelesTrak provides and what we're using:

```json
[
  {
    "OBJECT_NAME": "ISS (ZARYA)",
    "OBJECT_ID": "1998-067A",
    "NORAD_CAT_ID": 25544,
    "EPOCH": "2026-01-08T12:00:03.881088",
    "TLE_LINE1": "1 25544U 98067A   26008.50004492  .00009772  00000+0  18407-3 0  9997",
    "TLE_LINE2": "2 25544  51.6332   9.9851 0007637 355.2000   4.8914 15.49175445547009",
    "MEAN_MOTION": 15.49175445,
    "ECCENTRICITY": 0.0007637,
    "INCLINATION": 51.6332,
    "RA_OF_ASC_NODE": 9.9851,
    "ARG_OF_PERICENTER": 355.2,
    "MEAN_ANOMALY": 4.8914,
    "BSTAR": 0.00018407097,
    "MEAN_MOTION_DOT": 9.772e-5,
    "MEAN_MOTION_DDOT": 0,
    "ELEMENT_SET_NO": 999,
    "REV_AT_EPOCH": 54700,
    "CLASSIFICATION_TYPE": "U"
  }
]
```

### Format 2: Single Object
Also supported:

```json
{
  "OBJECT_NAME": "ISS (ZARYA)",
  "NORAD_CAT_ID": 25544,
  "TLE_LINE1": "1 25544U 98067A...",
  "TLE_LINE2": "2 25544  51.6332..."
}
```

### Important: Both Formats Needed

**Required for Skyfield**:
- `TLE_LINE1`: First line of TLE data (must start with "1 ")
- `TLE_LINE2`: Second line of TLE data (must start with "2 ")

**Optional but Recommended**:
- Individual orbital elements (for reference and fallback)
- If TLE lines are missing, script will construct them from elements

## Required Fields

- `TLE_LINE1`: First line of TLE data (must start with "1 ")
- `TLE_LINE2`: Second line of TLE data (must start with "2 ")
- `OBJECT_NAME`: Satellite name (should contain "ISS" for ISS data)
- `OBJECT_ID`: NORAD catalog ID (should be "25544" for ISS)

## Usage

### Using Default File (data/iss_tle.json)
```bash
python src/iss_tracker_json.py --local
```

### Using Custom File Path
```bash
python src/iss_tracker_json.py --local --file data/my_iss_data.json
```

Or with short flags:
```bash
python src/iss_tracker_json.py -l -f data/my_iss_data.json
```

## Getting JSON Data

You can download JSON TLE data from CelesTrak:

1. **Via API**: The script downloads automatically when run without `--local`
2. **Manual Download**: Visit https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json
3. **Save the file**: Save as `data/iss_tle.json` or your preferred filename

## Notes

- TLE data expires after ~2 weeks, so update your JSON file regularly
- The script will automatically find the ISS entry by NORAD ID (25544) or name
- If you have multiple satellites in an array, the script will find the ISS entry

## Current File Status

Your `iss_tle.json` file currently contains:
- ✅ TLE_LINE1 and TLE_LINE2 (required for Skyfield)
- ✅ All orbital elements (for reference)
- ✅ 16 satellite entries (ISS + other objects)
- ✅ Properly formatted JSON
- ✅ **TESTED AND WORKING** - Successfully used to calculate ISS position

**Validation**: Run `python validate_json.py` to check your file structure.

**Test Results** (January 2025):
- ✅ File loads successfully
- ✅ ISS entry found correctly
- ✅ TLE lines parsed correctly
- ✅ Position calculated accurately
- ✅ Output formatted correctly

## Challenges We Overcame

1. **Initial Issue**: JSON had orbital elements but not TLE lines
   - **Solution**: Added TLE lines manually from CelesTrak
   - **Better Solution**: Script now constructs TLE lines if missing

2. **Format Confusion**: Understanding why TLE lines are needed
   - **Explanation**: Skyfield requires TLE format for SGP4 propagation
   - **Best Practice**: Include both TLE lines and elements in JSON

See [PROJECT_STATUS.md](../PROJECT_STATUS.md) for more details on challenges and solutions.
