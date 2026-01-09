# SatWatch - Satellite Traffic Monitor

A Python project for tracking satellites in real-time, starting with the International Space Station (ISS).

## Project Status

**Current Phase**: Step 1 - Basic ISS Tracking ✅ **COMPLETE**

### What's Working ✅
- ✅ ISS position tracking from CelesTrak (text format)
- ✅ ISS position tracking from CelesTrak JSON API
- ✅ Local JSON file support with TLE data
- ✅ Automatic TLE line construction from orbital elements (fallback)
- ✅ Position calculation (latitude, longitude, altitude)
- ✅ Formatted output display
- ✅ Comprehensive error handling
- ✅ JSON validation tools
- ✅ **TESTED AND VERIFIED** - Scripts successfully tested and working

### Current Capabilities
- Download TLE data from CelesTrak (text or JSON)
- Load TLE data from local JSON files
- Calculate current ISS position using Skyfield
- Display position in human-readable format
- Handle both TLE lines and orbital elements in JSON

### Known Challenges & Solutions
- **Challenge**: Skyfield requires TLE lines, not just orbital elements
  - **Solution**: Script handles both formats, prefers TLE lines when available
- **Challenge**: JSON format from some sources lacks TLE lines
  - **Solution**: Added fallback to construct TLE lines from orbital elements
- **Challenge**: TLE line construction is complex
  - **Solution**: Implemented proper formatting functions, but prefer using TLE lines from CelesTrak

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed status and lessons learned.

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

The scripts will:
1. Load TLE data (from API or local file)
2. Calculate the ISS's current position (latitude, longitude, altitude)
3. Display the result in a formatted output

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
║                    Current Position                        ║
╠═══════════════════════════════════════════════════════════╣
║  Time:        2026-01-09 00:27:55 UTC                     ║
║  Latitude:     14.3471°                                    ║
║  Longitude:   -96.5131°                                     ║
║  Altitude:      414.28 km                                   ║
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
│   └── iss_tracker_json.py # ISS tracker (JSON format)
├── data/
│   ├── iss_tle.json        # Local JSON TLE data
│   └── README.md          # Data format documentation
├── validate_json.py        # JSON validation tool
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── CODE_EXPLANATION.md    # Detailed code walkthrough
├── TESTING_GUIDELINES.md  # Testing standards and practices
├── scaffolding-plan.md    # Future project structure
└── DOCUMENTATION_INDEX.md # Documentation overview and navigation
```

## What is TLE Data?

TLE (Two-Line Element) sets are a data format used to describe the orbit of Earth-orbiting objects. Each TLE contains:
- Satellite name
- Orbital parameters (inclination, eccentricity, etc.)
- Current position and velocity

TLE data is updated regularly (typically every few days) and is provided by organizations like CelesTrak.

## Next Steps

- [ ] Track multiple satellites
- [ ] Add visualization (map display)
- [ ] Real-time updates
- [ ] Historical tracking
- [ ] Alerts and notifications

## Documentation

This project includes comprehensive documentation:

- **README.md** (this file) - Project overview and quick start guide
- **QUICK_START.md** - Fast setup guide with examples
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

