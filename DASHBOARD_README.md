# SatWatch Dashboard

A real-time Streamlit dashboard for tracking the International Space Station (ISS) position on an interactive world map.

## Features

- 🌍 **Interactive World Map**: Real-time ISS position displayed on a dark-themed map
- 📊 **Live Data**: Auto-refreshes every 10 seconds (smooth, no flickering)
- 📍 **Position Tracking**: Shows latitude, longitude, and altitude
- 📡 **TLE Data Status**: Displays data freshness indicator (< 12 hours = fresh)
- 🎨 **Dark Theme**: Professional, clean UI with dark theme
- 🔄 **Auto-Refresh**: Automatically updates position every 10 seconds
- ✅ **Stable Display**: Fixed flickering issues for smooth map updates

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
  - Data freshness indicator (✅ if < 12 hours old)
- **Satellite Info**:
  - Satellite name
  - NORAD catalog ID

### Data Source Selection
Choose between:
- **Local File**: Uses `data/iss_tle.json` (faster, no internet needed)
- **CelesTrak API**: Downloads fresh data from CelesTrak (requires internet)

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