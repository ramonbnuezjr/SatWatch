# SatWatch Quick Start Guide

Get up and running with SatWatch in minutes!

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Internet connection (for downloading TLE data)

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `skyfield` - Satellite position calculations
- `requests` - HTTP requests for downloading TLE data
- `numpy` - Required by Skyfield

## Step 2: Choose Your Method

### Method A: Interactive Web Dashboard (Recommended) 🆕

1. **Run the dashboard**:
   ```bash
   streamlit run src/dashboard.py
   ```

2. **Open in browser**: The dashboard will open at `http://localhost:8501`

3. **Features**:
   - Interactive world map with ISS position
   - Real-time updates every 10 seconds
   - Sidebar with position data
   - Dark theme interface

See [DASHBOARD_README.md](DASHBOARD_README.md) for detailed dashboard documentation.

### Method C: Use Local JSON File (Command Line)

1. **Ensure you have a JSON file**:
   ```bash
   # Check if file exists
   ls data/iss_tle.json
   ```

2. **Validate your JSON file**:
   ```bash
   python validate_json.py
   ```

3. **Run the script**:
   ```bash
   python src/iss_tracker_json.py --local
   ```

### Method D: Download from CelesTrak (JSON Format)

```bash
python src/iss_tracker_json.py
```

This will:
- Download fresh TLE data from CelesTrak
- Calculate current ISS position
- Display results

### Method E: Download from CelesTrak (Text Format)

```bash
python src/iss_tracker.py
```

## Step 3: View Results

You should see output like this:

```
Loading ISS TLE data from local JSON file...
✓ JSON TLE data loaded successfully
  Satellite: ISS (ZARYA)
  NORAD ID: 1998-067A
  Epoch: 2026-01-08T12:00:03.881088

Parsing TLE data from JSON...
✓ TLE data parsed successfully

Calculating current ISS position...
✓ Position calculated successfully

╔═══════════════════════════════════════════════════════════╗
║              INTERNATIONAL SPACE STATION (ISS)            ║
║                    Current Position                        ║
╠═══════════════════════════════════════════════════════════╣
║  Time:        2026-01-09 00:27:55 UTC                     ║
║  Latitude:     14.3471°                                    ║
║  Longitude:   -96.5131°                                     ║
║  Altitude:      414.28 km                                   ║
╚═══════════════════════════════════════════════════════════╝
```

## Troubleshooting

### Issue: "Connection Failed" or "Site Can't Be Reached" (Dashboard)

**Symptoms**: Browser shows connection error when trying to access `http://localhost:8501`

**Solution**: The Streamlit server is not running. Restart it:

```bash
# Check if server is running
ps aux | grep -i streamlit | grep -v grep

# If not running, start it:
cd "/Users/ramonbnuezjr/AI Projects/satwatch"
streamlit run src/dashboard.py
```

**For persistent background execution**:
```bash
cd "/Users/ramonbnuezjr/AI Projects/satwatch"
nohup python3 -m streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &
```

**Verify it's working**:
```bash
curl http://localhost:8501
```

See [DASHBOARD_README.md](DASHBOARD_README.md) for detailed troubleshooting.

### Issue: "ModuleNotFoundError: No module named 'requests'"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "File not found: data/iss_tle.json"

**Solution**: 
- Create the `data/` directory: `mkdir -p data`
- Download JSON from CelesTrak or use the API method instead

### Issue: "ISS TLE data not found in JSON file"

**Solution**: 
- Run `python validate_json.py` to check your JSON structure
- Ensure your JSON contains an entry with NORAD_CAT_ID: 25544
- Check that TLE_LINE1 and TLE_LINE2 fields are present

### Issue: OpenSSL/LibreSSL Warning

**Solution**: This is harmless! The warning doesn't affect functionality. You can safely ignore it.

## Next Steps

- Read [CODE_EXPLANATION.md](CODE_EXPLANATION.md) to understand how the code works
- Check [PROJECT_STATUS.md](PROJECT_STATUS.md) for project status and challenges
- Review [JSON_APPROACH_EXPLANATION.md](JSON_APPROACH_EXPLANATION.md) for JSON format details

## Getting Help

- Check the [README.md](README.md) for overview
- Review [PROJECT_STATUS.md](PROJECT_STATUS.md) for known issues
- See [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for all documentation
