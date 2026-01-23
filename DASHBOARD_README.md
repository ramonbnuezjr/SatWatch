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
- 🚀 **Demo Mode: Full Traffic**: Display 500-1000 active satellites to visualize space traffic density
- 📊 **Space Statistics**: Real-world numbers showing 25,000+ tracked objects and ~500,000 debris pieces

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

### Demo Mode: Full Traffic View

**Purpose**: Demonstrate the scale and density of space traffic for educational/demo purposes.

**Features**:
- **"Show Full Traffic" Toggle**: When enabled, fetches 30-100 active satellites from CelesTrak
- **Traffic Density Slider**: Adjustable 30-100 objects (default: 50)
- **Visual Impact**: Shows the crowded nature of Low Earth Orbit (LEO)
- **Load Time**: Optimized for 200-500ms (near real-time)
- **Statistics Panel**: Displays real-world numbers:
  - **25,000+** tracked objects in space
  - **~500,000** pieces of debris (1-10cm)
  - **~2** ISS collision avoidance maneuvers per year

**How to Use**:
1. Check the "🚀 Show Full Traffic (Demo Mode)" checkbox in the sidebar
2. Adjust the "Traffic Density" slider (30-100 objects, default: 50)
3. Data loads once (~200-500ms) and is cached for smooth interaction
4. The 3D view will populate with satellites showing the density

**Performance & Caching**:
- **Smart Caching**: Data is fetched once and cached in session state
- **No Refresh Loops**: You can zoom/rotate the 3D plot without triggering refetches
- **Automatic Updates**: Only refetches if you change the traffic count slider
- **Smooth Interaction**: Cached data allows seamless 3D plot manipulation

**Best For**:
- Demonstrations to stakeholders
- Educational presentations
- Understanding the scale of the space traffic problem
- Visualizing why space traffic management is critical

**Note**: This mode fetches live data from CelesTrak, so it requires internet connectivity. Load time is optimized for 30-100 objects (200-500ms). Data is cached to prevent refresh loops when interacting with the 3D visualization.

## Auto-Refresh

The dashboard automatically refreshes every 10 seconds to show the latest ISS position. The countdown timer is displayed at the bottom of the map.

## Troubleshooting

### Dashboard won't start
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that `data/iss_tle.json` exists if using local file mode

### Satellites Fail to Load (Warning Messages)

**Symptoms**:
- Warning messages like: "Failed: STARLINK-1007 (44713)..."
- Some satellites in your `satellites.json` don't appear in the list

**Why This Happens**:

| Reason | Description |
|--------|-------------|
| **Deorbited** | Satellite has re-entered atmosphere (common for Starlink) |
| **Renamed** | Constellation satellites get new NORAD designations |
| **Debris decayed** | Small debris burns up, removed from catalog |
| **Not public** | Some objects restricted from public tracking |
| **Catalog changed** | NORAD IDs occasionally get reassigned |

**This is Normal**: Space objects are constantly changing. The warnings help you identify which satellites need to be updated or removed from your config.

**Solution**:
1. **Test before adding**: Verify catalog numbers work with CelesTrak:
   ```
   https://celestrak.org/NORAD/elements/gp.php?CATNR={id}&FORMAT=3le
   ```
2. **Use stable satellites**: ISS (25544), Hubble (20580), NOAA-20 (43013) rarely change
3. **Update periodically**: Review and clean up `satellites.json` monthly
4. **Remove failed entries**: Edit `satellites.json` to remove non-working catalog numbers

**Reliable Satellites** (verified working):
- Space Stations: ISS (25544), Tiangong (48274)
- Earth Observation: NOAA-20 (43013), Terra (25994), Landsat 9 (49260), GOES-16 (41866)
- Science: Hubble (20580)

### CelesTrak Rate Limiting (403 Forbidden Error)

**Symptoms**:
- Error: "403 Client Error: Forbidden for url: https://celestrak.org/..."
- Error: "Could not download ISS TLE data from CelesTrak"
- Dashboard stops loading

**Why This Happens**:
- CelesTrak may rate-limit requests if you make too many in a short time
- Common when testing "Show Full Traffic" mode repeatedly
- CelesTrak protects their servers from excessive requests

**Solutions**:

1. **Wait and Retry** (Recommended):
   - Rate limits typically expire after 15-30 minutes
   - Wait a few minutes, then refresh the dashboard
   - The system automatically tries 3LE format first (more reliable)

2. **Use Local File Mode** (Temporary):
   - Edit `src/dashboard.py` line 1827
   - Change `use_local = False` to `use_local = True`
   - This uses `data/iss_tle.json` (may be a few days old)
   - Switch back to API mode later for fresh data

3. **Reduce Traffic Density**:
   - If using "Show Full Traffic", reduce the slider to 30-50 objects
   - Fewer requests = less likely to trigger rate limits

4. **Be Respectful**:
   - The code includes a 500ms delay between requests
   - Don't rapidly toggle "Show Full Traffic" on/off
   - Space out your requests

**Prevention**:
- The dashboard uses 3LE format by catalog number (less likely to be rate-limited)
- User-Agent headers are included in all requests
- Automatic fallback to alternative formats if one fails

### Dashboard Refreshing Continuously (Refresh Loop)

**Symptoms**:
- Page keeps refreshing when zooming/rotating the 3D plot
- "Show Full Traffic" data appears to reload repeatedly
- Dashboard feels unresponsive during 3D plot interactions

**Why This Happens** (Fixed):
- Previously: Full traffic data was refetched on every Streamlit rerun
- Zoom/pan interactions triggered reruns, causing data refetch loops
- **This has been fixed with smart caching**

**Current Behavior** (After Fix):
- Full traffic data is cached in session state after first load
- Zoom/rotate interactions use cached data (no refetch)
- Only refetches when you change the traffic count slider
- Smooth, responsive 3D plot interactions

**If You Still Experience Issues**:
1. Clear browser cache and refresh
2. Disable and re-enable "Show Full Traffic" to reset cache
3. Check browser console for JavaScript errors

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