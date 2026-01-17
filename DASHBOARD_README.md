# SatWatch Dashboard

A real-time Streamlit dashboard for tracking the International Space Station (ISS) position on an interactive world map.

## Features

- 🌍 **Interactive World Map**: Real-time ISS position displayed on a dark-themed map
- 📊 **Live Data**: Auto-refreshes every 10 seconds (smooth, no flickering)
- 📍 **Position Tracking**: Shows latitude, longitude, and altitude
- 📡 **TLE Data Status**: Displays data freshness indicator with graduated warnings
- 🎨 **Dark Theme**: Professional, clean UI with dark theme
- 🔄 **Auto-Refresh**: Automatically updates position every 10 seconds
- ✅ **Stable Display**: Fixed flickering issues for smooth map updates
- 🎯 **Focus Mode**: Toggle to highlight your tracked satellites with nearby objects as secondary
- 🛰️ **Multi-Satellite Tracking**: Track multiple satellites from your `satellites.json` configuration
- 🌐 **3D Orbit View**: Interactive 3D visualization with Plotly showing Earth, satellites, and orbit paths

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

This will install:
- `streamlit` - Web dashboard framework
- `folium` - Interactive maps
- `streamlit-folium` - Folium integration for Streamlit
- All other SatWatch dependencies

## Running the Dashboard

### Option 1: Run from project root

```bash
streamlit run src/dashboard.py
```

### Option 2: Run from src directory

```bash
cd src
streamlit run dashboard.py
```

The dashboard will open in your default web browser at `http://localhost:8501`

## Dashboard Components

### Main Map View
- Interactive world map with dark theme
- Red marker showing current ISS position
- Approximate visibility circle around ISS
- Click and drag to explore the map
- Zoom in/out with mouse wheel

### Sidebar Information
- **Current Time (UTC)**: Real-time clock
- **ISS Position**: 
  - Latitude (degrees)
  - Longitude (degrees)
  - Altitude (kilometers)
- **TLE Data**:
  - Epoch timestamp
  - Data freshness indicator with graduated warnings:
    - ✅ **Fresh**: < 7 days old (green)
    - ⚠️ **Getting Old**: 7-10 days old (yellow)
    - ⚠️ **Old**: 10-14 days old (yellow/orange)
    - ❌ **Expired**: > 14 days old (red)
- **Satellite Info**:
  - Satellite name
  - NORAD catalog ID
- **Multi-Satellite Filters**:
  - Type filters: Show/Hide stations, satellites, debris
  - Proximity radius: Adjust distance threshold (100-5000 km)
  - **Focus Mode**: Toggle to highlight your tracked satellites

### Data Source Selection
Choose between:
- **Local File**: Uses `data/iss_tle.json` (faster, no internet needed)
- **CelesTrak API**: Downloads fresh data from CelesTrak (requires internet)

### Focus Mode

**Focus Mode** is a powerful feature that lets you prioritize your tracked satellites in the visualization.

**When OFF (default)**:
- Shows all objects within the proximity/type filters equally
- All objects displayed with standard markers and colors
- Proximity calculated from ISS position

**When ON**:
- **Primary Objects**: Your tracked satellites from `satellites.json` are displayed prominently:
  - Larger markers (size 12)
  - Bright colors
  - Name labels visible
  - Thicker borders
- **Secondary Objects**: Nearby objects within proximity threshold are shown as:
  - Smaller markers (size 4)
  - Semi-transparent gray
  - No labels
  - Automatically fetched from CelesTrak
- **Proximity**: Calculated from all your tracked satellites, not just ISS
- **Stats**: Shows "Tracking X satellites, Y nearby objects"

**Visual Distinctions in 3D View**:
- **Your Satellites**: Large, bright, labeled markers
- **Nearby Objects**: Small, muted, semi-transparent markers
- **Risk Objects**: Red highlight (if conjunction data exists)

**Use Cases**:
- Monitor your satellite fleet while seeing nearby traffic
- Identify potential conjunction risks with your assets
- Focus on your satellites without visual clutter from unrelated objects

## Auto-Refresh

The dashboard automatically refreshes every 10 seconds to show the latest ISS position. The countdown timer is displayed at the bottom of the map.

## Troubleshooting

### Dashboard won't start
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that `data/iss_tle.json` exists if using local file mode

### Connection Failed / Site Can't Be Reached

**Symptoms**: 
- Browser shows "Connection failed" or "Site can't be reached"
- Error when trying to access `http://localhost:8501`

**Root Cause**: 
The Streamlit server process is not running. This can happen if:
- The terminal window that started Streamlit was closed
- The process crashed or was terminated
- The system was restarted
- The process was killed by another process

**Solution - Check if Server is Running**:

1. **Check if Streamlit process is running**:
   ```bash
   ps aux | grep -i streamlit | grep -v grep
   ```
   - If no output, the server is not running

2. **Check if port 8501 is in use**:
   ```bash
   lsof -i :8501
   ```
   - If no output, nothing is listening on port 8501

3. **Restart the Streamlit server**:
   ```bash
   cd "/Users/ramonbnuezjr/AI Projects/satwatch"
   streamlit run src/dashboard.py
   ```
   
   Or for persistent background execution:
   ```bash
   cd "/Users/ramonbnuezjr/AI Projects/satwatch"
   nohup python3 -m streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &
   ```

4. **Verify server is running**:
   ```bash
   curl http://localhost:8501
   ```
   - Should return HTML (HTTP 200 status)

5. **Check server logs** (if using background mode):
   ```bash
   tail -f /tmp/streamlit.log
   ```

**Alternative URLs to Try**:
- `http://localhost:8501`
- `http://127.0.0.1:8501`

**Prevention**:
- Keep the terminal window open when running Streamlit in foreground mode
- Use `nohup` or a process manager for background execution
- Consider setting up a system service for automatic startup

### Map not displaying
- Check browser console for errors
- Ensure internet connection for map tiles (if using API mode)
- Try refreshing the browser page

### Position seems incorrect
- TLE data may be expired (check freshness indicator)
- Try switching to "CelesTrak API" to get fresh data
- TLE data is typically valid for ~2 weeks

### Map is flickering
- **Fixed**: The flickering issue has been resolved
- If you still see flickering, try refreshing the browser page
- The map uses stable keys to prevent unnecessary recreation

### "Location values cannot contain NaNs" Error

**Symptoms**: 
- Dashboard shows error: `ValueError: Location values cannot contain NaNs`
- Map or 3D view fails to display
- Error occurs when trying to render ISS position

**Root Cause**: 
Position calculation returned NaN (Not a Number) values. This can happen when:
- **Most Common**: Local TLE file is missing `TLE_LINE1` and `TLE_LINE2` fields (Skyfield requires these)
- TLE data is invalid or corrupted
- TLE data is too old or expired
- Error in position calculation
- Invalid orbital elements in TLE data

**Solution**:
1. **Check local file has TLE lines**: 
   ```bash
   grep "TLE_LINE" data/iss_tle.json
   ```
   - If missing, download 3LE format and add TLE lines to file

2. **Switch data source**: In the sidebar, change from "Local File" to "CelesTrak API"
   - API mode downloads fresh data with TLE lines automatically

3. **Update TLE data properly**: 
   - Use 3LE format (`FORMAT=3le`) to get TLE lines, not JSON format
   - Ensure `TLE_LINE1` and `TLE_LINE2` are included in local file

4. **Refresh page**: Reload the dashboard after fixing TLE data

**Prevention**:
- Always ensure local TLE files contain `TLE_LINE1` and `TLE_LINE2` fields
- When updating TLE data, use 3LE format to get TLE lines
- Keep TLE data updated (refresh every few days)
- Use CelesTrak API for most up-to-date data
- Dashboard now validates position values and shows helpful error messages

### "IndentationError" or Script Execution Error

**Symptoms**: 
- Dashboard shows: `IndentationError: expected an indented block`
- Page fails to load completely
- Script execution error in browser

**Root Cause**: 
Code syntax error due to incorrect indentation (usually after code updates)

**Solution**:
1. **Refresh the page**: Sometimes a simple refresh resolves temporary issues
2. **Check server logs**: Look at Streamlit server output for detailed error
3. **Restart server**: Stop and restart the Streamlit server
4. **Report issue**: If problem persists, check GitHub issues or report the error

**Status**: ✅ **Fixed** - All known indentation errors have been resolved

## Customization

### Change refresh interval
Edit `dashboard.py` and change the `10` in the auto-refresh logic:

```python
if time_since_refresh >= 10:  # Change 10 to desired seconds
```

### Change map theme
Edit the `tiles` parameter in `create_map()`:

```python
tiles='CartoDB dark_matter'  # Options: 'OpenStreetMap', 'CartoDB positron', etc.
```

### Adjust marker size
Edit the `radius` parameter in the `CircleMarker`:

```python
radius=10,  # Change to desired size
```

## Technical Details

- Uses Folium for map rendering
- Integrates with existing `iss_tracker_json.py` functions
- Session state management for auto-refresh
- Dark theme via custom CSS and CartoDB dark tiles
- Responsive layout with Streamlit's column system
- **Flickering Fix**: Uses stable map keys and improved refresh logic
- Map only updates when position actually changes significantly

## Known Issues & Solutions

### Map Flickering (Resolved ✅)
- **Issue**: Map was flickering every 0.5 seconds
- **Cause**: Map was being recreated on every script rerun
- **Solution**: 
  - Fixed map key to prevent unnecessary recreation
  - Improved refresh timing logic
  - Map now updates smoothly every 10 seconds
- **Status**: ✅ Fixed and tested

## Next Steps

- Add historical position tracking
- Show ISS orbit path
- Add multiple satellite support
- Implement alerts/notifications
- Add export functionality
- Customizable refresh intervals