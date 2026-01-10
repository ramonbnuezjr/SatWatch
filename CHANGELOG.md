# SatWatch Changelog

This document tracks significant changes, improvements, and lessons learned during development.

---

## 2025-01 - Initial Implementation & Testing

### ✅ Completed Features

1. **Basic ISS Tracking (Text Format)**
   - Download TLE from CelesTrak text format
   - Parse TLE data
   - Calculate position using Skyfield
   - Display formatted output

2. **JSON Format Support**
   - Download TLE from CelesTrak JSON API
   - Load TLE from local JSON files
   - Support for both TLE lines and orbital elements
   - Automatic TLE line construction from elements (fallback)

3. **Error Handling**
   - Network error handling
   - JSON parsing validation
   - Clear error messages with solutions

4. **Documentation**
   - Comprehensive code explanations
   - Project status tracking
   - Challenge documentation
   - Multiple format guides

### 🔧 Technical Improvements

- Added `validate_json.py` for JSON structure validation
- Implemented TLE line construction from orbital elements
- Dual script architecture (text and JSON formats)
- Flexible file loading with command-line options

### 📚 Documentation Updates

- Created `PROJECT_STATUS.md` documenting challenges and solutions
- Updated `README.md` with current status
- Enhanced `JSON_APPROACH_EXPLANATION.md` with lessons learned
- Updated `data/README.md` with actual format being used

### 🐛 Issues Resolved

1. **JSON Format Mismatch**
   - **Issue**: JSON had orbital elements but not TLE lines
   - **Fix**: Added TLE lines to JSON, implemented fallback construction
   - **Status**: ✅ Resolved

2. **Skyfield Requirements**
   - **Issue**: Confusion about needing TLE lines vs. individual elements
   - **Fix**: Documented requirement, added fallback support
   - **Status**: ✅ Resolved

3. **Error Messages**
   - **Issue**: Unclear error messages when JSON structure was wrong
   - **Fix**: Added validation script, improved error messages
   - **Status**: ✅ Resolved

### 📝 Lessons Learned

1. **TLE Format is Essential**: Skyfield requires TLE lines for SGP4 propagation
2. **JSON is Great for Storage**: But needs TLE lines for calculations
3. **Validation is Critical**: Always validate data structure before processing
4. **Clear Errors Help**: Good error messages save debugging time
5. **Documentation Matters**: Document challenges and solutions, not just features

### ✅ Testing & Verification (January 2025)

- **Tested**: `python src/iss_tracker_json.py --local`
- **Result**: ✅ Successfully executed
- **Output**: Correct position calculation and formatted display
- **Status**: All core functionality verified working

### ✅ Streamlit Dashboard (January 2025)

- **Added**: Interactive web dashboard (`src/dashboard.py`)
- **Features**:
  - Real-time ISS position on interactive world map
  - Auto-refresh every 10 seconds
  - Dark theme interface
  - Sidebar with position data and TLE status
  - Data source selection (local file or CelesTrak API)
- **Dependencies**: Added streamlit, folium, streamlit-folium
- **Fixed**: Map flickering issue (stable map keys, improved refresh logic)
- **Status**: ✅ Tested and working

### 🎯 Next Steps

- [ ] Add TLE data caching
- [ ] Improve TLE construction accuracy
- [x] Multi-satellite tracking ⚠️ **IN PROGRESS** - Implementation complete, debugging NaN positions
- [x] Real-time updates ✅ **COMPLETE** - Dashboard auto-refresh
- [x] Visualization ✅ **COMPLETE** - Streamlit dashboard with map
- [x] 3D Orbit View ✅ **COMPLETE** - 3D visualization with Plotly
- [x] Orbital Shell ✅ **COMPLETE** - Layer 1 implementation
- [ ] Historical position tracking
- [ ] Orbit path visualization
- [ ] Export functionality

---

## 2025-01 - Multi-Satellite Tracking Implementation

### ✅ Completed Features

1. **Multi-Satellite Data Fetcher**
   - Created `fetch_satellites(catnr_list)` function
   - Fetches TLE data for multiple satellites from CelesTrak API
   - Handles errors gracefully (continues if one satellite fails)
   - Supports individual catalog number queries

2. **Satellites Configuration File**
   - Created `satellites.json` config file
   - Structure: `{"tracked_satellites": [{"name": "...", "catnr": ..., "type": "..."}]}`
   - Supports stations, satellites, and debris types
   - Easy to add/remove tracked satellites

3. **Multi-Satellite 3D Visualization**
   - Created `create_3d_tracked_satellites_plot()` function
   - Color coding: Stations (red), Satellites (blue), Debris (orange)
   - Proximity filtering (show objects within X km of ISS)
   - Type filtering (show/hide by type)

4. **Sidebar Filters**
   - Checkboxes to show/hide: Stations, Satellites, Debris
   - Slider for proximity radius (100-5000 km)
   - Display count: "Showing X of Y objects"
   - Loading status indicators

5. **Debug Information**
   - Comprehensive debug expander
   - Shows TLE data availability
   - Calculates and displays positions
   - Shows distances from ISS
   - Identifies why satellites aren't showing

### 🐛 Issues Encountered & Resolution Attempts

1. **API Fetch Errors**
   - **Issue**: Some catalog numbers return empty responses
   - **Error**: `"Expecting value: line 1 column 1 (char 0)"`
   - **Fix**: Added empty response check, improved error handling
   - **Status**: ⚠️ Some catalog numbers may not exist in database

2. **Catalog Number Extraction**
   - **Issue**: `ValueError: invalid literal for int() with base 10: '1998-067A'`
   - **Cause**: `OBJECT_ID` field can be international designator, not numeric
   - **Fix**: Check `NORAD_CAT_ID` first, fallback to TLE line extraction
   - **Status**: ✅ Resolved

3. **NaN Position Calculations**
   - **Issue**: All positions showing as `nan` in debug output
   - **Cause**: CelesTrak JSON format doesn't include TLE_LINE1/TLE_LINE2 fields
   - **Fix**: Changed API format from `FORMAT=json` to `FORMAT=3le` (three-line element)
   - **Result**: 3LE format includes TLE lines directly, enabling Skyfield calculations
   - **Status**: ✅ **Resolved**

4. **Variable Scope Error**
   - **Issue**: `name 'all_sat_positions' is not defined`
   - **Cause**: Variable defined inside function, accessed outside
   - **Fix**: Recalculate positions in debug section
   - **Status**: ✅ Resolved

5. **Satellites Not Showing**
   - **Issue**: "Showing 0 of 3 tracked objects" even with filters enabled
   - **Cause**: Related to NaN positions issue (missing TLE lines)
   - **Fix**: Resolved by fixing Issue 3 (changed to 3LE format)
   - **Status**: ✅ **Resolved** - Satellites should now display correctly with valid TLE data

### 📚 Documentation Updates

- Updated `PROJECT_STATUS.md` with all recent issues and resolution attempts
- Updated `CHANGELOG.md` with multi-satellite tracking implementation
- Added comprehensive error documentation

### 🔧 Technical Improvements

- **Fixed `fetch_satellites()` function**: Changed from JSON to 3LE format
  - Now uses `FORMAT=3le` instead of `FORMAT=json`
  - Parses three-line element format (name, TLE line 1, TLE line 2)
  - Extracts catalog number from TLE line 1
  - Returns TLE lines directly for Skyfield calculations
- Improved error handling in `fetch_satellites()` function
- Enhanced catalog number extraction logic
- Added NaN validation checks
- Comprehensive debug output system
- Better user feedback for loading status

### 📝 Lessons Learned

1. **Catalog Number Validation**: Always verify catalog numbers exist in database
2. **API Response Formats**: CelesTrak uses different field names (`OBJECT_ID` vs `NORAD_CAT_ID`)
3. **TLE Format Matters**: CelesTrak JSON format doesn't include TLE lines - use 3LE format instead
4. **Error Handling**: Comprehensive error handling and debug output essential for complex features
5. **Data Format Consistency**: Ensure TLE data format is consistent across all sources
6. **Debug First**: Add debug information early when implementing complex features
7. **API Format Selection**: Choose API format based on what data you need - JSON for elements, 3LE for TLE lines

---

## 2025-01 - Multi-Satellite Tracking Fix (Latest)

### ✅ Critical Fix: NaN Position Calculations

**Issue**: All satellite positions returning NaN values, preventing visualization

**Root Cause**: CelesTrak JSON API format (`FORMAT=json`) does not include `TLE_LINE1` and `TLE_LINE2` fields required by Skyfield

**Solution**: Changed `fetch_satellites()` function to use 3LE format (`FORMAT=3le`) which includes TLE lines directly

**Changes**:
- Modified API request from `FORMAT=json` to `FORMAT=3le`
- Added 3LE format parsing (three lines: name, TLE line 1, TLE line 2)
- Extract catalog number from TLE line 1 (positions 2-7)
- Return dictionary with `OBJECT_NAME`, `TLE_LINE1`, `TLE_LINE2`, `NORAD_CAT_ID`

**Test Results**:
- ✅ Tested with ISS (25544) - Successfully fetches and parses 3LE format
- ✅ Returns required TLE lines for Skyfield calculations
- ✅ Position calculations now work correctly

**Impact**: Multi-satellite tracking visualization should now work correctly with valid position calculations

---

## 2025-01 - Streamlit Server Connection Issue

### 🐛 Issue: Dashboard Connection Failures

**Date**: January 2025  
**Issue**: Users experiencing "Connection failed" or "Site can't be reached" errors when accessing the dashboard

**Root Cause**: 
The Streamlit server process was not running. This can occur when:
- The terminal window that started Streamlit was closed
- The process crashed or was terminated
- The system was restarted
- The background process failed to start properly

**Symptoms**:
- Browser shows "Connection failed" or "Site can't be reached"
- Error accessing `http://localhost:8501`
- No Streamlit process found when checking with `ps aux | grep streamlit`
- Port 8501 not in use when checking with `lsof -i :8501`

**Resolution**:
1. **Check if server is running**:
   ```bash
   ps aux | grep -i streamlit | grep -v grep
   lsof -i :8501
   ```

2. **Restart the server**:
   ```bash
   streamlit run src/dashboard.py
   ```
   
   Or for persistent background execution:
   ```bash
   nohup python3 -m streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &
   ```

3. **Verify server is accessible**:
   ```bash
   curl http://localhost:8501
   ```

**Documentation Updates**:
- Added comprehensive troubleshooting section to `DASHBOARD_README.md`
- Added connection issue troubleshooting to `QUICK_START.md`
- Added note to main `README.md` about checking server status
- Updated `ERROR_RESOLUTION_LOG.md` with this issue

**Prevention**:
- Use `nohup` for background execution to persist after terminal closes
- Consider process managers (screen, tmux) for long-running sessions
- Document server status checking procedures

**Status**: ✅ Resolved - Documentation updated with troubleshooting steps

---

## 2025-01 - Dashboard Error Fixes & TLE Freshness Improvements

### 🐛 Issues Fixed

1. **Missing TLE Lines in Local File (Root Cause of NaN Issue)**
   - **Issue**: Local TLE file (`data/iss_tle.json`) was missing `TLE_LINE1` and `TLE_LINE2` after updating via JSON API
   - **Root Cause**: `download_iss_tle_json()` uses JSON format which provides orbital elements but NOT TLE lines required by Skyfield
   - **Solution**: 
     - Created script to download 3LE format data (includes TLE lines)
     - Merged TLE lines into existing JSON file structure
     - Verified position calculation works with valid (non-NaN) values
   - **Status**: ✅ Resolved - Foundation fixed, position calculations now work correctly

2. **NaN Position Values Causing Map Crash**
   - **Issue**: Dashboard crashing with `ValueError: Location values cannot contain NaNs` when position calculation returned NaN
   - **Root Cause**: Folium map creation cannot accept NaN values for latitude/longitude (caused by missing TLE lines)
   - **Solution**: 
     - Fixed root cause: Added TLE lines to local file
     - Added NaN validation in `create_map()` function
     - Added validation before creating both 2D map and 3D plot views
     - Added helpful error messages with troubleshooting steps
   - **Status**: ✅ Resolved

2. **Indentation Errors**
   - **Issue**: `IndentationError: expected an indented block` preventing dashboard from loading
   - **Root Cause**: Incorrect indentation when adding new code blocks (debug expander, else block)
   - **Solution**: Fixed indentation for all affected code blocks
   - **Status**: ✅ Resolved

### ✅ Improvements

1. **Enhanced TLE Data Freshness Warning System**
   - **Before**: Simple binary check (< 12 hours = fresh, else warning)
   - **After**: Graduated warning system:
     - < 7 days: Green "Data Fresh"
     - 7-10 days: Yellow "Data Getting Old" (with days until expiration)
     - 10-14 days: Yellow "Data Old" (with expiration countdown)
     - > 14 days: Red "Data Expired" (update required)
   - **Impact**: More accurate warnings that reflect TLE data validity period (~2 weeks)
   - **Status**: ✅ Implemented

2. **Better Error Handling**
   - Added comprehensive NaN validation throughout dashboard
   - Clear error messages guide users to solutions
   - Graceful degradation when position calculation fails
   - **Status**: ✅ Implemented

### 📚 Documentation Updates

- Updated `ERROR_RESOLUTION_LOG.md` with Error #7 (NaN map crash) and Error #8 (Indentation errors)
- Updated `CHANGELOG.md` with recent fixes
- Enhanced error handling documentation

---

## 2025-01 - Conjunction Risk Calculator

### ✅ New Feature: Collision Risk Assessment

**Added**: `calculate_conjunction_risk()` function in `src/conjunction_risk.py`

**Features**:
- Propagates two satellites forward in time using SGP4
- Calculates 3D distance between satellites at 1-minute intervals
- Identifies minimum distance and time of closest approach
- Risk level classification:
  - **CRITICAL**: Distance < 1 km
  - **HIGH RISK**: Distance < 5 km
  - **NORMAL**: Distance ≥ 5 km
- Returns detailed results including positions at closest approach
- Includes `format_conjunction_report()` for human-readable output

**Usage**:
```python
from conjunction_risk import calculate_conjunction_risk, format_conjunction_report

result = calculate_conjunction_risk(sat1_tle, sat2_tle, hours_ahead=48)
print(format_conjunction_report(result))
```

**Technical Details**:
- Uses Skyfield for SGP4 propagation
- Configurable time horizon (default: 48 hours)
- Configurable step size (default: 1 minute)
- Handles propagation errors gracefully
- Returns structured dictionary with all analysis results

**Status**: ✅ Implemented and tested

**Next Steps**:
- Integrate into dashboard for real-time monitoring
- Add batch analysis for multiple satellite pairs
- Implement alerting system based on risk levels

---

## Format

Each entry includes:
- **Date**: When the change was made
- **Type**: Feature, Fix, Documentation, etc.
- **Description**: What changed and why
- **Impact**: How it affects users/developers
