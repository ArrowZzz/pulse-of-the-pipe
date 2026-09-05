import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import IsolationForest

# 1. Page Configuration & Custom Theme Injection
st.set_page_config(page_title="Pulse of the Pipe | Diagnostics", layout="wide", initial_sidebar_state="expanded")

# Injecting custom CSS to change the background color from default blue-ish dark to an industrial slate gray
st.markdown("""
<style>
    .stApp {
        background-color: #18181A;
    }
    div[data-testid="stSidebar"] {
        background-color: #111111;
    }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar Navigation & Multi-Sensor Array Controls
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/Ministry_of_Energy_Saudi_Arabia.svg/1200px-Ministry_of_Energy_Saudi_Arabia.svg.png", width=200)
st.sidebar.title("Asset & Network Controls")

selected_asset = st.sidebar.selectbox("🎯 Select Active Facility", [
    "Pump Station #03 (Yanbu)", 
    "Remote Valve V-102 (East-West)", 
    "Fuel Storage Tank B (Jeddah)"
])

selected_node = st.sidebar.selectbox("📍 Select Sensor Node", [
    "Node 01: Main Inlet Pipe", 
    "Node 02: Pump Casing", 
    "Node 03: Discharge Outlet",
    "Node 04: Bypass Valve"
])

# Invisible spacer to push the Diagnostic Controls to the bottom of the sidebar
st.sidebar.markdown("<div style='height: 80vh;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.subheader("Diagnostic Controls")

simulate_fault = st.sidebar.toggle(
    f"🚨 Inject Fault ({selected_node[-5:]})", 
    value=False, 
    key=f"fault_{selected_asset}_{selected_node}"
)

# 3. Robust Data Generator
def generate_telemetry(asset_name, node_name, inject_fault):
    seed_offset = abs(hash(asset_name + node_name)) % 10000
    np.random.seed(seed_offset)
    
    now = pd.Timestamp.now()
    times = [now - pd.Timedelta(minutes=i) for i in range(100)][::-1]
    
    pressure = 45.0 + np.random.normal(0, 0.3, 100)
    vibration = 2.1 + np.random.normal(0, 0.1, 100)
    temperature = 62.0 + np.random.normal(0, 0.4, 100)
    acoustic = 120.0 + np.random.normal(0, 3.0, 100)
    
    if inject_fault:
        np.random.seed(None)
        severity = np.random.choice([1.0, 2.5]) 
        acoustic[-15:] += np.linspace(30, 150 * severity, 15) + np.random.normal(0, 5, 15)
        vibration[-15:] += np.linspace(1.0, 3.5 * severity, 15) + np.random.normal(0, 0.2, 15)
        pressure[-15:] -= np.linspace(0.5, 3.0 * severity, 15) + np.random.normal(0, 0.2, 15)
        
    return pd.DataFrame({"Time": times, "Pressure": pressure, "Vibration": vibration, "Temp": temperature, "Acoustic": acoustic})

df = generate_telemetry(selected_asset, selected_node, simulate_fault)

# 4. Calibrated AI & Priority Scoring System
features = df[["Pressure", "Vibration", "Temp", "Acoustic"]]
iso_forest = IsolationForest(contamination=0.01, random_state=42).fit(features.iloc[:75])
anomaly_scores = iso_forest.decision_function(features.iloc[-10:])

is_warning = (anomaly_scores < -0.02).sum() >= 3
is_critical = (anomaly_scores < -0.15).sum() >= 3

# Calculate exact timestamps for the work order
last_check_time = df["Time"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")
anomaly_time = "N/A"

if is_warning or is_critical:
    # Find the exact timestamp where the anomaly started within the last 10 edge readings
    threshold = -0.15 if is_critical else -0.02
    anomalous_indices = np.where(anomaly_scores < threshold)[0]
    if len(anomalous_indices) > 0:
        first_anomaly_idx = anomalous_indices[0]
        anomaly_time = df.iloc[-10 + first_anomaly_idx]["Time"].strftime("%Y-%m-%d %H:%M:%S")

# 5. UI Layout - Tabs for Dashboard vs. Scheduling
st.title("🛢️ Pulse of the Pipe | Smart Inspection Platform")
st.markdown(f"**Live Edge Monitoring — {selected_asset} | {selected_node}**")

tab_monitor, tab_schedule = st.tabs(["📊 Live Diagnostics & Alarms", "👥 Workforce & Scheduling"])

with tab_monitor:
    # Status Banners & Timestamps
    if is_critical:
        st.error(f"🔴 **CRITICAL PRIORITY:** Severe deviation detected. Immediate failure risk. (Last Checked: {last_check_time})")
    elif is_warning:
        st.warning(f"🟠 **WARNING PRIORITY:** Early degradation signature detected. (Last Checked: {last_check_time})")
    else:
        st.success(f"✅ **STATUS NORMAL:** Node is operating securely within baseline. (Last Checked: {last_check_time})")

    if is_warning or is_critical:
        with st.expander(f"📄 Smart Work Order - {selected_node}", expanded=True):
            st.markdown(f"""
            * **Facility:** {selected_asset}
            * **Affected Node:** {selected_node}
            * **Severity Level:** {'Critical' if is_critical else 'Warning'}
            * **Time of Occurrence:** `{anomaly_time}`
            * **Last System Check:** `{last_check_time}`
            * **Predictive Diagnostics:** Vibroacoustic signature deviation detected. Immediate thermal and visual inspection required.
            """)
            c1, c2 = st.columns(2)
            c1.button("📸 Upload Thermal Image")
            c2.button("✅ Mark Resolved")

    # Live Sensor Metrics
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pressure", f"{df['Pressure'].iloc[-1]:.2f} bar")
    m2.metric("Vibration", f"{df['Vibration'].iloc[-1]:.2f} mm/s")
    m3.metric("Surface Temp", f"{df['Temp'].iloc[-1]:.1f} °C")
    m4.metric("Acoustic Emission", f"{df['Acoustic'].iloc[-1]:.0f} kHz")

    # 6. Dedicated Graphs for Each Sensor (2x2 Grid)
    st.markdown("### Telemetry Breakdown")
    
    def create_sensor_graph(data, y_col, title, line_color, upper_limit=None):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data["Time"], y=data[y_col], mode='lines', name=title, line=dict(color=line_color, width=2)))
        if upper_limit:
            fig.add_hline(y=upper_limit, line_dash="dash", line_color="gray", annotation_text="Upper Limit")
        fig.update_layout(
            title=title,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)', # Transparent background to blend with new CSS
            plot_bgcolor='rgba(0,0,0,0.2)',
            height=280,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        return fig

    # Row 1: Acoustic & Vibration (The primary predictive indicators)
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        st.plotly_chart(create_sensor_graph(df, "Acoustic", "Contact Acoustic Emission (kHz)", "#00FFAA", upper_limit=130), use_container_width=True)
    with row1_col2:
        st.plotly_chart(create_sensor_graph(df, "Vibration", "Vibration RMS (mm/s)", "#FF55AA"), use_container_width=True)

    # Row 2: Pressure & Temperature
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        st.plotly_chart(create_sensor_graph(df, "Pressure", "Internal Pressure (bar)", "#55AAFF"), use_container_width=True)
    with row2_col2:
        st.plotly_chart(create_sensor_graph(df, "Temp", "Surface Temperature (°C)", "#FFDA55"), use_container_width=True)

with tab_schedule:
    # Shifts and Scheduling Module
    st.subheader("Workforce Management")
    
    st.markdown("#### 🕒 Today's Active Shifts")
    st.markdown("""
    | Shift | Supervisor | Active Techs | Status |
    | :--- | :--- | :--- | :--- |
    | Morning (06:00 - 14:00) | Ahmed Al-Ghamdi | 4 | Completed |
    | Evening (14:00 - 22:00) | Khalid Al-Faisal | 3 | Active 🟢 |
    | Night (22:00 - 06:00) | Yasser Al-Shahrani | 2 | Standby 🟡 |
    """)
    
    st.markdown("#### 📅 Weekly Maintenance Scheduler")
    st.markdown("""
    | Date | Facility | Target Node | Task | Assigned Team | Priority |
    | :--- | :--- | :--- | :--- | :--- | :--- |
    | 2026-09-03 | Pump Station #03 | Node 01: Inlet | Routine Calibration | Alpha Team | Low |
    | 2026-09-03 | Pump Station #03 | Node 02: Casing | Acoustic Verification | Alpha Team | High |
    | 2026-09-04 | Remote Valve V-102 | Node 01: Main | Seal Inspection | Bravo Team | Medium |
    | 2026-09-05 | Tank B (Jeddah) | Node 04: Bypass | Thermal Scan | Charlie Team | Low |
    """)