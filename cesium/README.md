# SatWatch Cesium Viewer

A minimal CesiumJS frontend for visualizing precomputed satellite positions over time.

## Quick Start

### 1. Start a Local Server

The Cesium viewer needs to be served via HTTP (not file://). Use any of these methods:

```bash
# Python 3 (recommended)
cd cesium
python3 -m http.server 8080

# Or Node.js
npx serve cesium -p 8080
```

### 2. Open in Browser

Navigate to: **http://localhost:8080**

### 3. Load Data

- Click **"Load Sample Data"** to test with pre-generated sample data
- Or use **"Choose File"** to load your own JSON data
- Or run the export script to generate real data from TLE

### 4. Playback Controls

- **▶ Play** - Start time animation
- **⏸ Pause** - Pause animation
- **⏮ Reset** - Return to start time
- **Speed** - Select playback multiplier (1x to 600x)
- **Timeline** - Click/drag to scrub through time

## Generate Real Position Data

Use the export script to generate positions from your tracked satellites:

```bash
# Default: 90 minutes, 60-second steps, starting now
python3 src/export_cesium_data.py

# Custom duration and step
python3 src/export_cesium_data.py --duration 180 --step 30

# Specific start time
python3 src/export_cesium_data.py --time "2026-01-17T21:00:00Z"

# Custom output path
python3 src/export_cesium_data.py -o cesium/my-data.json
```

## Data Format

The viewer expects JSON in this format:

```json
{
  "epoch": "2026-01-17T21:00:00Z",
  "satellites": [
    {
      "id": "25544",
      "name": "ISS (ZARYA)",
      "type": "station",
      "positions": [
        { "time": "2026-01-17T21:00:00Z", "lat": 14.32, "lon": -96.54, "alt_km": 414.2 },
        { "time": "2026-01-17T21:01:00Z", "lat": 14.85, "lon": -95.87, "alt_km": 414.3 }
      ]
    }
  ]
}
```

### Object Types

| Type | Color | Description |
|------|-------|-------------|
| `station` | Red | Space stations (ISS, Tiangong) |
| `satellite` | Blue | Operational satellites |
| `debris` | Orange | Space debris |

## Files

```
cesium/
├── index.html           # Main HTML viewer
├── satwatch-cesium.js   # Visualization module
├── sample-data.json     # Sample test data
└── README.md            # This file
```

## Features

- **3D Globe** - CesiumJS WebGL globe with terrain
- **Time Animation** - Smooth interpolation between position samples
- **Path Trails** - 1-hour orbital trails behind each object
- **Object Info** - Click objects to see details
- **Timeline Scrubbing** - Jump to any point in time
- **Playback Speed** - 1x to 600x multiplier

## Technical Notes

- Uses `SampledPositionProperty` for smooth position interpolation
- Lagrange polynomial interpolation (degree 3)
- No orbital math in JavaScript - all positions precomputed
- Supports dozens to hundreds of objects
- CesiumJS 1.114 (loaded from CDN)

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge

WebGL support required.
