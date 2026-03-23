st.divider()
    st.subheader("Data Management")
    
    # --- CSV UPLOADER ---
    uploaded_file = st.file_uploader("Import CSV", type="csv")
    if uploaded_file is not None:
        if st.button("Merge Uploaded Data", use_container_width=True):
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                uploaded_df['Date'] = pd.to_datetime(uploaded_df['Date'])
                
                # Merge logic: combine, sort, and drop duplicates keeping the NEWEST version
                combined_df = pd.concat([st.session_state.data, uploaded_df], ignore_index=True)
                combined_df = combined_df.sort_values('Date').drop_duplicates('Date', keep='last')
                
                st.session_state.data = combined_df.reset_index(drop=True)
                save_all(st.session_state.data, settings)
                st.success("Data Merged Successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # --- CSV DOWNLOADER ---
    csv_data = st.session_state.data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Export to CSV",
        data=csv_data,
        file_name=f"scale_trends_backup_{datetime.now().strftime('%Y%m%d')}.csv",
        mime='text/csv',
        use_container_width=True
    )
