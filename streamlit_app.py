import streamlit as st
import requests
from datetime import datetime, timedelta
import math
import matplotlib.pyplot as plt

# Predefined locations
LOCATIONS = {
    "Dover": (51.1290, 1.3080),
    "Shaftesbury": (51.0050, -2.1930),
    "Custom": None
}

def fetch_forecast(api_key, lat, lon, variable, hours=6):
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=hours)
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": variable,
        "start_datetime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "end_datetime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.get("https://api.zeussubnet.com/forecast", headers=headers, params=params)
    if r.status_code == 200:
        return r.json()
    else:
        st.error(f"API call failed: {r.status_code} {r.text}")
        return None

def wind_speed_direction(u, v):
    speed_ms = math.sqrt(u**2 + v**2)
    speed_knots = speed_ms * 1.94384  # m/s → knots
    direction_deg = (math.degrees(math.atan2(u, v)) + 180) % 360
    return speed_knots, direction_deg

def deg_to_compass(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
            "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    ix = round(deg / 22.5) % 16
    return dirs[ix]

def plot_time_series(times, values, ylabel, color="b"):
    if not times or not values:
        st.warning("No data available to plot.")
        return [], []

    # Convert API times (UTC) to local time
    local_times = [datetime.fromisoformat(t).astimezone().strftime("%d-%b %H:%M") for t in times]

    fig, ax = plt.subplots()
    ax.plot(local_times, values, marker="o", color=color)
    ax.set_xlabel("Local Time")
    ax.set_ylabel(ylabel)
    ax.tick_params(axis='x', rotation=45)
    fig.tight_layout()
    st.pyplot(fig)
    return local_times, values

# --- STREAMLIT APP ---
st.title("Zeus Forecast Dashboard 🌦")

# Sidebar: API key entry
api_key = st.sidebar.text_input("Enter your Zeus API Key", type="password")
if not api_key:
    st.warning("Please enter your API key in the sidebar to load data.")
    st.stop()

# Sidebar: location + hours
location_choice = st.sidebar.selectbox("Select Location", list(LOCATIONS.keys()))
if LOCATIONS[location_choice]:
    lat, lon = LOCATIONS[location_choice]
else:
    lat = st.sidebar.number_input("Latitude", value=52.377956)
    lon = st.sidebar.number_input("Longitude", value=4.897070)

hours = st.sidebar.slider("Forecast Hours Ahead", 1, 48, 1)

# Sidebar reminder
st.sidebar.info("ℹ️ App starts on the **Overview tab** so no forecast credits are used until you open a forecast tab.")

# Tabs
tab0, tab1, tab2, tab3, tab4 = st.tabs(
    ["📋 Overview", "🌡 Temperature", "💧 Humidity", "☔ Precipitation", "🌬 Wind"]
)

with tab0:
    st.subheader("Welcome to Zeus Forecast Dashboard 🌦")
    st.write(
        """
        This dashboard provides weather forecasts using the **Zeus API**.  
        Use the sidebar to enter your API key, select a location, and adjust forecast hours.
        
        ⚠️ **No forecast credits are used until you open one of the forecast tabs.**
        """
    )

    # API Key usage check (doesn't consume forecast credits)
    if api_key:
        headers = {"Authorization": f"Bearer {api_key}"}
        r = requests.get("https://api.zeussubnet.com/api-keys/usage", headers=headers)
        if r.status_code == 200:
            usage = r.json()
            remaining = usage.get("credits_remaining", "N/A")
            limit = usage.get("credits_limit", "N/A")
            used = usage.get("credits_used", "N/A")
            resets_at = usage.get("resets_at", None)

            if resets_at:
                utc_time = datetime.fromisoformat(resets_at.replace("Z",""))
                local_time = utc_time.astimezone()  # convert to system local time
                reset_str = local_time.strftime("%d-%b %H:%M %Z")
            else:
                reset_str = "Unknown"

            st.success(
                f"**API Usage**\n\n"
                f"- Credits used: **{used}**\n"
                f"- Credits remaining: **{remaining} / {limit}**\n"
                f"- Resets at: **{reset_str}**"
            )
        else:
            st.warning(f"Could not fetch API usage (status {r.status_code})")
    else:
        st.info("Enter your API key in the sidebar to check usage.")

with tab1:
    st.subheader("Temperature Forecast")
    data = fetch_forecast(api_key, lat, lon, "2m_temperature", hours)
    if data:
        times = data["hourly"].get("time", [])
        temps_raw = data["hourly"].get("2m_temperature", [])
        temps_c = [t - 273.15 if t is not None else None for t in temps_raw]
        local_times, vals = plot_time_series(times, temps_c, "Temperature (°C)", color="red")
        st.info("ℹ️ Temperature is at **2 m AGL** and displayed in **°C**.")
        if vals:
            st.success(f"Latest Forecast: {vals[-1]:.1f} °C at {local_times[-1]}")

with tab2:
    st.subheader("Humidity Forecast")
    data = fetch_forecast(api_key, lat, lon, "relative_humidity_2m", hours)
    if data:
        times = data["hourly"].get("time", [])
        hums = data["hourly"].get("relative_humidity_2m", [])
        local_times, vals = plot_time_series(times, hums, "Relative Humidity (%)", color="blue")
        st.info("ℹ️ Humidity is at **2 m AGL** and displayed in **%**.")
        if vals:
            st.success(f"Latest Forecast: {vals[-1]:.0f}% at {local_times[-1]}")

with tab3:
    st.subheader("Precipitation Forecast")
    data = fetch_forecast(api_key, lat, lon, "total_precipitation", hours)
    if data:
        times = data["hourly"].get("time", [])
        vals_raw = data["hourly"].get("total_precipitation", [])
        vals_mm = [v * 1000 if v is not None else None for v in vals_raw]  # m → mm
        local_times, vals = plot_time_series(times, vals_mm, "Precipitation (mm)", color="green")
        st.info("ℹ️ Precipitation is shown as **total precipitation in millimetres (mm)**.")
        if vals:
            st.success(f"Latest Forecast: {vals[-1]:.1f} mm at {local_times[-1]}")

with tab4:
    st.subheader("Wind Forecast (100 m AGL)")
    u_var = "100m_u_component_of_wind"
    v_var = "100m_v_component_of_wind"
    u = fetch_forecast(api_key, lat, lon, u_var, hours)
    v = fetch_forecast(api_key, lat, lon, v_var, hours)
    if u and v:
        times = u["hourly"].get("time", [])
        u_vals = u["hourly"].get(u_var, [])
        v_vals = v["hourly"].get(v_var, [])

        speeds, dirs = [], []
        for uu, vv in zip(u_vals, v_vals):
            speed, d = wind_speed_direction(uu, vv)
            speeds.append(speed)
            dirs.append(d)

        local_times, vals = plot_time_series(times, speeds, "Wind Speed (kt)", color="purple")
        st.info("ℹ️ Wind is shown at **100 m AGL**, with speeds in **knots (kt)** "
                "and directions following the **meteorological convention** (0° = North).")

        if vals and dirs:
            last_dir = dirs[-1]
            compass_label = deg_to_compass(last_dir)
            fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
            ax.set_theta_zero_location("N")
            ax.set_theta_direction(-1)
            ax.arrow(math.radians(last_dir), 0, 0, 1,
                     width=0.03, color='b', alpha=0.8, length_includes_head=True)
            ax.set_title(f"Latest Wind Direction: {last_dir:.0f}° ({compass_label})", va='bottom')
            st.pyplot(fig)
            st.success(f"Latest Forecast: {vals[-1]:.1f} kt from {last_dir:.0f}° ({compass_label}) at {local_times[-1]}")
