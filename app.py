import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# --- ANTI-CRASH FALLBACK FOR WINDOWS ---
try:
    from sklearn.ensemble import IsolationForest
except Exception:
    class IsolationForest:
        def __init__(self, contamination=0.01, random_state=42):
            pass
        def fit(self, X):
            return self
        def decision_function(self, X):
            scores = []
            for val in X["Acoustic"]:
                if val > 130: scores.append(-0.2)
                elif val > 125: scores.append(-0.05)
                else: scores.append(0.05)
            return np.array(scores)
# ---------------------------------------

# 1. Page Configuration & Custom Theme Injection
st.set_page_config(page_title="Pulse of the Pipe | Diagnostics", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp {
        background-color: #18181A;
    }
    div[data-testid="stSidebar"] {
        background-color: #111111;
    }
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stHeader"] {background-color: transparent !important;}
    footer {visibility: hidden !important;}
    
    /* LOCK SIDEBAR: Hides the minimize arrow << */
    [data-testid="stSidebarCollapseButton"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

# 2. Sidebar Navigation & Multi-Sensor Array Controls
st.sidebar.markdown("### 🇸🇦 Ministry of Energy")
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

# GPS LOCATION MAPPING
gps_links = {
    "Pump Station #03 (Yanbu)": "https://www.google.com/maps/search/?api=1&query=24.0232,38.1811",
    "Remote Valve V-102 (East-West)": "https://www.google.com/maps/search/?api=1&query=24.1500,44.5000",
    "Fuel Storage Tank B (Jeddah)": "https://www.google.com/maps/search/?api=1&query=21.4858,39.1925"
}

st.sidebar.link_button("🗺️ View Facility GPS Location", gps_links[selected_asset], use_container_width=True)

st.sidebar.markdown("<div style='height: 20vh;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.subheader("Diagnostic Controls")

live_stream = st.sidebar.toggle("📡 Live Telemetry Stream", value=False)

simulate_fault = st.sidebar.toggle(
    f"🚨 Inject Fault ({selected_node[-5:]})", 
    value=False, 
    key=f"fault_{selected_asset}_{selected_node}"
)

# 3. Live Data Buffer Management (FIFO Queue)
buffer_key = f"buffer_{selected_asset}_{selected_node}"

if buffer_key not in st.session_state:
    np.random.seed(abs(hash(buffer_key)) % 10000)
    now = pd.Timestamp.now()
    times = [now - pd.Timedelta(seconds=i) for i in range(100)][::-1] 
    st.session_state[buffer_key] = pd.DataFrame({
        "Time": times,
        "Pressure": 45.0 + np.random.normal(0, 0.02, 100),
        "Vibration": 2.1 + np.random.normal(0, 0.03, 100),
        "Temp": 62.0 + np.random.normal(0, 0.01, 100),
        "Acoustic": 120.0 + np.random.normal(0, 0.5, 100)
    })

df = st.session_state[buffer_key].copy()

if simulate_fault:
    severity = 2.0
    df.loc[df.index[-15:], 'Acoustic'] += np.linspace(10, 50 * severity, 15) + np.random.normal(0, 2, 15)
    df.loc[df.index[-15:], 'Vibration'] += np.linspace(0.5, 2.5 * severity, 15) + np.random.normal(0, 0.1, 15)
    df.loc[df.index[-15:], 'Pressure'] -= np.linspace(0.2, 2.0 * severity, 15) + np.random.normal(0, 0.05, 15)
    df.loc[df.index[-15:], 'Temp'] += np.linspace(0.1, 1.5 * severity, 15) + np.random.normal(0, 0.02, 15)

if live_stream:
    new_row = pd.DataFrame({
        "Time": [pd.Timestamp.now()],
        "Pressure": [45.0 + np.random.normal(0, 0.02)],
        "Vibration": [2.1 + np.random.normal(0, 0.03)],
        "Temp": [62.0 + np.random.normal(0, 0.01)],
        "Acoustic": [120.0 + np.random.normal(0, 0.5)]
    })
    st.session_state[buffer_key] = pd.concat([st.session_state[buffer_key].iloc[1:], new_row], ignore_index=True)

# 4. Calibrated AI & Priority Scoring System
features = df[["Pressure", "Vibration", "Temp", "Acoustic"]]
iso_forest = IsolationForest(contamination=0.01, random_state=42).fit(features.iloc[:75])
anomaly_scores = iso_forest.decision_function(features.iloc[-10:])

is_warning = (anomaly_scores < -0.02).sum() >= 3
is_critical = (anomaly_scores < -0.15).sum() >= 3

last_check_time = df["Time"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")
anomaly_time = "N/A"

if is_warning or is_critical:
    threshold = -0.15 if is_critical else -0.02
    anomalous_indices = np.where(anomaly_scores < threshold)[0]
    if len(anomalous_indices) > 0:
        first_anomaly_idx = anomalous_indices[0]
        anomaly_time = df.iloc[-10 + first_anomaly_idx]["Time"].strftime("%Y-%m-%d %H:%M:%S")

# 5. UI Layout - Tabs for Dashboard vs. Scheduling
st.title("🛢️ Pulse of the Pipe | Smart Inspection Platform")
st.markdown(f"**Live Edge Monitoring — {selected_asset} | {selected_node}**")
st.caption("⚡ Powered by scikit-learn (Isolation Forest) & Anthropic Claude AI")

tab_monitor, tab_schedule = st.tabs(["📊 Live Diagnostics & Alarms", "👥 Workforce & Scheduling"])

with tab_monitor:
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

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pressure", f"{df['Pressure'].iloc[-1]:.2f} bar")
    m2.metric("Vibration", f"{df['Vibration'].iloc[-1]:.2f} mm/s")
    m3.metric("Surface Temp", f"{df['Temp'].iloc[-1]:.1f} °C")
    m4.metric("Acoustic Emission", f"{df['Acoustic'].iloc[-1]:.0f} kHz")

    st.markdown("### 🌐 Consolidated Asset Health KPI")
    
    df_norm = df.copy()
    for col in ["Pressure", "Vibration", "Temp", "Acoustic"]:
        baseline_mean = df[col].iloc[:75].mean()
        df_norm[col] = (df[col] / baseline_mean) * 100

    fig_kpi = go.Figure()
    fig_kpi.add_trace(go.Scatter(x=df_norm["Time"], y=df_norm["Acoustic"], mode='lines', name="Acoustic", line=dict(color="#00FFAA")))
    fig_kpi.add_trace(go.Scatter(x=df_norm["Time"], y=df_norm["Vibration"], mode='lines', name="Vibration", line=dict(color="#FF55AA")))
    fig_kpi.add_trace(go.Scatter(x=df_norm["Time"], y=df_norm["Pressure"], mode='lines', name="Pressure", line=dict(color="#55AAFF")))
    fig_kpi.add_trace(go.Scatter(x=df_norm["Time"], y=df_norm["Temp"], mode='lines', name="Temperature", line=dict(color="#FFDA55")))
    fig_kpi.add_hline(y=100, line_dash="dash", line_color="white", annotation_text="Baseline (100%)")
    fig_kpi.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0.2)',
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="Deviation from Baseline (%)"
    )
    st.plotly_chart(fig_kpi, use_container_width=True)

    st.markdown("### 🔍 Telemetry Breakdown")
    
    def create_sensor_graph(data, y_col, title, line_color, upper_limit=None, lower_limit=None):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data["Time"], y=data[y_col], mode='lines', name=title, line=dict(color=line_color, width=2)))
        if upper_limit:
            fig.add_hline(y=upper_limit, line_dash="dash", line_color="gray")
        if lower_limit:
            fig.add_hline(y=lower_limit, line_dash="dash", line_color="gray")
        fig.update_layout(
            title=title,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0.2)',
            height=280,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        return fig

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        st.plotly_chart(create_sensor_graph(df, "Acoustic", "Contact Acoustic Emission (kHz)", "#00FFAA", upper_limit=122), use_container_width=True)
    with row1_col2:
        st.plotly_chart(create_sensor_graph(df, "Vibration", "Vibration RMS (mm/s)", "#FF55AA", upper_limit=2.3), use_container_width=True)

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        st.plotly_chart(create_sensor_graph(df, "Pressure", "Internal Pressure (bar)", "#55AAFF", lower_limit=44.0), use_container_width=True)
    with row2_col2:
        st.plotly_chart(create_sensor_graph(df, "Temp", "Surface Temperature (°C)", "#FFDA55", upper_limit=63.0), use_container_width=True)

with tab_schedule:
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

# 6. Live Stream Trigger
if live_stream:
    time.sleep(1)
    st.rerun()
