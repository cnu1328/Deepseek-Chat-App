import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
import time
from groq import Groq
import os
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import tiktoken
import json
import http.client
from styles import load_common_stylings
from utils.utils import CommonFunctionClass, YouTubeServiceClass, StreamlitServiceClass, \
    AgentServiceClass

load_dotenv()

st.set_page_config(
    page_title="YouTube Video Processor",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_common_stylings()


def main():
    # Header
    st.markdown('<h1 class="main-header">🎥Amplify YouTube Video Summarizer</h1>', unsafe_allow_html=True)
    st.markdown("Upload an Excel file with YouTube links to get video summaries using AI!")
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Upload File")
        uploaded_file = st.file_uploader(
            "Choose an Excel file",
            type=['csv', 'xlsx', 'xls'],
            help="Upload a CSV or Excel file containing YouTube links"
        )

        selected_hours = st.selectbox(
            "⏰ Select Time Range",
            options=[24, 12, 6, 3, 1],
            format_func=lambda x: f"Last {x} Hour" if x == 1 else f"Last {x} Hours",
            index=0
        )
        
        if uploaded_file:
            st.success("File uploaded successfully!")
        
        st.markdown("---")
        st.markdown("### 📋 Instructions")
        st.markdown("""
        1. Upload an Excel/CSV file with YouTube links
        2. Click 'Process Videos' to start
        3. Download the results when complete
        """)
    
    if uploaded_file and selected_hours:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # st.subheader("📊 File Preview")
            # st.dataframe(df.head(), use_container_width=True)

            channel_ids = CommonFunctionClass.load_channel_ids_from_file(df)

            youtube_service = YouTubeServiceClass()
            streamlit_service = StreamlitServiceClass()
            agent_service = AgentServiceClass()

            all_videos_df, channel_stats, global_stats = youtube_service.get_recent_videos_and_stats_by_channels(channel_ids, selected_hours)

            st.session_state["results_df"] = all_videos_df
            st.session_state["channel_stats"] = channel_stats
            st.session_state["global_stats"] = global_stats
            # print(f"ALL Videos :: {all_videos_df} \n\n Channel Stats :: {channel_stats} \n\n Global Stats :: {global_stats}")
            st.markdown("---")
            
            if 'four_line_summary' not in all_videos_df.columns:
                streamlit_service.create_channel_details(all_videos_df, channel_stats, global_stats, True)

            if st.button("Generate Summaries for All Videos", type="primary", use_container_width=True):
                if len(all_videos_df) == 0:
                    st.error("The uploaded file is empty!")
                    return

                print("Generating Summaries")
                
                progress_bar = st.progress(0)
                status_text = st.empty()

                four_line_summaries = []
                two_line_summaries = []
                sentiments = []

                with st.spinner("🔄 Generating summaries... This may take a while."):
                    total = len(all_videos_df)

                    for i, row in all_videos_df.iterrows():
                        video_id = row["video_id"]
                        percent_complete = int(((i + 1) / total) * 100)

                        # status_text.text(f"Processing {i+1}/{total}: {row['title'][:50]}...")
                        status_text.text(f"Processing {i + 1}/{total} videos. Title : {row['title'][:50]}")

                        print(f"Fetching fourline Summary for video id : {video_id}")
                        summary = agent_service.run_summary_pipeline(video_id, 4)
                        four_line_summaries.append(summary)

                        print(f"Completed the Four line summary for video id : {video_id}")

                        # two_line_summary = agent_service.run_summary_pipeline(video_id=video_id, recent_summary=summary, value=2)
                        # two_line_summaries.append(two_line_summary)

                        # sentiment = agent_service.run_summary_pipeline(video_id=video_id, recent_summary=summary, value=1)
                        # sentiments.append(sentiment)

                        progress_bar.progress(percent_complete)

                    all_videos_df["four_line_summary"] = four_line_summaries
                    # all_videos_df["two_line_summary"] = two_line_summaries
                    # all_videos_df["sentiment"] = sentiments
                    st.session_state["download_df"] = all_videos_df

            if 'download_df' in st.session_state:   
                results_df = st.session_state['download_df']
                channel_stats = st.session_state["channel_stats"]
                global_stats = st.session_state["global_stats"]

                # Display results
                st.subheader("✅ Processing Results")
                st.dataframe(results_df, use_container_width=True)
                
                # Success/Error summary
                successful = len(results_df[~results_df['four_line_summary'].str.contains('error|failed|not available', case=False, na=False)])
                total = len(results_df)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Processed", total)
                with col2:
                    st.metric("Successful", successful)
                with col3:
                    st.metric("Failed", total - successful)

                download_df = results_df.copy()
                download_df['published_at'] = download_df['published_at'].dt.strftime('%Y-%m-%d - %I:%M %p')

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    download_df.to_excel(writer, index=False, sheet_name='YouTube_Results')
                
                st.download_button(
                    label="📥 Download Results (Excel)",
                    data=output.getvalue(),
                    file_name="youtube_video_summaries.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )

                streamlit_service.create_channel_details(results_df, channel_stats, global_stats)

        except Exception as e:
            st.markdown(f'<div class="error-box">Error loading file: {str(e)}</div>', unsafe_allow_html=True)
    
    elif not uploaded_file:
        st.markdown('<div class="info-box">Please upload an Excel or CSV file in the sidebar to get started.</div>', unsafe_allow_html=True)
    
if __name__ == "__main__":
    main()
