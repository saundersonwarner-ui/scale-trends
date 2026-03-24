import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Scale Trends", layout="centered", page_icon="⚖️")

# --- Initialize JS Storage ---
# We use a key-based approach to pull data directly from the user's browser
def get_local_storage(key):
    return streamlit_js_eval(js_expressions=f"localStorage.getItem('{key}')", key=f"get_{key}")

def set_local_storage(key, value):
    streamlit_js_eval(js_expressions=f"localStorage.setItem('{key}', '{value}')", key=f"set_{key}")

# --- Load Data ---
raw_data = get_local_storage("fitness_data_v2")
raw_settings = get_local_storage("fitness_settings_v2")

# Convert raw browser strings into DataFrames/Dicts
if raw_data:
    try:
        df = pd.read_json(raw_data)
        df['Date'] = pd.to_datetime(df['Date'])
        st.session_state.data = df
    except:
        st.session_state.data = pd.DataFrame(columns=['Date', 'Weight_kg', 'M1_val', 'M2_val'])
else:
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame(columns=['Date', 'Weight_kg', 'M1_val', 'M2_val'])

if raw_settings:
    import json
    st.session_state.settings = json.loads(raw_settings)
else:
    st.session_state.settings = {"Goal": 75.0, "M1": "Chest", "M2": "Waist"}

settings = st.session_state.settings
st.title("⚖️ Scale Trends")
st.caption("🔒 Private: Data is stored in your browser, not on our servers.")

# --- Sidebar ---
with st.sidebar:
    st.header("👤 Settings")
    new_goal = st.number_input("Goal Weight", value=float(settings['Goal']), step=0.1)
    m1_name = st.text_input("Measurement 1", value=settings['M1'])
    m2_name = st.text_input("Measurement 2", value=settings['M2'])
    
    if st.button("Save Profile"):
        new_set = {"Goal": new_goal, "M1": m1_name, "M2": m2_name}
        import json
        set_local_storage("fitness_settings_v2", json.dumps(new_set))
        st.success("Saved!")
        st.rerun()

    st.divider()
    csv_out = st.session_state.data.to_csv(index=False).encode('utf-8')
    st.download_button("Export Backup (CSV)", data=csv_out, file_name="my_trends.csv")

# --- Input ---
with st.expander("➕ Log Entry"):
    date = st.date_input("Date", datetime.now())
    w = st.number_input("Weight (kg)", 0.0, 500.0, 0.0)
    m1 = st.number_input(settings['M1'], 0.0, 500.0, 0.0)
    m2 = st.number_input(settings['M2'], 0.0, 500.0, 0.0)
    
    if st.button("SAVE ENTRY"):
        new_row = pd.DataFrame([{
            'Date': pd.to_datetime(date), 
            'Weight_kg': w if w > 0 else None,
            'M1_val': m1 if m1 > 0 else None,
            'M2_val': m2 if m2 > 0 else None
        }])
        df = pd.concat([st.session_state.data, new_row]).drop_duplicates('Date', keep='last')
        df = df.dropna(subset=['Weight_kg', 'M1_val', 'M2_val'], how='all').sort_values('Date')
        
        # Save to Browser
        set_local_storage("fitness_data_v2", df.to_json())
        st.session_state.data = df
        st.success("Entry Saved Locally!")
        st.rerun()

# --- Visualization ---
df = st.session_state.data
if not df.empty:
    # 10-Day Trimmed Trend Logic
    if df['Weight_kg'].notnull().sum() >= 3:
        def trimmed_mean(s):
            return np.sort(s)[1:-1].mean() if len(s) >= 3 else np.mean(s)
        df['Trend'] = df['Weight_kg'].interpolate().rolling(10, min_periods=1).apply(trimmed_mean)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Weight_kg'], mode='markers', name='Actual'))
    if 'Trend' in df.columns:
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Trend'], mode='lines', name='Trend', line=dict(color='#00CC96', width=3)))
    
    fig.update_layout(height=400, margin=dict(l=0,r=0,b=0,t=20))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Start logging to see your private trend chart!")
