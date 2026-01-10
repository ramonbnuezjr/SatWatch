# Error Resolution Log - Multi-Satellite Tracking

This document provides a detailed log of all errors encountered during the multi-satellite tracking implementation and all attempts to resolve them.

**Date**: January 2025  
**Feature**: Multi-Satellite Tracking Implementation

---

## Error Summary

| Error # | Error Type | Status | Resolution |
|---------|-----------|--------|------------|
| 1 | API Fetch Empty Response | ⚠️ Partial | Added empty response check, improved error handling |
| 2 | Catalog Number Extraction | ✅ Resolved | Fixed to use NORAD_CAT_ID first, fallback to TLE extraction |
| 3 | NaN Position Calculations | ✅ Resolved | Changed API format from JSON to 3LE format |
| 4 | Variable Scope Error | ✅ Resolved | Fixed variable scope in debug section |
| 5 | Satellites Not Showing | ✅ Resolved | Fixed by resolving Issue 3 (3LE format provides TLE lines) |
| 6 | Streamlit Server Connection Failed | ✅ Resolved | Documented troubleshooting steps, restart procedures |
| 7 | NaN Values Causing Map Crash | ✅ Resolved | Added NaN validation before map/plot creation, error messages |
| 8 | Indentation Errors in Dashboard | ✅ Resolved | Fixed indentation in debug expander and else blocks |
| 9 | Missing TLE Lines in Local File | ✅ Resolved | Updated local file with 3LE format data, added TLE lines to JSON |

---

## Detailed Error Log

### Error 1: API Fetch Empty Response

**Error Message**:
```
Failed to fetch satellite 44713: Network error - Expecting value: line 1 column 1 (char 0)
Failed to fetch satellite 49863: Network error - Expecting value: line 1 column 1 (char 0)
```

**When It Occurred**: During initial multi-satellite tracking implementation

**Root Cause**:
- CelesTrak API returns empty responses for satellites that:
  - Are no longer in active database (decayed/deorbited)
  - Have incorrect catalog numbers
  - Are not publicly available
- Empty responses cause JSON parsing errors (`json.decoder.JSONDecodeError`)

**Resolution Attempts**:

1. **Attempt 1**: Added empty response check
   ```python
   if not response.text or not response.text.strip():
       st.warning(f"No data returned for satellite {catnr}")
       continue
   ```
   - **Result**: ✅ Prevents crash, but satellite still not loaded

2. **Attempt 2**: Improved error handling with better messages
   ```python
   except json.JSONDecodeError:
       st.warning(f"Invalid JSON response for satellite {catnr}")
       continue
   ```
   - **Result**: ✅ Better user feedback

3. **Attempt 3**: Updated catalog numbers to known working ones
   - Changed from: Starlink-1007 (44713), Cosmos 1408 Debris (49863)
   - Changed to: Hubble Space Telescope (20580), Tiangong Space Station (48274)
   - **Result**: ✅ Hubble and Tiangong load successfully

**Current Status**: ⚠️ **Partially Resolved**
- Error handling prevents crashes
- Some catalog numbers may not be available in database
- Need to validate catalog numbers before use

**Recommendation**: Use CelesTrak's group endpoints (e.g., `GROUP=stations`) for more reliable data

---

### Error 2: Catalog Number Extraction

**Error Message**:
```
ValueError: invalid literal for int() with base 10: '1998-067A'
Traceback:
File "/Users/ramonbnuezjr/AI Projects/satwatch/src/dashboard.py", line 981, in <module>
    catnr = int(sat_data.get('OBJECT_ID', 0))
```

**When It Occurred**: When processing fetched satellite data

**Root Cause**:
- CelesTrak JSON API uses `OBJECT_ID` field for international designator (e.g., '1998-067A')
- `NORAD_CAT_ID` field contains the numeric catalog number (e.g., 25544)
- Code was trying to convert international designator to int, causing crash

**Resolution Attempts**:

1. **Attempt 1**: Check `NORAD_CAT_ID` first
   ```python
   if 'NORAD_CAT_ID' in sat_data:
       catnr = int(sat_data['NORAD_CAT_ID'])
   ```
   - **Result**: ✅ Works for satellites with NORAD_CAT_ID field

2. **Attempt 2**: Fallback to TLE line extraction
   ```python
   elif 'TLE_LINE1' in sat_data:
       catnr = int(sat_data['TLE_LINE1'][2:7].strip())
   ```
   - **Result**: ✅ Works when NORAD_CAT_ID missing but TLE lines present

3. **Attempt 3**: Handle both formats gracefully
   - Check NORAD_CAT_ID first (preferred)
   - Try OBJECT_ID if numeric
   - Extract from TLE_LINE1 if needed
   - Skip with warning if none work
   - **Result**: ✅ Comprehensive solution

**Current Status**: ✅ **Resolved**
- Code now handles both field formats correctly
- No crashes on international designators
- Clear warnings when catalog number cannot be determined

---

### Error 3: NaN Position Calculations

**Error Message**:
```
Position: (nan, nan, nan) km
Altitude: nan km
Distance from ISS: nan km
```

**When It Occurred**: When calculating positions for tracked satellites, and later when using local TLE file

**Root Cause**:
- **Primary Issue**: CelesTrak JSON API response (`FORMAT=json`) does not include `TLE_LINE1` and `TLE_LINE2` fields
- **Secondary Issue**: Local TLE file (`data/iss_tle.json`) was missing TLE lines after updating via JSON API
- Skyfield requires TLE lines (not just orbital elements) to calculate positions
- Without TLE lines, position calculations fail, resulting in NaN values
- The JSON format only includes individual orbital elements, not the formatted TLE lines

**Resolution Attempts**:

1. **Attempt 1**: Added NaN checks
   ```python
   if math.isnan(lat) or math.isnan(lon) or math.isnan(alt):
       st.warning(f"Position calculation returned NaN for {sat_name}")
       continue
   ```
   - **Result**: ✅ Prevents NaN from propagating, but doesn't fix root cause

2. **Attempt 2**: Enhanced error handling with tracebacks
   ```python
   except Exception as e:
       st.error(f"Error calculating position: {e}")
       import traceback
       st.code(traceback.format_exc())
   ```
   - **Result**: ✅ Better error visibility

3. **Attempt 3**: Field validation before parsing
   ```python
   if 'TLE_LINE1' not in sat_tle or 'TLE_LINE2' not in sat_tle:
       st.error(f"Missing TLE_LINE1 or TLE_LINE2 in TLE data")
       st.write(f"Available fields: {list(sat_tle.keys())}")
   ```
   - **Result**: ✅ Identified missing TLE fields

4. **Attempt 4**: Comprehensive debug information
   - Shows available fields in TLE data
   - Validates TLE line format
   - Step-by-step position calculation
   - Full error tracebacks
   - **Result**: ✅ Confirmed TLE_LINE1 and TLE_LINE2 were missing

5. **Attempt 5 (Final Fix)**: Changed API format from JSON to 3LE
   ```python
   # Changed from:
   params = {'CATNR': catnr, 'FORMAT': 'json'}
   
   # To:
   params = {'CATNR': catnr, 'FORMAT': '3le'}
   
   # Parse 3LE format (three lines: name, line1, line2)
   lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
   name_line = lines[0]
   tle_line1 = lines[1]
   tle_line2 = lines[2]
   norad_cat_id = int(tle_line1[2:7].strip())
   ```
   - **Result**: ✅ **RESOLVED** - 3LE format includes TLE lines directly

**Additional Resolution (January 2025)**:
- **Issue**: Local TLE file was updated using JSON format, which removed TLE_LINE1 and TLE_LINE2
- **Fix**: Created script to download 3LE format and merge TLE lines into local JSON file
- **Result**: Local file now contains both orbital elements AND TLE lines
- **Verification**: Position calculation tested and confirmed working with valid (non-NaN) values

**Current Status**: ✅ **Resolved**
- Root cause identified: JSON format doesn't include TLE lines
- Solution implemented: Changed to 3LE format which includes TLE lines
- Local file fixed: TLE lines now properly included in local JSON file
- Tested with ISS (25544): Successfully fetches and parses TLE lines
- Position calculations now work correctly with both API and local file

**Key Lesson**: 
1. CelesTrak's JSON format (`FORMAT=json`) provides orbital elements but not formatted TLE lines
2. The 3LE format (`FORMAT=3le`) provides TLE lines directly, which is what Skyfield needs
3. When updating local TLE files, always ensure TLE_LINE1 and TLE_LINE2 are included
4. Always verify position calculation returns valid (non-NaN) values after updating TLE data

---

### Error 4: Variable Scope Error

**Error Message**:
```
Error creating 3D view: name 'all_sat_positions' is not defined
```

**When It Occurred**: When accessing debug information

**Root Cause**:
- `all_sat_positions` calculated inside `create_3d_tracked_satellites_plot()` function
- Debug code in main dashboard tried to access it outside function scope

**Resolution**:

1. **Fix**: Recalculate positions in debug section
   ```python
   debug_all_sat_positions = calculate_tracked_satellite_positions(
       tracked_satellites, 
       satellites_tle_data, 
       current_time
   )
   ```
   - **Result**: ✅ Variable scope issue fixed

**Current Status**: ✅ **Resolved**

---

### Error 5: Satellites Not Showing

**Error Message**:
```
Showing 0 of 3 tracked objects (within 5000 km of ISS)
⚠️ No other satellites visible. They may be outside the 5000 km radius or failed to load.
```

**When It Occurred**: After implementing multi-satellite tracking

**Root Cause**:
- Related to Error 3 (NaN positions)
- Without TLE lines, position calculations returned NaN
- Distance calculations failed with NaN values
- Filtering logic correctly excluded invalid positions

**Resolution Attempts**:

1. **Attempt 1**: Added debug expander
   - Shows which satellites have TLE data
   - Calculates and displays positions
   - Shows distances from ISS
   - Identifies why satellites aren't showing
   - **Result**: ✅ Debug info added, confirmed missing TLE lines

2. **Attempt 2**: Fixed total count calculation
   ```python
   # Changed from len(all_sat_positions) to len(tracked_satellites)
   total_count = len(tracked_satellites)
   ```
   - **Result**: ✅ Count now shows configured satellites, not just calculated ones

3. **Attempt 3**: Improved error messages
   - Clear warnings about why satellites aren't showing
   - Suggests checking debug information
   - **Result**: ✅ Better user guidance

4. **Attempt 4 (Final Fix)**: Resolved by fixing Error 3
   - Changed API format to 3LE which provides TLE lines
   - With valid TLE lines, position calculations work correctly
   - Satellites now display properly when within proximity radius
   - **Result**: ✅ **RESOLVED** - Satellites should now show correctly

**Current Status**: ✅ **Resolved**
- Fixed by resolving Error 3 (3LE format provides TLE lines)
- Position calculations now work correctly
- Satellites should display when within proximity radius

---

### Error 6: Streamlit Server Connection Failed

**Error Message**:
```
Connection failed
Site can't be reached
```

**When It Occurred**: When trying to access the dashboard at `http://localhost:8501`

**Root Cause**:
- The Streamlit server process was not running
- This can happen when:
  - The terminal window that started Streamlit was closed
  - The process crashed or was terminated
  - The system was restarted
  - The background process failed to start properly

**Resolution**:

1. **Check if server is running**:
   ```bash
   ps aux | grep -i streamlit | grep -v grep
   lsof -i :8501
   ```
   - If no output, the server is not running

2. **Restart the Streamlit server**:
   ```bash
   cd "/Users/ramonbnuezjr/AI Projects/satwatch"
   streamlit run src/dashboard.py
   ```
   
   Or for persistent background execution:
   ```bash
   cd "/Users/ramonbnuezjr/AI Projects/satwatch"
   nohup python3 -m streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &
   ```

3. **Verify server is accessible**:
   ```bash
   curl http://localhost:8501
   ```
   - Should return HTML (HTTP 200 status)

4. **Check server logs** (if using background mode):
   ```bash
   tail -f /tmp/streamlit.log
   ```

**Current Status**: ✅ **Resolved**
- Documented troubleshooting steps in DASHBOARD_README.md
- Added connection issue section to QUICK_START.md
- Updated main README.md with server status check note
- Users can now diagnose and fix connection issues independently

**Key Lesson**: Always check if the server process is running before troubleshooting connection issues. Background processes may not persist after terminal closes.

---

## Lessons Learned

1. **Always validate catalog numbers** before using them - some may not exist in database
2. **API response formats vary** - CelesTrak uses different field names (`OBJECT_ID` vs `NORAD_CAT_ID`)
3. **Add debug information early** - Essential for complex features like multi-satellite tracking
4. **Data format consistency matters** - Ensure TLE data format is consistent across all sources
5. **Error handling is critical** - Comprehensive error handling prevents crashes and provides useful feedback
6. **Variable scope matters** - Be careful when accessing variables across function boundaries
7. **Check server status first** - When troubleshooting connection issues, always verify the server process is running before investigating other causes
8. **Background processes need persistence** - Use `nohup` or process managers for long-running background services

---

## Recommendations

1. **For Future Development**:
   - Always add comprehensive debug information when implementing complex features
   - Test with known working catalog numbers before using user-provided ones
   - Validate data formats at each step
   - Use group endpoints when possible for more reliable data

2. **For Resolving Current Issues**:
   - Check debug output to identify root cause of NaN positions
   - Verify TLE data format consistency
   - Test with different satellite data sources
   - Consider using CelesTrak's group endpoints for initial testing

---

## Related Documentation

- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Detailed status and challenges
- [CHANGELOG.md](CHANGELOG.md) - Change history and updates
- [README.md](README.md) - Project overview

---

---

### Error 7: NaN Values Causing Map Crash

**Error Message**:
```
ValueError: Location values cannot contain NaNs.
Traceback:
File ".../dashboard.py", line 1270, in <module>
    map_obj = create_map(
File ".../dashboard.py", line 445, in create_map
    m = folium.Map(
File ".../folium/folium.py", line 300, in __init__
    self.location = validate_location(location)
File ".../folium/utilities.py", line 110, in validate_location
    raise ValueError("Location values cannot contain NaNs.")
```

**When It Occurred**: After updating TLE data freshness warning system

**Root Cause**:
- Position calculation was returning NaN values (latitude, longitude, or altitude)
- Folium map creation requires valid numeric values, cannot accept NaN
- NaN values can occur when:
  - TLE data is invalid or corrupted
  - TLE data is too old or expired
  - Position calculation fails due to invalid orbital elements
  - Error in Skyfield position calculation

**Resolution Attempts**:

1. **Attempt 1**: Added NaN validation in `create_map()` function
   ```python
   if math.isnan(latitude) or math.isnan(longitude) or math.isnan(altitude):
       raise ValueError(f"Invalid position values: latitude={latitude}, ...")
   ```
   - **Result**: ✅ Prevents crash, but doesn't handle gracefully in UI

2. **Attempt 2**: Added validation before creating map in main code
   ```python
   if (math.isnan(position['latitude']) or 
       math.isnan(position['longitude']) or 
       math.isnan(position['altitude'])):
       st.error("Position Calculation Failed...")
   ```
   - **Result**: ✅ Shows helpful error message instead of crashing

3. **Attempt 3**: Added same validation for 3D plot view
   - Validates position before creating 3D visualization
   - Shows error message with troubleshooting steps
   - **Result**: ✅ Both 2D and 3D views handle NaN gracefully

**Current Status**: ✅ **Resolved**
- Added NaN validation in `create_map()` function
- Added validation before creating both 2D map and 3D plot
- Clear error messages guide users to:
  - Switch to CelesTrak API data source
  - Refresh the page
  - Check TLE data validity
- Dashboard no longer crashes when position calculation fails

**Key Lesson**: Always validate data before passing to external libraries (like Folium) that may not handle NaN values gracefully.

---

### Error 8: Indentation Errors in Dashboard

**Error Message**:
```
IndentationError: expected an indented block
File ".../dashboard.py", line 1371
    with st.expander("🔍 Debug Information...", expanded=True):
    ^
```

**When It Occurred**: After adding NaN validation and fixing code structure

**Root Cause**:
- Incorrect indentation when adding new code blocks
- Missing indentation for code inside `with st.expander` block
- Missing indentation for `else` block handling no tracked satellites
- Python requires consistent indentation - mixing tabs/spaces or incorrect levels causes errors

**Resolution Attempts**:

1. **Attempt 1**: Fixed indentation for `with st.expander` block
   - Added proper indentation (4 spaces) for all code inside expander
   - **Result**: ✅ Fixed first indentation error

2. **Attempt 2**: Fixed indentation for `else` block
   - Corrected indentation for else block handling orbital shell view
   - Ensured all code inside else block properly indented
   - **Result**: ✅ Fixed second indentation error

3. **Attempt 3**: Verified all code structure
   - Checked indentation consistency throughout affected sections
   - Used linter to verify no syntax errors
   - **Result**: ✅ All indentation errors resolved

**Current Status**: ✅ **Resolved**
- Fixed indentation for debug expander block
- Fixed indentation for else block (orbital shell view)
- All code properly indented and validated
- Dashboard loads without syntax errors

**Key Lesson**: Always verify indentation when adding nested code blocks, especially when modifying existing code structure. Use linters to catch indentation errors early.

---

### Error 9: Missing TLE Lines in Local File

**Error Message**:
```
Position: (nan, nan, nan) km
ValueError: Location values cannot contain NaNs.
```

**When It Occurred**: After updating local TLE file using JSON format download

**Root Cause**:
- Local TLE file (`data/iss_tle.json`) was updated using `download_iss_tle_json()` function
- This function uses CelesTrak's JSON API (`FORMAT=json`) which provides orbital elements but NOT TLE lines
- The JSON format includes fields like `MEAN_MOTION`, `ECCENTRICITY`, `INCLINATION`, etc., but not `TLE_LINE1` and `TLE_LINE2`
- Skyfield requires TLE lines (formatted strings) to calculate positions, not just orbital elements
- Without TLE lines, position calculations return NaN values, causing dashboard to crash

**Diagnosis**:
1. **Tested CelesTrak API directly**: `curl "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=3le"` - ✅ Working, returns valid 3LE format
2. **Checked local file**: `cat data/iss_tle.json` - ❌ Missing `TLE_LINE1` and `TLE_LINE2` fields
3. **Root cause identified**: File was updated using JSON format which doesn't include TLE lines

**Resolution**:

1. **Downloaded 3LE format data**:
   ```python
   url = 'https://celestrak.org/NORAD/elements/gp.php'
   params = {'CATNR': 25544, 'FORMAT': '3le'}
   response = requests.get(url, params=params)
   ```

2. **Parsed 3LE format** (three lines: name, TLE line 1, TLE line 2):
   ```python
   lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
   name_line = lines[0]
   tle_line1 = lines[1]
   tle_line2 = lines[2]
   ```

3. **Merged TLE lines into existing JSON structure**:
   - Loaded existing JSON file (preserving orbital elements)
   - Added `TLE_LINE1` and `TLE_LINE2` fields
   - Updated `OBJECT_NAME` with fresh data
   - Saved back to file

4. **Verified fix**:
   - Position calculation now works correctly
   - Returns valid (non-NaN) values: Lat: 10.1616°, Lon: -64.2184°, Alt: 413.84 km
   - Dashboard can now display map and 3D view

**Current Status**: ✅ **Resolved**
- Local TLE file now contains both orbital elements AND TLE lines
- Position calculations work correctly with local file
- Dashboard displays ISS position without NaN errors
- Both API and local file modes now work properly

**Key Lesson**: 
- Always ensure TLE files contain `TLE_LINE1` and `TLE_LINE2` fields for Skyfield
- When updating TLE data, use 3LE format (`FORMAT=3le`) to get TLE lines, not JSON format
- Verify position calculation returns valid values after updating TLE data
- Test foundation (data source) before debugging application code

---

**Last Updated**: January 2025
