import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# --- App Configuration ---
st.set_page_config(page_title="Scale Trends", layout="centered") 

# --- Data & Settings Persistence ---
DB_FILE = "fitness_data.csv"
SETTINGS_FILE = "settings.csv"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            # Migration/Cleanup Logic
            rename_map = {'Chest_cm': 'M1_val', 'Waist_cm': 'M2_val'}
            df = df.rename(columns=rename_map)
            for col in ['Date', 'Weight_kg', 'M1_val', 'M2_val']:
                if col not in df.columns:
                    df[col] = np.nan
            df['Date'] = pd.to_datetime(df['Date'])
            return df.sort_values('Date').reset_index(drop=True)
        except:
            pass
    return pd.DataFrame(columns=['Date', 'Weight_kg', 'M1_val', 'M2_val'])

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            return pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
        except:
            pass
    return {"Goal_Weight": 75.0, "M1_Name": "Chest", "M2_Name": "Waist"}

def save_all(df, settings_dict):
    df.to_csv(DB_FILE, index=False)
    pd.DataFrame([settings_dict]).to_csv(SETTINGS_FILE, index=False)

# Initialize Session State
if 'data' not in st.session_state:
    st.session_state.data = load_data()
if 'settings' not in st.session_state:
    st.session_state.settings = load_settings()

settings = st.session_state.settings
st.title("⚖️ Scale Trends")

# --- SIDEBAR: SETTINGS & DATA MANAGEMENT ---
with st.sidebar:
    st.header("App Settings")
    new_goal = st.number_input("Goal Weight (kg)", value=float(settings['Goal_Weight']), step=0.1, format="%.1f")
    
    st.divider()
    st.subheader("Custom Measurements")
    m1_label = st.text_input("Measurement 1 Name", value=settings['M1_Name'])
    m2_label = st.text_input("Measurement 2 Name", value=settings['M2_Name'])
    
    if st.button("Update Settings", use_container_width=True):
        settings.update({"Goal_Weight": new_goal, "M1_Name": m1_label, "M2_Name": m2_label})
        st.session_state.settings = settings
        save_all(st.session_state.data, settings)
        st.success("Settings Updated!")
        st.rerun()

    st.divider()
    st.subheader("Data Management")
    
    # CSV Upload
    uploaded_file = st.file_uploader("Import CSV", type="csv")
    if uploaded_file is not None:
        if st.button("Merge Uploaded Data", use_container_width=True):
            try:
                up_df = pd.read_csv(uploaded_file)
                up_df['Date'] = pd.to_datetime(up_df['Date'])
                # Combine and keep the most recent entry for each date
                combined = pd.concat([st.session_state.data, up_df], ignore_index=True)
                st.session_state.data = combined.sort_values('Date').drop_duplicates('Date', keep='last').reset_index(drop=True)
                save_all(st.session_state.data, settings)
                st.success("Merged!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # CSV Download
    csv_out = st.session_state.data.to_csv(index=False).encode('utf-8')
    st.download_button("Export to CSV", data=csv_out, file_name="scale_trends_backup.csv", mime='text/csv', use_container_width=True)

    st.divider()
    view_option = st.selectbox("View Range", ["Monthly", "Quarterly", "Yearly", "All Time"])

# --- INPUT SECTION ---
with st.expander("➕ Add or Edit Log", expanded=False):
    date = st.date_input("Date", datetime.now())
    date_ts = pd.to_datetime(date)
    
    # Check if data already exists for this date
    existing_row = st.session_state.data[st.session_state.data['Date'] == date_ts]
    is_existing = not existing_row.empty

    col_w, col_c,
