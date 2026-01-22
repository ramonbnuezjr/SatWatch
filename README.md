# SatWatch - Satellite Traffic Monitor

A Python project for tracking satellites in real-time, starting with the International Space Station (ISS).

## Project Status

**Current Phase**: Step 1 - Basic ISS Tracking ✅ | Step 2 - Dashboard ✅ | Step 3 - Multi-Satellite ✅ | **Step 4 - Cesium 3D Globe ✅ NEW**

**Design Philosophy**: SatWatch uses deterministic physics (SGP4 propagation) for position calculations, not AI/ML. This ensures predictable, repeatable results for safety-critical satellite tracking. See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

### What's Working ✅
- ✅ ISS position tracking from CelesTrak (text format)
- ✅ ISS position tracking from CelesTrak JSON API
- ✅ Local JSON file support with TLE data
- ✅ Automatic TLE line construction from orbital elements (fallback)
- ✅ Position calculation (latitude, longitude, altitude)
- ✅ Formatted output display
- ✅ **Streamlit Dashboard** - Interactive web dashboard with real-time map
- ✅ **3D Orbit View** - 3D visualization with Plotly showing Earth, ISS, and orbit path
- ✅ **Orbital Shell Visualization** - Layer 1 implementation showing multiple satellites
- ✅ Comprehensive error handling
- ✅ JSON validation tools
- ✅ **Multi-Satellite Data Fetcher** - Fetches TLE data for multiple satellites
- ✅ **Satellites Configuration** - JSON config file for tracked satellites
- ✅ **Conjunction Risk Calculator** - Collision risk assessment between two satellites
- ✅ **Focus Mode** - Toggle to highlight your tracked satellites with nearby objects as secondary
- ✅ **Timeline Controls** - View satellite positions at any date/time (past or future)
- ✅ **CesiumJS 3D Globe** - Professional WebGL visualization with time animation
- ✅ **Demo Mode: Full Traffic** - Display 500-1000 satellites to show space traffic density
- ✅ **Space Statistics Panel** - Real numbers: 25,000+ tracked objects, ~500,000 debris pieces
- ✅ **TESTED AND VERIFIED** - Core ISS tracking and dashboard successfully tested and working

### In Progress / Known Issues ⚠️
- ⚠️ **Satellite Availability** - Some satellites may fail to load (see below)
- ✅ **Multi-Satellite Position Calculations** - Fixed by switching to 3LE format (includes TLE lines)
- ✅ **Multi-Satellite Visualization** - Should now work correctly with TLE lines available

### Why Some Satellites Fail to Load

When you see warnings like "Failed: STARLINK-1007 (44713)...", this is normal and expected:

| Reason | Example |
|--------|---------|
| **Satellite deorbited** | Starlink satellites are frequently retired |
| **Renamed/repositioned** | Constellation satellites get new designations |
| **Debris decayed** | Small debris burns up on re-entry |
| **Not publicly tracked** | Some objects restricted from public databases |
| **Catalog number changed** | NORAD IDs can be reassigned |

**Best Practice**: The `satellites.json` config only includes verified, stable satellites. If you add new satellites, test them first with CelesTrak: `https://celestrak.org/NORAD/elements/gp.php?CATNR={id}&FORMAT=3le`

### Current Capabilities
- Download TLE data from CelesTrak (text or JSON)
- Load TLE data from local JSON files
- Calculate current ISS position using Skyfield
- Display position in human-readable format (terminal output)
- **Interactive web dashboard** with real-time map visualization
- Handle both TLE lines and orbital elements in JSON
- Auto-refreshing dashboard updates every 10 seconds
- **Conjunction risk analysis** - Calculate collision risk between two satellites
- **Focus Mode** - Highlight your tracked satellites with nearby objects shown as secondary markers

### Known Challenges & Solutions
- **Challenge**: Skyfield requires TLE lines, not just orbital elements
  - **Solution**: Script handles both formats, prefers TLE lines when available
- **Challenge**: JSON format from some sources lacks TLE lines
  - **Solution**: Added fallback to construct TLE lines from orbital elements
- **Challenge**: TLE line construction is complex
  - **Solution**: Implemented proper formatting functions, but prefer using TLE lines from CelesTrak
- **Challenge**: Multi-satellite position calculations returning NaN
  - **Status**: ✅ Resolved - Changed API format to 3LE which provides TLE lines
  - **See**: [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed error documentation
- **Challenge**: NaN values causing dashboard map to crash
  - **Status**: ✅ Resolved - Added NaN validation and error handling
  - **See**: [ERROR_RESOLUTION_LOG.md](ERROR_RESOLUTION_LOG.md) for details

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed status, challenges, and lessons learned.
See [CHANGELOG.md](CHANGELOG.md) for recent changes and issue tracking.

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Install Dependencies

Open your terminal and run:

```bash
pip install -r requirements.txt
```

This will install:
- **skyfield**: For calculating satellite positions
- **requests**: For downloading TLE data from the internet
- **numpy**: Required by Skyfield for numerical calculations
- **streamlit**: Web dashboard framework
- **folium**: Interactive maps
- **streamlit-folium**: Folium integration for Streamlit

## Quick Start

### Option 1: Download TLE from CelesTrak (Text Format)

```bash
python src/iss_tracker.py
```

### Option 2: Download TLE from CelesTrak (JSON Format)

```bash
python src/iss_tracker_json.py
```

### Option 3: Use Local JSON File

```bash
python src/iss_tracker_json.py --local
```

### Option 4: Conjunction Risk Analysis 🆕

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from conjunction_risk import calculate_conjunction_risk, format_conjunction_report
from iss_tracker_json import load_iss_tle_from_file

# Load TLE data for two satellites
sat1 = load_iss_tle_from_file()  # ISS
sat2 = load_iss_tle_from_file()  # In practice, load different satellite

# Calculate risk
result = calculate_conjunction_risk(sat1, sat2, hours_ahead=48)
print(format_conjunction_report(result))
"
```

### Option 5: Interactive Web Dashboard 🆕

```bash
streamlit run src/dashboard.py
```

**Note**: If you get "Connection failed" or "Site can't be reached", the Streamlit server may not be running. Check if it's running with `ps aux | grep streamlit` and restart if needed. See [DASHBOARD_README.md](DASHBOARD_README.md) for troubleshooting.

The dashboard provides:
- Interactive world map with ISS position (2D Map View)
- 3D orbit visualization showing Earth, ISS position, and orbit path (3D Orbit View)
- Orbital shell visualization showing multiple satellites as "space highway"
- Multi-satellite tracking with color coding (stations=red, satellites=blue, debris=orange)
- Real-time updates every 10 seconds
- Sidebar with current position, altitude, and TLE data status
- Multi-satellite filters (show/hide by type, proximity radius)
- Dark theme interface
- Data source selection (local file or CelesTrak API)
- Comprehensive debug information for troubleshooting

### Option 6: CesiumJS 3D Globe Viewer 🆕

Professional-grade 3D visualization using CesiumJS with time animation.

```bash
# 1. Export satellite positions (generates cesium/satellite-positions.json)
python3 src/export_cesium_data.py --duration 120 --step 60

# 2. Start a local web server
cd cesium && python3 -m http.server 8080

# 3. Open http://localhost:8080 in your browser
```

**Features:**
- WebGL 3D globe with satellite imagery
- Time-dynamic animation with play/pause/scrub
- Color-coded objects (stations=red, satellites=blue, debris=orange)
- Orbital path trails
- Playback speed control (1x to 600x)

See [cesium/README.md](cesium/README.md) for detailed documentation.

---

The scripts will:
1. Load TLE data (from API or local file)
2. Calculate the ISS's current position (latitude, longitude, altitude)
3. Display the result in a formatted output (or interactive map for dashboard)

### Example Output

When you run the script successfully, you'll see:

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
║                    Current Position                       ║
╠═══════════════════════════════════════════════════════════╣
║  Time:        2026-01-09 00:27:55 UTC                     ║
║  Latitude:     14.3471°                                   ║
║  Longitude:   -96.5131°                                   ║
║  Altitude:      414.28 km                                 ║
╚═══════════════════════════════════════════════════════════╝
```

**Note**: You may see a warning about OpenSSL/LibreSSL. This is harmless and doesn't affect functionality.

### Validate Your JSON File

```bash
python validate_json.py
```

This checks if your JSON file has the required fields for ISS tracking.

## Project Structure

```
satwatch/
├── .cursor/
│   └── rules/              # Cursor AI rules and guidelines
│       ├── code-style.mdc
│       ├── instructions.mdc
│       ├── testing.mdc
│       └── data-handling.mdc
├── src/
│   ├── iss_tracker.py      # ISS tracker (text TLE format)
│   ├── iss_tracker_json.py # ISS tracker (JSON format)
│   ├── dashboard.py        # Streamlit web dashboard
│   ├── conjunction_risk.py # Collision risk calculator
│   └── export_cesium_data.py # Export positions for CesiumJS
├── cesium/                 # CesiumJS 3D globe viewer
│   ├── index.html          # Main viewer HTML
│   ├── satwatch-cesium.js  # Visualization module
│   ├── sample-data.json    # Sample test data
│   └── README.md           # Cesium documentation
├── data/
│   ├── iss_tle.json        # Local JSON TLE data
│   └── README.md           # Data format documentation
├── satellites.json         # Tracked satellites configuration
├── validate_json.py        # JSON validation tool
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── ARCHITECTURE.md         # System design and roadmap
├── DASHBOARD_README.md     # Dashboard documentation
├── CODE_EXPLANATION.md     # Detailed code walkthrough
├── TESTING_GUIDELINES.md   # Testing standards and practices
├── scaffolding-plan.md     # Future project structure
└── DOCUMENTATION_INDEX.md  # Documentation overview and navigation
```

## What is TLE Data?

TLE (Two-Line Element) sets are a data format used to describe the orbit of Earth-orbiting objects. Each TLE contains:
- Satellite name
- Orbital parameters (inclination, eccentricity, etc.)
- Current position and velocity

TLE data is updated regularly (typically every few days) and is provided by organizations like CelesTrak.

## Development Roadmap

### Core Phases (Complete)

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Basic ISS Tracking | ✅ Complete | TLE download, position calculation, terminal output |
| Phase 2: Dashboard | ✅ Complete | Streamlit web UI with 2D/3D visualization |
| Phase 3: Multi-Satellite | ✅ Complete | Track multiple satellites, proximity detection |
| Phase 4: Collision Risk | ✅ Complete | Conjunction risk calculator |

### UI Enhancement Phases (2026)

| Phase | Status | Description |
|-------|--------|-------------|
| UI Phase 1: Timeline | ✅ Complete | Datetime picker for past/future viewing |
| UI Phase 2: Search | ✅ Complete | Filter satellites by name or NORAD ID |
| UI Phase 3: Orbital Data | ✅ Complete | Display orbital parameters (inclination, period, etc.) |
| UI Phase 4: Enhanced List | ✅ Complete | Visibility toggles, grouping, favorites |

### Cesium Bridge Phases (2026)

| Phase | Status | Description |
|-------|--------|-------------|
| Cesium Phase 1: MVP | ✅ Complete | CesiumJS 3D globe with time animation |
| Cesium Phase 2: Real-time | 📋 Planned | WebSocket updates, automated exports |
| Cesium Phase 3: Advanced | 📋 Planned | Conjunction lines, footprints, ground stations |

### Future Core Phases

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 5: Alerting | 📋 Planned | Notifications for conjunction events |
| Phase 6: Historical | 📋 Planned | Store and replay past positions |
| Phase 7: API | 📋 Planned | REST API for external integrations |
| Phase 8: AI/ML | 📋 Planned | Anomaly detection (if needed) |

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed phase descriptions.

## Documentation

This project includes comprehensive documentation:

- **README.md** (this file) - Project overview and quick start guide
- **QUICK_START.md** - Fast setup guide with examples
- **DASHBOARD_README.md** - Streamlit dashboard guide and features
- **ARCHITECTURE.md** - System design, architecture, and design philosophy
- **PROJECT_STATUS.md** - Current status, what's working, challenges faced
- **CODE_EXPLANATION.md** - Line-by-line explanation of the ISS tracker code
- **JSON_APPROACH_EXPLANATION.md** - Using JSON format with TLE data
- **TESTING_GUIDELINES.md** - Testing standards and best practices
- **scaffolding-plan.md** - Future project structure and architecture plans
- **DOCUMENTATION_INDEX.md** - Complete documentation overview and navigation guide
- **CHANGELOG.md** - Change history and updates

## Cursor AI Rules

This project uses Cursor AI rules (in `.cursor/rules/`) to guide code generation:
- `code-style.mdc` - Python coding conventions
- `instructions.mdc` - Project context and AI behavior
- `testing.mdc` - Testing patterns and guidelines
- `data-handling.mdc` - TLE parsing and Skyfield usage patterns

## Resources

- [CelesTrak](https://celestrak.org/) - TLE data source
- [Skyfield Documentation](https://rhodesmill.org/skyfield/)
- [NORAD Two-Line Element Sets](https://en.wikipedia.org/wiki/Two-line_element_set)

## License

This project is for educational purposes.

