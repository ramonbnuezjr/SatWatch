#!/usr/bin/env python3
"""
SatWatch - ISS Tracking Dashboard

A Streamlit dashboard that displays the International Space Station's
current position on an interactive world map with real-time updates.

Author: SatWatch Project
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import math
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import numpy as np

# Add src directory to path to import iss_tracker_json functions
sys.path.insert(0, str(Path(__file__).parent))
from iss_tracker_json import (
    load_iss_tle_from_file,
    download_iss_tle_json,
    parse_tle_from_json,
    calculate_iss_position
)
import requests
from skyfield.api import load, EarthSatellite


def get_iss_data(use_local: bool = True):
    """
    Get ISS TLE data and calculate current position.
    
    Args:
        use_local: If True, use local JSON file; if False, download from API
        
    Returns:
        tuple: (position_dict, json_data, error_message)
    """
    try:
        # Load or download TLE data
        if use_local:
            json_data = load_iss_tle_from_file()
        else:
            json_data = download_iss_tle_json()
        
        # Parse TLE and calculate position
        satellite = parse_tle_from_json(json_data)
        position = calculate_iss_position(satellite)
        
        return position, json_data, None
        
    except Exception as e:
        return None, None, str(e)


def download_multiple_satellites(group: str = 'active', limit: int = 500):
    """
    Download TLE data for multiple satellites from CelesTrak.
    
    Args:
        group: CelesTrak group name ('active', 'stations', 'starlink', 'weather', etc.)
        limit: Maximum number of satellites to download (to avoid overwhelming the visualization)
        
    Returns:
        list: List of satellite dictionaries with TLE data
    """
    url = "https://celestrak.org/NORAD/elements/gp.php"
    params = {
        'GROUP': group,
        'FORMAT': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Limit the number of satellites
        if limit and len(data) > limit:
            data = data[:limit]
        
        return data
    except Exception as e:
        st.warning(f"Could not download satellite data: {e}")
        return []


def calculate_satellite_positions(satellites_data: list, current_time: datetime):
    """
    Calculate 3D positions for multiple satellites.
    
    Args:
        satellites_data: List of satellite dictionaries with TLE data
        current_time: Current datetime object
        
    Returns:
        list: List of (x, y, z, name, altitude) tuples
    """
    from skyfield.api import load
    
    ts = load.timescale()
    skyfield_time = ts.from_datetime(current_time)
    
    positions = []
    
    for sat_data in satellites_data:
        try:
            # Parse TLE from JSON data
            satellite = parse_tle_from_json(sat_data)
            
            # Calculate position
            geocentric = satellite.at(skyfield_time)
            subpoint = geocentric.subpoint()
            
            lat = subpoint.latitude.degrees
            lon = subpoint.longitude.degrees
            alt = subpoint.elevation.km
            
            # Convert to x, y, z
            x, y, z = lat_lon_alt_to_xyz(lat, lon, alt)
            
            name = sat_data.get('OBJECT_NAME', 'Unknown')
            norad_id = sat_data.get('OBJECT_ID', 'Unknown')
            
            positions.append((x, y, z, name, alt, norad_id))
        except Exception as e:
            # Skip satellites that can't be parsed
            continue
    
    return positions


def create_altitude_bands(earth_radius: float = 6371.0):
    """
    Create visualization for altitude bands (LEO, MEO, GEO).
    
    Args:
        earth_radius: Earth radius in kilometers
        
    Returns:
        list: List of Plotly traces for altitude bands
    """
    bands = []
    
    # LEO: 160-2000 km
    leo_radius = earth_radius + 2000
    leo_x, leo_y, leo_z = create_earth_sphere(leo_radius, resolution=30)
    bands.append(go.Surface(
        x=leo_x, y=leo_y, z=leo_z,
        colorscale=[[0, 'rgba(0, 100, 255, 0.1)'], [1, 'rgba(0, 100, 255, 0.1)']],
        showscale=False,
        name='LEO (160-2000 km)',
        opacity=0.15
    ))
    
    # MEO: 2000-35786 km (show at 10000 km for visibility)
    meo_radius = earth_radius + 10000
    meo_x, meo_y, meo_z = create_earth_sphere(meo_radius, resolution=30)
    bands.append(go.Surface(
        x=meo_x, y=meo_y, z=meo_z,
        colorscale=[[0, 'rgba(255, 200, 0, 0.1)'], [1, 'rgba(255, 200, 0, 0.1)']],
        showscale=False,
        name='MEO (2000-35786 km)',
        opacity=0.1
    ))
    
    return bands


def is_data_fresh(epoch_str: str) -> tuple[bool, float]:
    """
    Check if TLE data is fresh (< 12 hours old).
    
    Args:
        epoch_str: Epoch string from TLE data
        
    Returns:
        tuple: (is_fresh, hours_old)
    """
    try:
        from datetime import datetime
        epoch_dt = datetime.fromisoformat(epoch_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        # Handle timezone-aware comparison
        if epoch_dt.tzinfo is None:
            epoch_dt = epoch_dt.replace(tzinfo=timezone.utc)
        
        time_diff = now - epoch_dt
        hours_old = time_diff.total_seconds() / 3600.0
        
        return hours_old < 12, hours_old
    except:
        return False, 999


def create_map(latitude: float, longitude: float, altitude: float):
    """
    Create a Folium map with ISS position marker.
    
    Args:
        latitude: ISS latitude in degrees
        longitude: ISS longitude in degrees
        altitude: ISS altitude in kilometers
        
    Returns:
        folium.Map: Map object with ISS marker
    """
    # Create map centered on ISS position
    m = folium.Map(
        location=[latitude, longitude],
        zoom_start=3,
        tiles='CartoDB dark_matter'  # Dark theme
    )
    
    # Add ISS marker
    folium.CircleMarker(
        location=[latitude, longitude],
        radius=10,
        popup=f'ISS<br>Altitude: {altitude:.2f} km',
        tooltip='International Space Station',
        color='red',
        fill=True,
        fillColor='red',
        fillOpacity=0.8,
        weight=2
    ).add_to(m)
    
    # Add a larger circle to show visibility area
    folium.Circle(
        location=[latitude, longitude],
        radius=2000000,  # ~2000 km radius (approximate visibility)
        popup='Approximate ISS visibility area',
        color='red',
        fill=False,
        weight=1,
        opacity=0.3
    ).add_to(m)
    
    return m


def lat_lon_alt_to_xyz(latitude: float, longitude: float, altitude: float, earth_radius: float = 6371.0) -> tuple[float, float, float]:
    """
    Convert latitude, longitude, and altitude to 3D Cartesian coordinates (x, y, z).
    
    Args:
        latitude: Latitude in degrees (-90 to 90)
        longitude: Longitude in degrees (-180 to 180)
        altitude: Altitude in kilometers above sea level
        earth_radius: Earth radius in kilometers (default: 6371 km)
        
    Returns:
        tuple: (x, y, z) coordinates in kilometers
    """
    # Convert degrees to radians
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    
    # Calculate radius from Earth center (Earth radius + altitude)
    r = earth_radius + altitude
    
    # Convert to Cartesian coordinates
    # x: points toward (0°N, 0°E) - intersection of equator and prime meridian
    # y: points toward (0°N, 90°E) - intersection of equator and 90°E meridian
    # z: points toward North Pole
    x = r * math.cos(lat_rad) * math.cos(lon_rad)
    y = r * math.cos(lat_rad) * math.sin(lon_rad)
    z = r * math.sin(lat_rad)
    
    return x, y, z


def calculate_orbit_path(satellite, start_datetime, duration_minutes: int = 90, step_minutes: int = 2):
    """
    Calculate ISS orbit path for the next N minutes.
    
    Args:
        satellite: Skyfield EarthSatellite object
        start_datetime: datetime object for start time
        duration_minutes: How many minutes into the future to calculate
        step_minutes: Time step between points (in minutes)
        
    Returns:
        list: List of (x, y, z) tuples representing orbit path
    """
    from skyfield.api import load
    
    ts = load.timescale()
    path_points = []
    
    # Calculate points along the orbit
    for minutes in range(0, duration_minutes + 1, step_minutes):
        # Calculate time for this point
        future_time = start_datetime + timedelta(minutes=minutes)
        skyfield_time = ts.from_datetime(future_time)
        
        # Calculate position at this time
        geocentric = satellite.at(skyfield_time)
        subpoint = geocentric.subpoint()
        
        # Convert to x, y, z
        lat = subpoint.latitude.degrees
        lon = subpoint.longitude.degrees
        alt = subpoint.elevation.km
        
        x, y, z = lat_lon_alt_to_xyz(lat, lon, alt)
        path_points.append((x, y, z))
    
    return path_points


def create_earth_sphere(earth_radius: float = 6371.0, resolution: int = 50):
    """
    Create a 3D sphere representing Earth.
    
    Args:
        earth_radius: Earth radius in kilometers
        resolution: Number of points for sphere resolution
        
    Returns:
        tuple: (x, y, z) arrays for sphere surface
    """
    # Create sphere using spherical coordinates
    theta = np.linspace(0, 2 * np.pi, resolution)  # Longitude
    phi = np.linspace(0, np.pi, resolution)       # Latitude
    
    theta, phi = np.meshgrid(theta, phi)
    
    # Convert to Cartesian coordinates
    x = earth_radius * np.sin(phi) * np.cos(theta)
    y = earth_radius * np.sin(phi) * np.sin(theta)
    z = earth_radius * np.cos(phi)
    
    return x, y, z


def create_3d_orbit_plot(position: dict, satellite, current_time, show_orbital_shell: bool = True, satellite_group: str = 'active', max_satellites: int = 500):
    """
    Create a 3D Plotly plot showing Earth, ISS position, orbit path, and orbital shell.
    
    Args:
        position: Dictionary with latitude, longitude, altitude
        satellite: Skyfield EarthSatellite object
        current_time: Current datetime object
        show_orbital_shell: If True, show multiple satellites as orbital shell
        satellite_group: CelesTrak group to download ('active', 'stations', 'starlink', etc.)
        max_satellites: Maximum number of satellites to display
        
    Returns:
        plotly.graph_objects.Figure: 3D plot figure
    """
    earth_radius = 6371.0  # km
    
    # Convert current ISS position to x, y, z
    iss_x, iss_y, iss_z = lat_lon_alt_to_xyz(
        position['latitude'],
        position['longitude'],
        position['altitude'],
        earth_radius
    )
    
    # Calculate orbit path for next 90 minutes
    from skyfield.api import load
    ts = load.timescale()
    skyfield_time = ts.from_datetime(current_time)
    
    orbit_path = calculate_orbit_path(satellite, current_time, duration_minutes=90, step_minutes=2)
    
    # Create Earth sphere
    earth_x, earth_y, earth_z = create_earth_sphere(earth_radius)
    
    # Create the 3D plot
    fig = go.Figure()
    
    # Add Earth sphere (semi-transparent gray)
    fig.add_trace(go.Surface(
        x=earth_x,
        y=earth_y,
        z=earth_z,
        colorscale='Greys',
        showscale=False,
        opacity=0.3,
        name='Earth'
    ))
    
    # Add orbital shell (multiple satellites) if enabled
    if show_orbital_shell:
        with st.spinner("Loading orbital shell data..."):
            # Download multiple satellites
            satellites_data = download_multiple_satellites(group=satellite_group, limit=max_satellites)
            
            if satellites_data:
                # Calculate positions for all satellites
                satellite_positions = calculate_satellite_positions(satellites_data, current_time)
                
                if satellite_positions:
                    # Separate ISS from other satellites
                    other_sats_x = []
                    other_sats_y = []
                    other_sats_z = []
                    other_sats_names = []
                    
                    for x, y, z, name, alt, norad_id in satellite_positions:
                        # Skip ISS (we'll show it separately in red)
                        if norad_id == '25544' or 'ISS' in name.upper():
                            continue
                        other_sats_x.append(x)
                        other_sats_y.append(y)
                        other_sats_z.append(z)
                        other_sats_names.append(f"{name} (Alt: {alt:.0f} km)")
                    
                    # Add all other satellites as white dots (orbital shell)
                    if other_sats_x:
                        fig.add_trace(go.Scatter3d(
                            x=other_sats_x,
                            y=other_sats_y,
                            z=other_sats_z,
                            mode='markers',
                            marker=dict(
                                size=3,
                                color='white',
                                symbol='circle',
                                opacity=0.8,
                                line=dict(width=0)
                            ),
                            name=f'Orbital Shell ({len(other_sats_x)} satellites)',
                            hovertemplate='%{text}<extra></extra>',
                            text=other_sats_names
                        ))
    
    # Add orbit path
    if orbit_path:
        path_x = [p[0] for p in orbit_path]
        path_y = [p[1] for p in orbit_path]
        path_z = [p[2] for p in orbit_path]
        
        fig.add_trace(go.Scatter3d(
            x=path_x,
            y=path_y,
            z=path_z,
            mode='lines',
            line=dict(color='red', width=3),
            name='ISS Orbit Path (90 min)',
            hovertemplate='Orbit Path<extra></extra>'
        ))
    
    # Add current ISS position (red dot, larger and more prominent)
    fig.add_trace(go.Scatter3d(
        x=[iss_x],
        y=[iss_y],
        z=[iss_z],
        mode='markers',
        marker=dict(
            size=12,
            color='red',
            symbol='circle',
            line=dict(width=2, color='darkred')
        ),
        name='ISS Current Position',
        hovertemplate=f'ISS<br>Lat: {position["latitude"]:.2f}°<br>Lon: {position["longitude"]:.2f}°<br>Alt: {position["altitude"]:.2f} km<extra></extra>'
    ))
    
    # Set camera angle to show Earth and orbit clearly
    # Adjust range based on whether orbital shell is shown
    if show_orbital_shell:
        # Wider range to show orbital shell (LEO extends to ~8,371 km from center)
        axis_range = 15000
        title_text = 'ISS 3D Orbit View - Orbital Shell'
    else:
        # Closer range for ISS-only view
        axis_range = 8000
        title_text = 'ISS 3D Orbit View'
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (km)', range=[-axis_range, axis_range], backgroundcolor='#0e1117', gridcolor='#333'),
            yaxis=dict(title='Y (km)', range=[-axis_range, axis_range], backgroundcolor='#0e1117', gridcolor='#333'),
            zaxis=dict(title='Z (km)', range=[-axis_range, axis_range], backgroundcolor='#0e1117', gridcolor='#333'),
            aspectmode='cube',
            camera=dict(
                eye=dict(x=2.0, y=2.0, z=1.5),  # Position camera to see Earth and orbit
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            ),
            bgcolor='#0e1117'
        ),
        title=dict(
            text=title_text,
            font=dict(color='white', size=20)
        ),
        height=700,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font=dict(color='white')
    )
    
    return fig


# Page configuration
st.set_page_config(
    page_title="SatWatch - ISS Tracker",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stSidebar {
        background-color: #1e1e1e;
    }
    h1 {
        color: #ffffff;
    }
    h2, h3 {
        color: #e0e0e0;
    }
    .stMetric {
        background-color: #262730;
    }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title("🛰️ SatWatch - ISS Tracker")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📊 ISS Status")
    
    # Data source selection
    use_local = st.radio(
        "Data Source",
        ["Local File", "CelesTrak API"],
        index=0,
        help="Choose to use local JSON file or download fresh data from CelesTrak"
    )
    
    # Get ISS data
    position, json_data, error = get_iss_data(use_local=(use_local == "Local File"))
    
    if error:
        st.error(f"❌ Error: {error}")
        st.stop()
    
    if position and json_data:
        # Current time
        current_time = datetime.now(timezone.utc)
        st.metric("Current Time (UTC)", current_time.strftime("%H:%M:%S"))
        st.caption(f"Date: {current_time.strftime('%Y-%m-%d')}")
        
        st.markdown("---")
        
        # ISS Position
        st.subheader("📍 Position")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Latitude", f"{position['latitude']:.4f}°")
        with col2:
            st.metric("Longitude", f"{position['longitude']:.4f}°")
        
        st.metric("Altitude", f"{position['altitude']:.2f} km")
        
        st.markdown("---")
        
        # TLE Data Info
        st.subheader("📡 TLE Data")
        epoch = json_data.get('EPOCH', 'Unknown')
        st.text(f"Epoch: {epoch}")
        
        # Data freshness
        is_fresh, hours_old = is_data_fresh(epoch)
        if is_fresh:
            st.success(f"✅ Data Fresh ({hours_old:.1f} hours old)")
        else:
            st.warning(f"⚠️ Data Old ({hours_old:.1f} hours old)")
        
        st.caption("TLE data is typically valid for ~2 weeks")
        
        st.markdown("---")
        
        # Satellite Info
        st.subheader("🛰️ Satellite Info")
        st.text(f"Name: {json_data.get('OBJECT_NAME', 'Unknown')}")
        st.text(f"NORAD ID: {json_data.get('NORAD_CAT_ID', 'Unknown')}")
        
        st.markdown("---")
        
        # 3D View Options
        st.subheader("🌐 3D View Options")
        show_orbital_shell = st.checkbox(
            "Show Orbital Shell",
            value=st.session_state.get('show_orbital_shell', True),
            help="Display multiple satellites as a 'space highway' around Earth",
            key='show_orbital_shell_checkbox'
        )
        st.session_state.show_orbital_shell = show_orbital_shell
        
        if show_orbital_shell:
            satellite_group = st.selectbox(
                "Satellite Group",
                ['active', 'stations', 'starlink', 'weather', 'noaa', 'goes', 'last-30-days'],
                index=0,
                help="Choose which group of satellites to display",
                key='satellite_group_select'
            )
            st.session_state.satellite_group = satellite_group
            
            max_satellites = st.slider(
                "Max Satellites",
                min_value=50,
                max_value=1000,
                value=st.session_state.get('max_satellites', 500),
                step=50,
                help="Maximum number of satellites to display (more = slower loading)",
                key='max_satellites_slider'
            )
            st.session_state.max_satellites = max_satellites
        else:
            satellite_group = 'active'
            max_satellites = 500
            st.session_state.satellite_group = satellite_group
            st.session_state.max_satellites = max_satellites

# Main content area
if position and json_data:
    # Create tabs for 2D map and 3D orbit view
    tab1, tab2 = st.tabs(["🗺️ 2D Map View", "🌐 3D Orbit View"])
    
    with tab1:
        st.subheader("🌍 ISS Current Position (2D Map)")
        
        # Create and display map with a stable, unchanging key to prevent flickering
        map_obj = create_map(
            position['latitude'],
            position['longitude'],
            position['altitude']
        )
        
        # Use a fixed key so the map doesn't get recreated on every rerun
        # The map will update its position internally without full recreation
        map_data = st_folium(
            map_obj, 
            width=1200, 
            height=600, 
            key="iss_tracker_map",  # Fixed key prevents recreation
            returned_objects=[]
        )
        
        # Additional info below map
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**Last Update:** {position['timestamp']}")
        with col2:
            st.info(f"**Speed:** ~7.66 km/s (orbital velocity)")
        with col3:
            st.info(f"**Orbit Period:** ~92 minutes")
    
    with tab2:
        st.subheader("🌐 ISS 3D Orbit View")
        
        # Get satellite object for orbit calculation
        try:
            satellite = parse_tle_from_json(json_data)
            current_time = datetime.now(timezone.utc)
            
            # Get orbital shell settings from sidebar (if available)
            show_shell = st.session_state.get('show_orbital_shell', True)
            sat_group = st.session_state.get('satellite_group', 'active')
            max_sats = st.session_state.get('max_satellites', 500)
            
            # Create 3D orbit plot with orbital shell
            fig_3d = create_3d_orbit_plot(
                position, 
                satellite, 
                current_time,
                show_orbital_shell=show_shell,
                satellite_group=sat_group,
                max_satellites=max_sats
            )
            
            # Display the 3D plot
            st.plotly_chart(fig_3d, use_container_width=True)
            
            # Info about 3D view
            st.info("**3D View Features:**")
            features_text = """
            - **Earth**: Semi-transparent gray sphere (radius: 6,371 km)
            - **ISS Position**: Red dot showing current location
            - **Orbit Path**: Red line showing predicted path for next 90 minutes
            - **Interactive**: Rotate, zoom, and pan to explore the 3D view
            """
            if show_shell:
                features_text += f"\n- **Orbital Shell**: White dots showing {max_sats} satellites from '{sat_group}' group"
            st.markdown(features_text)
            
        except Exception as e:
            st.error(f"Error creating 3D view: {e}")
            st.info("Make sure you have plotly installed: `pip install plotly`")
    
    # Auto-refresh indicator (below tabs)
    st.markdown("---")
    
    # Initialize refresh tracking
    if 'last_refresh_time' not in st.session_state:
        st.session_state.last_refresh_time = datetime.now(timezone.utc).timestamp()
    
    # Calculate time since last refresh
    current_timestamp = datetime.now(timezone.utc).timestamp()
    elapsed = current_timestamp - st.session_state.last_refresh_time
    
    # Show countdown
    remaining_seconds = max(0, 10 - int(elapsed))
    refresh_placeholder = st.empty()
    with refresh_placeholder:
        st.caption(f"🔄 Auto-refreshing in {remaining_seconds} seconds...")
    
    # Only rerun if 10 seconds have passed AND we haven't rerun recently
    if elapsed >= 10:
        st.session_state.last_refresh_time = current_timestamp
        # Use rerun with a small delay to prevent rapid loops
        import time
        time.sleep(0.5)  # Small delay to stabilize
        st.rerun()
else:
    st.error("Unable to load ISS position data. Please check your data source.")
