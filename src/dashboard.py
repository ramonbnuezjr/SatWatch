#!/usr/bin/env python3
"""
SatWatch - ISS Tracking Dashboard

A Streamlit dashboard that displays the International Space Station's
current position on an interactive world map with real-time updates.

Author: SatWatch Project
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
import folium
from streamlit_folium import st_folium

# Add src directory to path to import iss_tracker_json functions
sys.path.insert(0, str(Path(__file__).parent))
from iss_tracker_json import (
    load_iss_tle_from_file,
    download_iss_tle_json,
    parse_tle_from_json,
    calculate_iss_position
)


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

# Main content area
if position:
    with st.container():
        st.subheader("🌍 ISS Current Position")
        
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
        
        # Auto-refresh indicator
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
