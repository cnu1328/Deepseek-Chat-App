import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import pytz
from utils.utils import YouTubeSearcher
import io

# Configure Streamlit page
st.set_page_config(
    page_title="YouTube Video Search & Export",
    page_icon="🎥",
    layout="wide"
)

def create_video_details(videos_df):
    """Create detailed video information display"""
    if len(videos_df) == 0:
        st.info("No videos to display")
        return
    
    st.markdown("---")
    st.markdown("### 🎥 Video Details")
    
    # Sort by published date (newest first)
    sorted_videos = videos_df.sort_values('published_date', ascending=False)
    
    for _, video in sorted_videos.iterrows():
        with st.expander(f"📺 {video['video_title']} | {video['channel_name']}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                **{video['video_title']}**
                
                🏢 **Channel:** {video['channel_name']}
                
                🕒 **Published at:** *{video['published_date'].strftime('%I:%M %p - %Y-%m-%d')}*
                """)
                
                # Display description if available
                if 'description' in video and pd.notna(video['description']) and video['description'].strip():
                    description = video['description'][:200] + "..." if len(video['description']) > 200 else video['description']
                    st.markdown(f"📝 **Description:** {description}")
            
            with col2:
                st.markdown(f"[🔗 Watch Video]({video['video_link']})")
                
                # Show time since published
                now = datetime.now(pytz.timezone('Asia/Kolkata'))
                time_diff = now - video['published_date']
                
                if time_diff.days > 0:
                    time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    minutes = time_diff.seconds // 60
                    time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                
                st.markdown(f"⏰ *{time_ago}*")
            
            st.markdown("---")

def main():
    st.title("🎥 YouTube HashTag Video Search")
    st.markdown("Search YouTube videos by hashtags or keywords and export to Excel with date filtering")
    
    # Initialize session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'is_searching' not in st.session_state:
        st.session_state.is_searching = False
    
    # Time period selection
    st.sidebar.subheader("📅 Time Period")
    
    # Add option to choose between predefined periods or custom range
    time_mode = st.sidebar.radio(
        "Select time filter mode:",
        options=["Predefined Periods", "Custom Date-Time Range"],
        index=0
    )
    
    selected_period = None
    custom_start_time = None
    custom_end_time = None
    
    if time_mode == "Predefined Periods":
        time_periods = [
            ("Last 3 months", 90),
            ("Last 1 month", 30),
            ("Last 15 days", 15),
            ("Last 7 days", 7),
            ("Last 24 hours", 1),
            ("Last 12 hours", 0.5),
            ("Last 6 hours", 0.25),
            ("Last 1 hour", 0.042)  # 1/24 of a day
        ]
        
        selected_period = st.sidebar.selectbox(
            "Select a time period to search:",
            options=[period[0] for period in time_periods],
            index=0  
        )
    else:
        st.sidebar.markdown("**Select Date-Time Range:**")
        
        # Get current time in IST
        ist_tz = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist_tz)
        
        # Set default times to yesterday 10:30 AM to today 10:30 AM
        default_time = datetime.strptime("10:30", "%H:%M").time()
        yesterday = now_ist.date() - timedelta(days=1)
        today = now_ist.date()
        
        # Date inputs
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input(
                "From Date",
                value=yesterday,
                max_value=now_ist.date()
            )
        with col2:
            end_date = st.date_input(
                "To Date",
                value=today,
                max_value=now_ist.date()
            )
        
        # Time inputs
        col3, col4 = st.sidebar.columns(2)
        with col3:
            start_time = st.time_input(
                "From Time",
                value=default_time
            )
        with col4:
            end_time = st.time_input(
                "To Time",
                value=default_time
            )
        
        # Combine date and time
        custom_start_time = ist_tz.localize(datetime.combine(start_date, start_time))
        custom_end_time = ist_tz.localize(datetime.combine(end_date, end_time))
        
        # Validate date range
        if custom_start_time >= custom_end_time:
            st.sidebar.error("⚠️ Start date-time must be before end date-time!")
        else:
            duration = custom_end_time - custom_start_time
            st.sidebar.info(f"📊 Duration: {duration.days} days, {duration.seconds // 3600} hours")

    search_query = st.sidebar.text_input(
        "Enter hashtag or search query:",
        placeholder="#technology OR artificial intelligence",
        help="Use hashtags like #AI or keywords like 'machine learning'"
    )
    
    search_button = st.sidebar.button(
        "🚀 Start Search",
        use_container_width=True
    )
        
    
    # Search execution
    if search_button and not st.session_state.is_searching:

        if not search_query:
            st.error(f"Please enter Hashtag or Query")
        elif time_mode == "Custom Date-Time Range" and custom_start_time >= custom_end_time:
            st.error("⚠️ Invalid date-time range! Start must be before end.")
        else:
            st.session_state.is_searching = True
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Initialize searcher
                searcher = YouTubeSearcher()
                
                # Determine search parameters based on mode
                if time_mode == "Predefined Periods":
                    # Convert selected periods to days
                    period_mapping = {period[0]: period[1] for period in time_periods}
                    selected_days = period_mapping[selected_period]
                    
                    # Run async search with predefined period
                    results = asyncio.run(
                        searcher.search_videos_async(
                            query=search_query,
                            time_periods_days=[selected_days],
                            progress_callback=lambda p, s: (
                                progress_bar.progress(p),
                                status_text.text(s)
                            )
                        )
                    )
                else:
                    # Run async search with custom date-time range
                    results = asyncio.run(
                        searcher.search_videos_async(
                            query=search_query,
                            custom_start_time=custom_start_time,
                            custom_end_time=custom_end_time,
                            progress_callback=lambda p, s: (
                                progress_bar.progress(p),
                                status_text.text(s)
                            )
                        )
                    )
                
                st.session_state.search_results = results
                st.session_state.is_searching = False
                
                progress_bar.progress(1.0)
                status_text.text("✅ Search completed successfully!")
                
                st.success(f"Found {len(results)} videos!")
                
            except Exception as e:
                st.session_state.is_searching = False
                st.error(f"❌ Error during search: {str(e)}")
                return
    
    if st.session_state.search_results:
        st.subheader("📋 Search Results")
        
        # Convert to DataFrame
        display_df = pd.DataFrame(st.session_state.search_results)
        
        # Sort by published date (newest first)
        display_df = display_df.sort_values('published_date', ascending=False)
        
        # Display data in tabular format first
        st.dataframe(
            display_df[['channel_name', 'video_title', 'video_link', 'published_date']],
            use_container_width=True,
            hide_index=True
        )

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            # Format the DataFrame for Excel
            export_df = display_df.copy()
            export_df['published_date'] = export_df['published_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            export_df.to_excel(writer, index=False, sheet_name='YouTube Videos')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['YouTube Videos']
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        
        excel_buffer.seek(0)
        
        # Download button
        if time_mode == "Predefined Periods":
            sanitized_period = selected_period.replace(" ", "_")
            file_name = f"youtube_videos_{search_query.replace(' ', '_')}_{sanitized_period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        else:
            date_range = f"{custom_start_time.strftime('%Y%m%d')}_{custom_end_time.strftime('%Y%m%d')}"
            file_name = f"youtube_videos_{search_query.replace(' ', '_')}_custom_{date_range}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        st.download_button(
            label="📁 Download Excel File",
            data=excel_buffer.getvalue(),
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type='primary',
            use_container_width=True
        )
        
        # Summary statistics
        st.subheader("📈 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Videos", len(display_df))
        
        with col2:
            st.metric("Unique Channels", display_df['channel_name'].nunique())
        
        with col3:
            if len(display_df) > 0:
                avg_per_day = len(display_df) / max(1, (display_df['published_date'].max() - display_df['published_date'].min()).days)
                st.metric("Avg Videos/Day", f"{avg_per_day:.1f}")
        
        with col4:
            if len(display_df) > 0:
                latest_video = display_df['published_date'].max()
                hours_ago = (datetime.now(pytz.timezone('Asia/Kolkata')) - latest_video).total_seconds() / 3600
                st.metric("Latest Video", f"{hours_ago:.1f}h ago")
        
        # Video Details Section
        create_video_details(display_df)

if __name__ == "__main__":
    main()