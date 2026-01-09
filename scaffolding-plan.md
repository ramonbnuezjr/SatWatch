# SatWatch Project Scaffolding Plan

## Project Overview

SatWatch is a satellite traffic monitoring system that tracks satellites in real-time, calculates their positions, and provides monitoring capabilities.

## Current Architecture

### Phase 1: Basic ISS Tracking (Current)
- Single script: `src/iss_tracker.py`
- Downloads TLE from CelesTrak
- Calculates position using Skyfield
- Prints formatted output

## Future Module Structure

```
satwatch/
├── src/
│   ├── satwatch/
│   │   ├── __init__.py
│   │   ├── tracker.py          # Core tracking logic
│   │   ├── tle_downloader.py   # TLE data fetching
│   │   ├── position_calculator.py  # Position calculations
│   │   ├── satellite.py        # Satellite data models
│   │   └── utils.py            # Helper functions
│   └── iss_tracker.py          # Entry point (current)
├── tests/
│   ├── test_tracker.py
│   ├── test_tle_downloader.py
│   └── test_position_calculator.py
└── data/
    └── cache/                  # Cached TLE files
```

## Module Responsibilities

### `tracker.py`
- Main tracking interface
- Orchestrates TLE download and position calculation
- Handles multiple satellites

### `tle_downloader.py`
- Downloads TLE data from CelesTrak
- Caches TLE data locally
- Validates TLE format
- Handles network errors

### `position_calculator.py`
- Parses TLE data
- Calculates satellite positions
- Converts to geographic coordinates
- Handles time calculations

### `satellite.py`
- Data models for satellites
- TLE data structures
- Position data structures

### `utils.py`
- Formatting functions
- Validation helpers
- Coordinate conversions

## Data Flow

```
CelesTrak API
    ↓
TLE Downloader (downloads & caches)
    ↓
Position Calculator (parses TLE, calculates position)
    ↓
Tracker (orchestrates, formats output)
    ↓
Display/Export
```

## Future Enhancements

1. **Multi-satellite tracking**: Track multiple satellites simultaneously
2. **Visualization**: Map display showing satellite positions
3. **Real-time updates**: Continuous position updates
4. **Database**: Store historical positions
5. **API**: REST API for accessing satellite data
6. **Alerts**: Notifications for satellite events
7. **Web dashboard**: Browser-based interface

## Dependencies

- **skyfield**: Astronomical calculations
- **requests**: HTTP requests
- **numpy**: Numerical computations (Skyfield dependency)
- **Future**: matplotlib, folium (for visualization)

## Configuration

Future configuration file (`config.yaml`):
```yaml
satellites:
  - name: ISS
    norad_id: 25544
  - name: Hubble
    norad_id: 20580

tle:
  source: celestrak
  cache_duration: 3600  # seconds
  refresh_interval: 86400  # seconds
```

