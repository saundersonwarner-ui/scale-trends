import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# --- 1. APP CONFIG & STYLING ---
st.set_page_config(page_title="Scale Trends", layout="centered", page_icon="⚖️")

# Custom CSS for a cleaner mobile look
st.markdown("""
    <style>
    .main { max-width: 600px; margin: 0 auto; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE ---
DB_FILE = "scale_trends_data.csv"

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # Migration logic for older versions
        df = df.rename(columns={'Chest_cm': 'M1_val', 'Waist_cm': 'M2_val'})
        df['Date'] = pd.to_datetime(df['Date'])
        return df.sort_values('Date').reset_index(drop=True)
    return pd.DataFrame(columns=['Date', 'Weight_kg', 'M1_val', 'M2_val'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Initialize Session
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 3. SIDEBAR: SETTINGS & BACKUPS ---
with st.sidebar:
    st.header("⚙️ App Settings")
    goal_w = st.number_input("Goal Weight (kg)", value=75.0, step=0.1)
    m1_name = st.text_input("Measurement 1 Name", value="Chest")
    m2_name = st.text_input("Measurement 2 Name", value="Waist")
    
    st.divider()
    st.subheader("💾 Device Storage")
    
    # Export
    if not st.session_state.data.empty:
        csv_bytes = st.session_state.data.to_csv(index=False).encode('utf-8')
        st.download_button("Export Data to Device", data=csv_bytes, 
                           file_name=f"scale_trends_{datetime.now().strftime('%Y-%m-%d')}.csv", 
                           mime="text/csv", use_container_width=True)
    
    # Import
    uploaded = st.file_uploader("Import Backup CSV", type="csv")
    if uploaded:
        st.session_state.data = pd.read_csv(uploaded)
        save_data(st.session_state.data)
        st.success("Data Synced!")
        st.rerun()

st.title("⚖️ Scale Trends")

# --- 4. INPUT SECTION ---
with st.expander("➕ Add New Log", expanded=False):
    date_in = st.date_input("Date", datetime.now())
    c1, c2, c3 = st.columns(3)
    with c1: w_in = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
    with c2: val1 = st.number_input(m1_name, min_value=0.0, step=0.1)
    with c3: val2 = st.number_input(m2_name, min_value=0.0, step=0.1)
    
    if st.button("SAVE ENTRY", type="primary", use_container_width=True):
        new_row = pd.DataFrame([{'Date': pd.to_datetime(date_in), 'Weight_kg': w_in, 'M1_val': val1, 'M2_val': val2}])
        updated_df = pd.concat([st.session_state.data, new_row], ignore_index=True).sort_values('Date')
        st.session_state.data = updated_df
        save_data(updated_df)
        st.success("Entry Saved!")
        st.rerun()

# --- 5. GOAL PREDICTIONS & INSIGHTS ---
df = st.session_state.data
if not df.empty and df['Weight_kg'].notnull().any():
    # Calculate 7-Day Moving Average
    df['Trend'] = df['Weight_kg'].rolling(window=7, min_periods=1).mean()
    curr_w = df['Weight_kg'].iloc[-1]
    
    st.subheader("Progress Insights")
    
    # Prediction Logic with Smart Prompts
    if len(df) < 8:
        st.info("📉 **Status:** Gathering data. We need at least 8 logs to calculate a trend.")
    else:
        # Calculate weekly velocity (last 7 days vs previous 7 days)
        recent_avg = df['Trend'].iloc[-1]
        past_avg = df['Trend'].iloc[-8]
        weekly_rate = past_avg - recent_avg
        
        if curr_w <= goal_w:
            st.balloons()
            st.success(f"🎉 **Goal Reached!** You are currently {goal_w - curr_w:.1f}kg under your target.")
        elif weekly_rate <= 0:
            st.warning("⚖️ **Status:** Plateau/Maintenance. The goal date will reappear once a downward trend is detected over the last 7 days.")
        else:
            kg_to_go = curr_w - goal_w
            weeks_to_goal = kg_to_go / weekly_rate
            finish_date = datetime.now() + timedelta(weeks=weeks_to_goal)
            
            st.metric("Predicted Goal Date", finish_date.strftime('%d %B %Y'), 
                      delta=f"{weekly_rate:.2f} kg/week", delta_color="normal")
            st.caption(f"Estimated arrival at {goal_w}kg based on your recent 7-day velocity.")

    # --- 6. CHARTS ---
    tab1, tab2 = st.tabs(["Weight History", "Body Measurements"])
    
    chart_cfg = {'displayModeBar': False, 'staticPlot': False, 'scrollZoom': False}

    with tab1:
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(x=df['Date'], y=df['Weight_kg'], mode='markers', name='Actual', marker=dict(color='gray', opacity=0.3)))
        fig_w.add_trace(go.Scatter(x=df['Date'], y=df['Trend'], mode='lines', name='Trend', line=dict(color='#00CC96', width=3)))
        fig_w.add_hline(y=goal_w, line_dash="dash", line_color="red", annotation_text="Goal")
        fig_w.update_layout(margin=dict(l=0,r=0,t=20,b=0), height=350, showlegend=False)
        st.plotly_chart(fig_w, use_container_width=True, config=chart_cfg)

    with tab2:
        fig_m = go.Figure()
        if df['M1_val'].any(): fig_m.add_trace(go.Scatter(x=df['Date'], y=df['M1_val'], name=m1_name))
        if df['M2_val'].any(): fig_m.add_trace(go.Scatter(x=df['Date'], y=df['M2_val'], name=m2_name))
        fig_m.update_layout(margin=dict(l=0,r=0,t=20,b=0), height=350, legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_m, use_container_width=True, config=chart_cfg)

else:
    st.info("Welcome to Scale Trends! Start by adding your first weight entry above.")
