# SatWatch Architecture

## Design Philosophy: Deterministic, Not AI

<aside>
⚙️

**Key Insight:** SatWatch is a **deterministic, physics-based system** — not an AI/ML application. This is intentional.

</aside>

### What Powers SatWatch

| Component | What It Is | AI? |
| --- | --- | --- |
| TLE Fetching | HTTP calls to CelesTrak/Space-Track | ❌ No |
| Position Calculation | SGP4 propagation (Kepler's laws + perturbations) | ❌ No — it's **physics** |
| Collision Detection | Distance threshold (`< 5km` → HIGH RISK, `< 1km` → CRITICAL) | ❌ No — it's **rule-based** |
| Alerting | If risk > threshold → send email | ❌ No — it's **conditional logic** (planned) |

**Same input → same output. Every time.** That's deterministic.

### Why Deterministic Is a Feature

Satellite operators don't want:

> "There's a 73% chance this is concerning based on similar patterns..."
> 

They want:

> "Object A will be **0.8 km** from Object B at **14:32:07 UTC**. Take action."
> 

**Explainability and repeatability matter more than probabilistic inference** for safety-critical applications.

### Where AI Could Layer In (v2+)

- **Anomaly detection**: Flag unusual TLE patterns that might indicate bad data
- **Covariance analysis**: Model position *uncertainty* (probabilistic)
- **Natural language reports**: LLM-generated executive summaries
- **Predictive maintenance**: Learn which operators ignore alerts → adjust messaging

**But for MVP: Ship physics first, add intelligence later.**

---

## System Components

### Data Flow

```
CelesTrak API → TLE Data → Skyfield (SGP4) → Position Calculation → Dashboard/API
```

### Core Libraries

- **Skyfield**: Astronomical calculations and SGP4 propagation
- **Requests**: HTTP client for TLE data fetching
- **Streamlit**: Web dashboard framework
- **Folium/Plotly**: Visualization libraries

### Data Sources

- **Primary**: CelesTrak (public TLE data)
- **Format**: 3LE (three-line element) for TLE lines, JSON for metadata
- **Update Frequency**: TLE data typically valid for ~2 weeks

### Position Calculation

SatWatch uses **SGP4 (Simplified General Perturbations 4)** propagation:

1. **Input**: TLE data (Two-Line Element set)
2. **Propagation**: Skyfield's SGP4 implementation
3. **Output**: Geocentric position (latitude, longitude, altitude)
4. **Accuracy**: Suitable for LEO satellites (typically ±1-2 km)

**Why SGP4?**
- Industry standard for satellite position prediction
- Deterministic (same TLE + time = same position)
- Handles orbital perturbations (atmospheric drag, gravitational effects)
- Fast enough for real-time applications

---

## Current Architecture (MVP)

### Phase 1: Basic Tracking ✅
- Single satellite tracking (ISS)
- Position calculation
- Command-line interface

### Phase 2: Dashboard ✅
- Interactive web dashboard
- Real-time position updates
- 2D map visualization
- 3D orbit view

### Phase 3: Multi-Satellite Tracking ✅
- Multiple satellite tracking
- Proximity detection
- Color-coded visualization

### Future Phases (Planned)

- **Phase 4**: Collision risk assessment ✅ **IN PROGRESS** - Basic conjunction calculator implemented
- **Phase 5**: Alerting system
- **Phase 6**: Historical tracking
- **Phase 7**: API endpoints
- **Phase 8**: AI/ML enhancements (if needed)

---

## Design Decisions

### Why Not Use AI for Position Prediction?

1. **Physics is deterministic**: Orbital mechanics follow well-understood laws
2. **SGP4 is proven**: Used by NASA, ESA, and commercial operators
3. **Explainability**: Operators need to understand *why* a prediction was made
4. **Reliability**: Deterministic systems are easier to debug and verify
5. **Performance**: Physics-based calculations are fast and efficient

### Why Streamlit for Dashboard?

- **Rapid prototyping**: Fast iteration for MVP
- **Python-native**: Matches existing codebase
- **Interactive**: Built-in widgets and auto-refresh
- **Future**: Can migrate to React/Vue if needed

### Why JSON for TLE Storage?

- **Human-readable**: Easy to inspect and debug
- **Flexible**: Can store both TLE lines and orbital elements
- **Compatible**: Works with existing tools and APIs
- **Version control**: Easy to track changes in git

---

## Scalability Considerations

### Current Limitations

- **Single-threaded**: Dashboard runs in single process
- **In-memory**: No database for historical data
- **Synchronous**: API calls block execution

### Future Improvements

- **Database**: Store historical positions and TLE data
- **Background jobs**: Async TLE updates
- **Caching**: Reduce API calls to CelesTrak
- **API layer**: RESTful API for programmatic access
- **Microservices**: Separate dashboard, API, and processing services

---

## Security Considerations

### Current State (MVP)

- **Public data**: TLE data is publicly available
- **No authentication**: Dashboard is local-only
- **No sensitive data**: No user accounts or credentials

### Future Considerations

- **API authentication**: If exposing public API
- **Rate limiting**: Prevent abuse of CelesTrak API
- **Data validation**: Sanitize all inputs
- **Error handling**: Don't expose internal errors

---

## Testing Strategy

### Current Testing

- **Manual testing**: Verify position calculations
- **Integration tests**: Test TLE fetching and parsing
- **Validation**: JSON schema validation

### Future Testing

- **Unit tests**: Test individual functions
- **Property-based testing**: Test SGP4 calculations
- **End-to-end tests**: Test full data flow
- **Performance tests**: Measure calculation speed

---

## Documentation

- **README.md**: User-facing documentation
- **ARCHITECTURE.md**: This file - system design
- **CODE_EXPLANATION.md**: Code walkthrough
- **ERROR_RESOLUTION_LOG.md**: Troubleshooting guide
- **CHANGELOG.md**: Version history

---

**Last Updated**: January 2025
