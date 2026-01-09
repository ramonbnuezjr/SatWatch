# SatWatch Project Status & Lessons Learned

This document tracks what's working well, challenges we've faced, and solutions we've implemented.

**Last Updated**: January 2025

---

## ✅ What's Working Well

### 1. **Dual Script Architecture**
- **`iss_tracker.py`**: Downloads TLE from CelesTrak text format
- **`iss_tracker_json.py`**: Works with JSON format (both API and local files)
- Both scripts successfully calculate ISS position using Skyfield
- Clean separation of concerns

### 2. **JSON Support with Fallback**
- Script handles JSON with TLE lines (preferred)
- Falls back to constructing TLE lines from orbital elements if needed
- Supports both single object and array formats
- Flexible file loading (local or API)

### 3. **Comprehensive Documentation**
- Line-by-line code explanations for beginners
- Clear installation instructions
- Multiple documentation formats (README, explanations, guidelines)
- Cursor AI rules for consistent code generation

### 4. **Error Handling**
- Graceful handling of network errors
- Clear error messages for missing data
- Validation of JSON structure and TLE format
- Helpful troubleshooting messages

### 5. **Data Validation**
- `validate_json.py` script checks JSON structure
- Validates required fields (TLE lines or orbital elements)
- Identifies ISS entry correctly (by NORAD ID or name)

### 6. **Successful Testing** ✅
- Scripts tested and verified working (January 2025)
- Successfully loads JSON from local file
- Correctly parses TLE data
- Accurately calculates ISS position
- Displays formatted output as expected
- All dependencies install correctly

### 7. **Streamlit Dashboard** ✅ **NEW**
- Interactive web dashboard with real-time ISS tracking
- World map visualization using Folium
- Auto-refresh every 10 seconds
- Dark theme interface
- Sidebar with position data and TLE status
- Data source selection (local file or API)
- Fixed flickering issues for smooth map updates
- Successfully tested and working

---

## 🚧 Challenges We Faced

### Challenge 1: JSON Format Mismatch

**Problem**: 
- Initial JSON file contained individual orbital elements (MEAN_MOTION, ECCENTRICITY, etc.)
- But Skyfield's `EarthSatellite` class requires TLE lines (TLE_LINE1, TLE_LINE2)
- User expected to use just the 5 orbital elements they mentioned

**Root Cause**:
- Skyfield uses SGP4 propagation which requires TLE format
- TLE lines encode orbital elements in a specific fixed-width format
- Individual elements alone aren't sufficient without proper TLE formatting

**Solution**:
1. Updated script to handle both formats:
   - **Preferred**: Use TLE_LINE1 and TLE_LINE2 if present
   - **Fallback**: Construct TLE lines from orbital elements
2. Added TLE lines to JSON file manually (from CelesTrak)
3. Documented that both formats are needed:
   - TLE lines for Skyfield calculations
   - Individual elements for human readability

**Lesson Learned**: 
- Always check library requirements before assuming data format
- TLE format is the industry standard for a reason - it's optimized for SGP4
- Having both formats in JSON gives best of both worlds

---

### Challenge 4: Dashboard Map Flickering

**Problem**:
- Streamlit dashboard map was flickering every 0.5 seconds
- Map was being recreated on every script rerun
- Poor user experience with constant visual disruption

**Root Cause**:
- Streamlit reruns the entire script on every refresh
- Map was being recreated with dynamic keys based on position
- No caching or stable key mechanism
- Refresh logic was triggering too frequently

**Solution**:
1. Changed map key to fixed value (`"iss_tracker_map"`) instead of dynamic
2. Improved refresh timing logic with better session state management
3. Added delay before rerun to prevent rapid loops
4. Map now only updates when position actually changes significantly

**Lesson Learned**:
- Use stable keys for Streamlit components that shouldn't be recreated
- Session state management is crucial for auto-refresh features
- Small delays can prevent rapid rerun loops
- Fixed keys prevent unnecessary component recreation

---

### Challenge 2: TLE Line Construction Complexity

**Problem**:
- Attempted to construct TLE lines from orbital elements
- TLE format has strict fixed-width fields (69 characters per line)
- Complex formatting rules (epoch as YYDDD.DDDDDDDD, scientific notation for small numbers)

**Root Cause**:
- TLE format specification is very precise
- Many edge cases in formatting (negative numbers, scientific notation)
- Easy to introduce errors in manual construction

**Solution**:
- Implemented `format_tle_line1()` and `format_tle_line2()` functions
- Followed TLE format specification carefully
- Added validation to ensure proper format
- **However**: Still recommend using TLE lines from CelesTrak when available (more accurate)

**Lesson Learned**:
- Prefer using authoritative sources (CelesTrak) for TLE data
- Construction from elements is possible but error-prone
- Always validate TLE format before using with Skyfield

---

### Challenge 3: Understanding Skyfield Requirements

**Problem**:
- Initial assumption: Can use individual orbital elements directly
- Reality: Skyfield needs TLE lines for `EarthSatellite` class
- Confusion about what data format is needed

**Root Cause**:
- Skyfield documentation assumes TLE format
- Not immediately obvious that TLE lines are required
- Individual elements seem more intuitive for beginners

**Solution**:
- Created `JSON_APPROACH_EXPLANATION.md` explaining requirements
- Updated documentation to clarify TLE line requirement
- Added examples showing both formats
- Made script handle both for flexibility

**Lesson Learned**:
- Read library documentation carefully before designing data structures
- TLE format is the standard for good reasons (accuracy, compatibility)
- Documentation should explain "why" not just "how"

---

### Challenge 4: JSON File Structure Validation

**Problem**:
- User copied JSON that had orbital elements but not TLE lines
- Script would fail with unclear error messages
- No way to validate JSON structure before running

**Solution**:
- Created `validate_json.py` script
- Checks for required fields (TLE lines OR orbital elements)
- Provides clear feedback on what's missing
- Identifies ISS entry correctly

**Lesson Learned**:
- Validation tools are essential for data-driven applications
- Clear error messages save debugging time
- Always validate input data structure

---

### Challenge 5: Dashboard Map Flickering

**Problem**:
- Streamlit dashboard map was flickering every 0.5 seconds
- Map was being recreated on every script rerun
- Poor user experience with constant visual disruption
- Made the dashboard difficult to use

**Root Cause**:
- Streamlit reruns the entire script on every refresh
- Map was being recreated with dynamic keys based on position
- No caching or stable key mechanism
- Refresh logic was triggering too frequently

**Solution**:
1. Changed map key to fixed value (`"iss_tracker_map"`) instead of dynamic
2. Improved refresh timing logic with better session state management
3. Added delay before rerun to prevent rapid loops
4. Map now only updates when position actually changes significantly

**Lesson Learned**:
- Use stable keys for Streamlit components that shouldn't be recreated
- Session state management is crucial for auto-refresh features
- Small delays can prevent rapid rerun loops
- Fixed keys prevent unnecessary component recreation

---

## 📊 Current Implementation Status

### Working Features ✅

1. **TLE Download (Text Format)**
   - ✅ Downloads from CelesTrak
   - ✅ Parses TLE format
   - ✅ Calculates position
   - ✅ Displays formatted output

2. **TLE Download (JSON Format)**
   - ✅ Downloads from CelesTrak JSON API
   - ✅ Parses JSON structure
   - ✅ Finds ISS entry
   - ✅ Calculates position

3. **Local JSON File Support**
   - ✅ Loads from `data/iss_tle.json`
   - ✅ Supports custom file paths
   - ✅ Handles both TLE lines and orbital elements
   - ✅ Command-line flags (`--local`, `--file`)

4. **Error Handling**
   - ✅ Network error handling
   - ✅ JSON parsing errors
   - ✅ Missing data validation
   - ✅ Clear error messages

### Known Limitations ⚠️

1. **TLE Construction Accuracy**
   - Constructed TLE lines may have slight formatting differences
   - Prefer using TLE lines from CelesTrak when possible
   - Construction is a fallback, not primary method

2. **Single Satellite Only**
   - Currently tracks only ISS
   - Multi-satellite support planned for future

3. **No Caching**
   - Downloads TLE data every run
   - No local caching mechanism yet

4. **Dashboard Refresh Rate**
   - Auto-refreshes every 10 seconds (configurable)
   - Not true real-time (sub-second updates)
   - Suitable for ISS tracking (orbital period ~92 minutes)

5. **OpenSSL Warning (Minor)**
   - urllib3 may show a warning about OpenSSL/LibreSSL compatibility
   - This is harmless and doesn't affect functionality
   - Can be safely ignored

6. **Map Flickering (Resolved)**
   - Initial version had map flickering issue
   - **Fixed** by using stable map keys and improved refresh logic
   - Map now updates smoothly without flickering

---

## 🎯 Best Practices Established

### 1. **Data Format Priority**
   - **First choice**: TLE_LINE1 and TLE_LINE2 from JSON
   - **Second choice**: Construct TLE lines from orbital elements
   - **Never**: Try to use individual elements directly with Skyfield

### 2. **Error Messages**
   - Always explain what went wrong
   - Suggest solutions (e.g., "Use --local flag for local files")
   - Provide context (e.g., "Check internet connection")

### 3. **Code Organization**
   - Separate functions for different tasks
   - Clear function names and docstrings
   - Type hints for better IDE support

### 4. **Documentation**
   - Explain "why" not just "how"
   - Include examples
   - Document challenges and solutions
   - Keep documentation updated with code

### 5. **Streamlit Dashboard Development**
   - Use stable keys for components that shouldn't be recreated
   - Manage session state carefully for auto-refresh
   - Add small delays to prevent rapid rerun loops
   - Test for flickering and visual stability
   - Use fixed keys for maps and visualizations

---

## 🔄 Next Steps

### Immediate Improvements
- [ ] Add TLE data caching (avoid repeated downloads)
- [ ] Improve TLE construction accuracy
- [ ] Add more validation for orbital element ranges
- [ ] Dashboard: Add orbit path visualization
- [ ] Dashboard: Add historical position trail

### Future Enhancements
- [ ] Multi-satellite tracking
- [ ] Historical position tracking
- [ ] API endpoint for position queries
- [ ] Dashboard: Export position data
- [ ] Dashboard: Customizable refresh intervals
- [ ] Dashboard: Multiple map view options
- [ ] Alerts and notifications

---

## 📝 Key Takeaways

1. **TLE Format is Essential**: Skyfield requires TLE lines, not just orbital elements
2. **JSON is Great for Storage**: But needs TLE lines for calculations
3. **Validation is Critical**: Always validate data structure before processing
4. **Clear Errors Help**: Good error messages save time debugging
5. **Documentation Matters**: Explain challenges and solutions, not just features
6. **Testing Confirms Success**: Scripts have been tested and verified working correctly
7. **Dashboard Stability**: Use stable keys and proper session state management for smooth UI
8. **User Experience**: Fix visual issues (like flickering) promptly for better UX

## ✅ Verification Results

### Command-Line Scripts (January 2025)

**Test Command**: `python src/iss_tracker_json.py --local`

**Results**:
- ✅ Successfully loaded JSON file from `data/iss_tle.json`
- ✅ Correctly identified ISS entry (NORAD ID: 25544)
- ✅ Parsed TLE_LINE1 and TLE_LINE2 successfully
- ✅ Calculated position accurately (latitude, longitude, altitude)
- ✅ Displayed formatted output correctly
- ✅ All dependencies installed without issues

**Sample Output Verified**:
- Position calculation: Working correctly
- Time display: Current UTC time
- Coordinate format: Degrees with proper precision
- Altitude: Kilometers with 2 decimal places
- Box formatting: Clean, readable display

### Streamlit Dashboard (January 2025)

**Test Command**: `streamlit run src/dashboard.py`

**Results**:
- ✅ Dashboard starts successfully on port 8501
- ✅ Map displays correctly with ISS position
- ✅ Auto-refresh works (every 10 seconds)
- ✅ Sidebar displays all required information
- ✅ Data source switching works (local file / API)
- ✅ Dark theme renders correctly
- ✅ Map flickering issue resolved
- ✅ Position updates smoothly without map recreation

**Dashboard Features Verified**:
- Interactive map: Working with Folium
- ISS marker: Red dot displays correctly
- Position data: Latitude, longitude, altitude accurate
- TLE status: Freshness indicator works
- Auto-refresh: Updates every 10 seconds as designed
- UI stability: No flickering, smooth updates

---

## 🚀 Professional Context & Future Vision

### What Professional Satellite Monitoring Looks Like

Companies like **SpaceX** and other space operators don't just see "dots on a map." They use **layered, structured 3D telemetry systems** that answer one critical question:

> **"Do we need to act — and if so, when?"**

### The Five Layers of Professional Monitoring

#### Layer 1: The Orbital Shell (The "Space Highway")
- **3D state vectors** for each object (position x,y,z + velocity vx,vy,vz)
- Multiple altitude bands visualized (LEO, MEO, GEO)
- Objects rendered as moving points or vectors on curved orbital planes
- Answers: **"Who shares this neighborhood?"**

#### Layer 2: Conjunction Space (The Danger Bubble)
- **3D covariance ellipsoids** around each tracked object
- Size depends on:
  - Tracking uncertainty
  - Object size
  - Relative velocity
- **Probabilistic risk**, not just distance
- Anything entering triggers analysis

#### Layer 3: Time-Sliced Trajectories
- **Projected paths forward** (10 min, 1 orbit, 24-72 hours)
- Each object becomes a **tube**, not a line
- Color-coded by:
  - Probability of collision (Pc)
  - Relative speed
  - Tracking confidence
- Fast-moving objects (14 km/s) get more attention than slow ones

#### Layer 4: Risk Prioritization
- Ranked alerts showing:
  - Object ID
  - Time of Closest Approach (TCA)
  - Miss distance (radial / along-track / cross-track)
  - Probability of collision
  - Recommended action (Monitor / Refine tracking / Maneuver required)
- **99.9% of objects filtered out automatically**
- Humans only see top 0.1% of risk events

#### Layer 5: Maneuver Simulation (The "What If" Engine)
- Simulates tiny burns (< 1 m/s) before execution
- Shows new projected orbit
- Calculates secondary effects:
  - New conjunctions created
  - Fuel cost
  - Mission impact
- Updates map instantly: **"If we move here, what breaks?"**

### What This Means for SatWatch

**Current State**: 
- ✅ Basic ISS position tracking
- ✅ 2D map visualization
- ✅ 3D orbit view with path prediction
- ✅ Real-time updates

**Future Potential**:
- Multi-satellite tracking (Layer 1)
- Conjunction analysis (Layer 2)
- Extended trajectory visualization (Layer 3)
- Risk scoring and alerts (Layer 4)
- Maneuver planning tools (Layer 5)

### Key Insight

Professional systems don't show "space debris" — they show **time, probability, and decision pressure**. The visualization exists to answer one question: **"Do we need to act?"**

Everything else is noise.

---

## 🤝 Contributing Notes

When adding new features:
- Follow the established patterns (TLE lines preferred)
- Add validation for new data formats
- Update this document with new challenges/solutions
- Keep error messages helpful and actionable
- Consider the professional context above when designing new features