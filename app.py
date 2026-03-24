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
            rename_map = {'Chest_cm': 'M1_val', 'Waist_cm': 'M2_val'}
            df = df.rename(columns=rename_map)
            for col in ['Date', 'Weight_kg', 'M1_val', 'M2_val']:
                if col not in df.columns:
                    df[col] = np.nan
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.replace(0, np.nan)
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
    
    uploaded_file = st.file_uploader("Import CSV", type="csv")
    if uploaded_file is not None:
        if st.button("Merge Uploaded Data", use_container_width=True):
            try:
                up_df = pd.read_csv(uploaded_file)
                up_df['Date'] = pd.to_datetime(up_df['Date'])
                up_df = up_df.replace(0, np.nan)
                combined = pd.concat([st.session_state.data, up_df], ignore_index=True)
                st.session_state.data = combined.sort_values('Date').drop_duplicates('Date', keep='last').reset_index(drop=True)
                save_all(st.session_state.data, settings)
                st.success("Merged!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    csv_out = st.session_state.data.to_csv(index=False).encode('utf-8')
    st.download_button("Export to CSV", data=csv_out, file_name="scale_trends_backup.csv", mime='text/csv', use_container_width=True)

    st.divider()
    view_option = st.selectbox("View Range", ["Monthly", "Quarterly", "Yearly", "All Time"])

# --- INPUT SECTION ---
with st.expander("➕ Add or Edit Log", expanded=False):
    date = st.date_input("Date", datetime.now())
    date_ts = pd.to_datetime(date)
    
    existing_row = st.session_state.data[st.session_state.data['Date'] == date_ts]
    is_existing = not existing_row.empty

    col_w, col_c, col_wa = st.columns(3)
    with col_w:
        w_input = st.number_input("Weight (KG)", min_value=0.0, step=0.1, format="%.1f", value=0.0)
    with col_c:
        c_input = st.number_input(settings['M1_Name'], min_value=0, step=1, value=0)
    with col_wa:
        wa_input = st.number_input(settings['M2_Name'], min_value=0, step=1, value=0)
    
    btn_col1, btn_col2 = st.columns([3, 1])
    
    with btn_col1:
        if st.button("SAVE TO SCALE TRENDS", use_container_width=True, type="primary"):
            df = st.session_state.data
            new_w = round(w_input, 1) if w_input > 0 else None
            new_m1 = int(c_input) if c_input > 0 else None
            new_m2 = int(wa_input) if wa_input > 0 else None

            if new_w is None and new_m1 is None and new_m2 is None:
                st.error("Please enter a value greater than 0.")
            else:
                if is_existing:
                    idx = existing_row.index[0]
                    if new_w is not None: df.at[idx, 'Weight_kg'] = new_w
                    if new_m1 is not None: df.at[idx, 'M1_val'] = new_m1
                    if new_m2 is not None: df.at[idx, 'M2_val'] = new_m2
                else:
                    new_entry = {'Date': date_ts, 'Weight_kg': new_w, 'M1_val': new_m1, 'M2_val': new_m2}
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                
                df = df.replace(0, np.nan).dropna(subset=['Weight_kg', 'M1_val', 'M2_val'], how='all')
                st.session_state.data = df.sort_values('Date').reset_index(drop=True)
                save_all(st.session_state.data, settings)
                st.success("Entry Synced!")
                st.rerun()

    with btn_col2:
        if is_existing:
            if st.button("DELETE", use_container_width=True):
                df = st.session_state.data
                st.session_state.data = df[df['Date'] != date_ts].reset_index(drop=True)
                save_all(st.session_state.data, settings)
                st.warning("Deleted.")
                st.rerun()

# --- DASHBOARD & CHARTS ---
df = st.session_state.data.copy()
chart_cfg = {'displayModeBar': False, 'scrollZoom': False, 'staticPlot': False}

if not df.empty:
    ranges = {"Monthly": 30, "Quarterly": 90, "Yearly": 365, "All Time": 9999}
    start_date = pd.Timestamp.now().normalize() - timedelta(days=ranges[view_option])
    
    # Calculate 10-Day Trimmed Weight Trend
    if df['Weight_kg'].notnull().any():
        def trimmed_mean(s):
            if len(s) >= 3:
                return np.sort(s)[1:-1].mean()
            return np.mean(s)
        
        df['Weight_Trend'] = df['Weight_kg'].interpolate().rolling(window=10, min_periods=1).apply(trimmed_mean)
    
    view_df = df[df['Date'] >= start_date]
    tab_w, tab_m = st.tabs(["Weight Trend", "Measurements"])

    with tab_w:
        valid_w = view_df.dropna(subset=['Weight_kg'])
        if not valid_w.empty:
            curr = valid_w['Weight_kg'].iloc[-1]
            goal = settings['Goal_Weight']
            st.metric("Current", f"{curr:.1f} kg", delta=f"{curr - goal:.1f} to goal", delta_color="inverse")
            
            # --- GOAL DATE PREDICTOR (Trimmed Trend) ---
            if len(df) >= 10 and 'Weight_Trend' in df.columns:
                recent_trend = df['Weight_Trend'].iloc[-1]
                prev_trend = df['Weight_Trend'].iloc[-10]
                weekly_rate = (recent_trend - prev_trend) * (7 / 10)
                remaining_kg = curr - goal
                
                if (remaining_kg > 0 and weekly_rate < 0) or (remaining_kg < 0 and weekly_rate > 0):
                    weeks_left = abs(remaining_kg / weekly_rate)
                    prediction_date = datetime.now() + timedelta(weeks=weeks_left)
                    st.success(f"🎯 **Goal Prediction:** {prediction_date.strftime('%b %d, %Y')} ({weeks_left:.1f} weeks)")
                elif abs(remaining_kg) < 0.1:
                    st.success("Goal Reached!")
                else:
                    st.info("📉 Not currently trending towards goal.")
            else:
                st.info("⏳ Log 10 days of data to see your Goal Predictor.")

            fig_w = go.Figure()
            fig_w.add_trace(go.Scatter(x=view_df['Date'], y=view_df['Weight_kg'], mode='markers', name='Raw', marker=dict(color='gray', opacity=0.4)))
            if 'Weight_Trend' in view_df.columns:
                fig_w.add_trace(go.Scatter(x=view_df['Date'], y=view_df['Weight_Trend'], mode='lines', name='Trend', line=dict(color='#00CC96', width=4)))
            fig_w.add_hline(y=goal, line_dash="dash", line_color="#FF4B4B")
            fig_w.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=350, showlegend=False, xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True))
            st.plotly_chart(fig_w, use_container_width=True, config=chart_cfg)
        else:
            st.info("No weight data in this range.")

    with tab_m:
        m_df = view_df.dropna(subset=['M1_val', 'M2_val'], how='all')
        if not m_df.empty:
            fig_m = go.Figure()
            if m_df['M1_val'].notnull().any():
                fig_m.add_trace(go.Scatter(x=m_df['Date'], y=m_df['M1_val'], mode='lines+markers', name=settings['M1_Name'], line=dict(color='#AB63FA')))
            if m_df['M2_val'].notnull().any():
                fig_m.add_trace(go.Scatter(x=m_df['Date'], y=m_df['M2_val'], mode='lines+markers', name=settings['M2_Name'], line=dict(color='#FFA15A')))
            fig_m.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=350, legend=dict(orientation="h", y=1.1, x=1, xanchor="right"), xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True))
            st.plotly_chart(fig_m, use_container_width=True, config=chart_cfg)
        else:
            st.info("No measurements logged yet.")
else:
    st.warning("Welcome! Start by adding your first entry above.")
