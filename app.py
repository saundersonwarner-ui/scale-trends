import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_browser_storage import BrowserStorage # Capitalized Class name

# --- App Configuration ---
st.set_page_config(page_title="Scale Trends", layout="centered", page_icon="⚖️")

# --- Initialize Private Browser Storage ---
# This ensures data stays on the user's device.
storage = BrowserStorage()

def load_local_data():
    stored = storage.get("scale_trends_data")
    if stored:
        try:
            df = pd.DataFrame(stored)
            df['Date'] = pd.to_datetime(df['Date'])
            return df.sort_values('Date').reset_index(drop=True)
        except:
            pass
    return pd.DataFrame(columns=['Date', 'Weight_kg', 'M1_val', 'M2_val'])

def load_local_settings():
    stored = storage.get("scale_trends_settings")
    if stored:
        return stored
    return {"Goal_Weight": 75.0, "M1_Name": "Chest", "M2_Name": "Waist"}

# Initialize Session State
if 'data' not in st.session_state:
    st.session_state.data = load_local_data()
if 'settings' not in st.session_state:
    st.session_state.settings = load_local_settings()

settings = st.session_state.settings
st.title("⚖️ Scale Trends")
st.caption("Privacy First: Your data is stored locally in this browser.")

# --- SIDEBAR: SETTINGS & DATA MANAGEMENT ---
with st.sidebar:
    st.header("👤 Your Profile")
    new_goal = st.number_input("Goal Weight (kg)", value=float(settings['Goal_Weight']), step=0.1)
    
    st.divider()
    m1_label = st.text_input("Measurement 1 Name", value=settings['M1_Name'])
    m2_label = st.text_input("Measurement 2 Name", value=settings['M2_Name'])
    
    if st.button("Save Profile Settings", use_container_width=True):
        new_settings = {"Goal_Weight": new_goal, "M1_Name": m1_label, "M2_Name": m2_label}
        st.session_state.settings = new_settings
        storage.set("scale_trends_settings", new_settings)
        st.success("Settings Saved!")
        st.rerun()

    st.divider()
    st.subheader("💾 Backup & Sync")
    
    uploaded_file = st.file_uploader("Import CSV", type="csv")
    if uploaded_file is not None:
        if st.button("Merge to Browser", use_container_width=True):
            up_df = pd.read_csv(uploaded_file)
            up_df['Date'] = pd.to_datetime(up_df['Date'])
            combined = pd.concat([st.session_state.data, up_df], ignore_index=True)
            df = combined.sort_values('Date').drop_duplicates('Date', keep='last').reset_index(drop=True)
            st.session_state.data = df
            storage.set("scale_trends_data", df.to_dict(orient="records"))
            st.success("Imported!")
            st.rerun()

    csv_out = st.session_state.data.to_csv(index=False).encode('utf-8')
    st.download_button("Export CSV", data=csv_out, file_name="scale_trends_backup.csv", use_container_width=True)
    
    st.divider()
    view_option = st.selectbox("View Range", ["Monthly", "Quarterly", "Yearly", "All Time"])

# --- INPUT SECTION ---
with st.expander("➕ Log Progress", expanded=st.session_state.data.empty):
    date = st.date_input("Date", datetime.now())
    date_ts = pd.to_datetime(date)
    
    existing_row = st.session_state.data[st.session_state.data['Date'] == date_ts]
    is_existing = not existing_row.empty

    col_w, col_m1, col_m2 = st.columns(3)
    with col_w:
        w_in = st.number_input("Weight (kg)", min_value=0.0, step=0.1, value=0.0)
    with col_m1:
        m1_in = st.number_input(settings['M1_Name'], min_value=0.0, step=0.1, value=0.0)
    with col_m2:
        m2_in = st.number_input(settings['M2_Name'], min_value=0.0, step=0.1, value=0.0)
    
    if st.button("SAVE TO BROWSER", type="primary", use_container_width=True):
        df = st.session_state.data
        nw = round(w_in, 1) if w_in > 0 else None
        nm1 = round(m1_in, 1) if m1_in > 0 else None
        nm2 = round(m2_in, 1) if m2_in > 0 else None

        if nw is None and nm1 is None and nm2 is None:
            st.error("Enter a value > 0.")
        else:
            if is_existing:
                idx = existing_row.index[0]
                if nw is not None: df.at[idx, 'Weight_kg'] = nw
                if nm1 is not None: df.at[idx, 'M1_val'] = nm1
                if nm2 is not None: df.at[idx, 'M2_val'] = nm2
            else:
                new_entry = {'Date': date_ts, 'Weight_kg': nw, 'M1_val': nm1, 'M2_val': nm2}
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            
            df = df.replace(0, np.nan).dropna(subset=['Weight_kg', 'M1_val', 'M2_val'], how='all')
            df = df.sort_values('Date').reset_index(drop=True)
            
            st.session_state.data = df
            storage.set("scale_trends_data", df.to_dict(orient="records"))
            st.success("Saved Privately!")
            st.rerun()

# --- DASHBOARD & CHARTS ---
df = st.session_state.data.copy()

if not df.empty:
    ranges = {"Monthly": 30, "Quarterly": 90, "Yearly": 365, "All Time": 9999}
    start_date = pd.Timestamp.now().normalize() - timedelta(days=ranges[view_option])
    
    if df['Weight_kg'].notnull().any():
        def trimmed_mean(s):
            if len(s) >= 3: return np.sort(s)[1:-1].mean()
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
            
            if len(df) >= 10 and 'Weight_Trend' in df.columns:
                recent_t = df['Weight_Trend'].iloc[-1]
                prev_t = df['Weight_Trend'].iloc[-10]
                weekly_rate = (recent_t - prev_t) * (7 / 10)
                rem_kg = curr - goal
                
                if (rem_kg > 0 and weekly_rate < 0) or (rem_kg < 0 and weekly_rate > 0):
                    weeks_left = abs(rem_kg / weekly_rate)
                    p_date = datetime.now() + timedelta(weeks=weeks_left)
                    st.success(f"🎯 **Goal Prediction:** {p_date.strftime('%b %d, %Y')} ({weeks_left:.1f} weeks)")
            
            fig_w = go.Figure()
            fig_w.add_trace(go.Scatter(x=view_df['Date'], y=view_df['Weight_kg'], mode='markers', name='Actual', marker=dict(color='gray', opacity=0.4)))
            if 'Weight_Trend' in view_df.columns:
                fig_w.add_trace(go.Scatter(x=view_df['Date'], y=view_df['Weight_Trend'], mode='lines', name='10D Trend', line=dict(color='#00CC96', width=4)))
            fig_w.add_hline(y=goal, line_dash="dash", line_color="#FF4B4B")
            fig_w.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350, showlegend=False)
            st.plotly_chart(fig_w, use_container_width=True, config={'displayModeBar': False})

    with tab_m:
        m_df = view_df.dropna(subset=['M1_val', 'M2_val'], how='all')
        if not m_df.empty:
            fig_m = go.Figure()
            if m_df['M1_val'].notnull().any(): fig_m.add_trace(go.Scatter(x=m_df['Date'], y=m_df['M1_val'], name=settings['M1_Name'], line=dict(color='#AB63FA')))
            if m_df['M2_val'].notnull().any(): fig_m.add_trace(go.Scatter(x=m_df['Date'], y=m_df['M2_val'], name=settings['M2_Name'], line=dict(color='#FFA15A')))
            fig_m.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350, legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_m, use_container_width=True, config={'displayModeBar': False})
        
