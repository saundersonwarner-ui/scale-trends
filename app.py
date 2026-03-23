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
        df = pd.read_csv(DB_FILE)
        # Fix for old column names (MIGRATION LOGIC)
        rename_map = {'Chest_cm': 'M1_val', 'Waist_cm': 'M2_val'}
        df = df.rename(columns=rename_map)
        
        # Ensure the columns exist even if the file was empty
        for col in ['Date', 'Weight_kg', 'M1_val', 'M2_val']:
            if col not in df.columns:
                df[col] = np.nan
                
        df['Date'] = pd.to_datetime(df['Date'])
        return df.sort_values('Date')
    return pd.DataFrame(columns=['Date', 'Weight_kg', 'M1_val', 'M2_val'])

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        return pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
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

# --- SIDEBAR: SETTINGS & CUSTOMIZATION ---
with st.sidebar:
    st.header("App Settings")
    
    # Goal Setting
    new_goal = st.number_input("Goal Weight (kg)", value=float(settings['Goal_Weight']), step=0.1, format="%.1f")
    
    st.divider()
    st.subheader("Custom Measurements")
    # Edit Names Here
    m1_label = st.text_input("Measurement 1 Name", value=settings['M1_Name'])
    m2_label = st.text_input("Measurement 2 Name", value=settings['M2_Name'])
    
    if st.button("Update Settings", use_container_width=True):
        settings.update({"Goal_Weight": new_goal, "M1_Name": m1_label, "M2_Name": m2_label})
        st.session_state.settings = settings
        save_all(st.session_state.data, settings)
        st.success("Settings Updated!")
        st.rerun()

    st.divider()
    view_option = st.selectbox("View Range", ["Monthly", "Quarterly", "Yearly", "All Time"])

# --- INPUT SECTION ---
with st.expander("➕ Add New Log", expanded=False):
    date = st.date_input("Date", datetime.now())
    col_w, col_c, col_wa = st.columns(3)
    with col_w:
        w_input = st.number_input("Weight (KG)", min_value=0.0, step=0.1, format="%.1f")
    with col_c:
        c_input = st.number_input(settings['M1_Name'], min_value=0, step=1)
    with col_wa:
        wa_input = st.number_input(settings['M2_Name'], min_value=0, step=1)
    
    if st.button("SAVE TO SCALE TRENDS", use_container_width=True, type="primary"):
        df = st.session_state.data
        date_ts = pd.to_datetime(date)
        if not df.empty and (df['Date'] == date_ts).any():
            idx = df.index[df['Date'] == date_ts][0]
            if w_input > 0: df.at[idx, 'Weight_kg'] = round(w_input, 1)
            if c_input > 0: df.at[idx, 'M1_val'] = int(c_input)
            if wa_input > 0: df.at[idx, 'M2_val'] = int(wa_input)
        else:
            new_row = {'Date': date_ts, 
                       'Weight_kg': round(w_input, 1) if w_input > 0 else None,
                       'M1_val': int(c_input) if c_input > 0 else None,
                       'M2_val': int(wa_input) if wa_input > 0 else None}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        df = df.sort_values('Date').reset_index(drop=True)
        st.session_state.data = df
        save_all(df, settings)
        st.success("Data Synced!")
        st.rerun()

# --- DATA PROCESSING & DASHBOARD ---
df = st.session_state.data.copy()
goal_w = settings['Goal_Weight']
chart_config = {'staticPlot': False, 'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False, 'showAxisDragHandles': False}

if not df.empty:
    today = pd.Timestamp.now()
    ranges = {"Monthly": 30, "Quarterly": 90, "Yearly": 365, "All Time": 9999}
    start_date = today - timedelta(days=ranges[view_option])
    
    # Weight Analysis
    if df['Weight_kg'].notnull().any():
        roll = df['Weight_kg'].rolling(window=5, center=True)
        df['is_outlier'] = (df['Weight_kg'] > roll.mean() + 2 * roll.std()) | (df['Weight_kg'] < roll.mean() - 2 * roll.std())
        df['Filtered_Weight'] = np.where(df['is_outlier'], np.nan, df['Weight_kg'])
        df['Weight_7D_Avg'] = df['Filtered_Weight'].interpolate().rolling(window=7, min_periods=1).mean()
    
    view_df = df[df['Date'] >= start_date]

    # --- DASHBOARD TABS ---
    tab_weight, tab_measure = st.tabs(["Weight Trend", f"Body Measurements"])

    with tab_weight:
        if not view_df.empty and view_df['Weight_kg'].notnull().any():
            curr = view_df['Weight_kg'].dropna().iloc[-1]
            st.metric("Current Weight", f"{curr:.1f} kg", delta=f"{curr - goal_w:.1f} to goal", delta_color="inverse")
            
            fig_w = go.Figure()
            fig_w.add_trace(go.Scatter(x=view_df['Date'], y=view_df['Weight_kg'], mode='markers', name='Raw', marker=dict(color='gray', opacity=0.3)))
            fig_w.add_trace(go.Scatter(x=view_df['Date'], y=view_df['Weight_7D_Avg'], mode='lines', name='Trend', line=dict(color='#00CC96', width=4)))
            fig_w.add_hline(y=goal_w, line_dash="dash", line_color="red")
            fig_w.update_xaxes(fixedrange=True)
            fig_w.update_yaxes(fixedrange=True)
            fig_w.update_layout(margin=dict(l=5, r=5, t=10, b=5), height=350, showlegend=False)
            st.plotly_chart(fig_w, use_container_width=True, config=chart_config)

    with tab_measure:
        m_df = view_df.dropna(subset=['M1_val', 'M2_val'], how='all')
        if not m_df.empty:
            fig_m = go.Figure()
            if m_df['M1_val'].notnull().any():
                fig_m.add_trace(go.Scatter(x=m_df['Date'], y=m_df['M1_val'], mode='lines+markers', name=settings['M1_Name'], line=dict(color='#AB63FA')))
            if m_df['M2_val'].notnull().any():
                fig_m.add_trace(go.Scatter(x=m_df['Date'], y=m_df['M2_val'], mode='lines+markers', name=settings['M2_Name'], line=dict(color='#FFA15A')))
            
            fig_m.update_xaxes(fixedrange=True)
            fig_m.update_yaxes(fixedrange=True)
            fig_m.update_layout(margin=dict(l=5, r=5, t=30, b=5), height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_m, use_container_width=True, config=chart_config)
        else:
            st.info(f"No measurement data logged yet.")

else:
    st.warning("Welcome to Scale Trends! Start by adding your first weight entry.")
