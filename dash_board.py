import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from urllib.parse import urlparse
import re

# Page configuration
st.set_page_config(
    page_title="YouTube Analytics Dashboard",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #FF0000;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .channel-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .video-card {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        padding: 0.8rem;
        margin: 0.3rem 0;
        transition: all 0.3s ease;
    }
    
    .video-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }
    
    .sidebar-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #495057;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def load_sample_data():
    """Load sample data for demonstration"""
    return [
        {
            "channel_title": "TV9 Entertainment",
            "videos": [
                {
                    "video_id": "oU-56ou4Xpk",
                    "title": "Devi Sri Prasad : సినిమాకు ప్రాణం గా నిలుస్తున్న దేవీ మ్యూజిక్ | Kuberaa - TV9",
                    "published_at": "2025-06-22T05:11:57Z",
                    "video_url": "https://www.youtube.com/watch?v=oU-56ou4Xpk",
                    "channel_title": "TV9 Entertainment"
                },
                {
                    "video_id": "p8avuFvYQ8g",
                    "title": "Hari Hara Veera Mallu New Release Date | ఆలస్యమైనా.. అదిరిపోయే సెంటిమెంట్‌తో వస్తున్న వీరమల్లు -TV9",
                    "published_at": "2025-06-22T05:11:33Z",
                    "video_url": "https://www.youtube.com/watch?v=p8avuFvYQ8g",
                    "channel_title": "TV9 Entertainment"
                },
                {
                    "video_id": "_4bDIg2Id9E",
                    "title": "అమీర్‌కు అవమానం.. ఖాన్స్‌కు పరాభవం..! | Aamir Khan | Shah Rukh Khan | Salman Khan - TV9",
                    "published_at": "2025-06-22T05:12:00Z",
                    "video_url": "https://www.youtube.com/watch?v=_4bDIg2Id9E",
                    "channel_title": "TV9 Entertainment"
                }
            ]
        },
        {
            "channel_title": "TV10 Entertainment",
            "videos": [
                {
                    "video_id": "oU-56ou4Xpk",
                    "title": "Devi Sri Prasad : సినిమాకు ప్రాణం గా నిలుస్తున్న దేవీ మ్యూజిక్ | Kuberaa - TV9",
                    "published_at": "2025-06-22T05:11:57Z",
                    "video_url": "https://www.youtube.com/watch?v=oU-56ou4Xpk",
                    "channel_title": "TV9 Entertainment"
                },
                {
                    "video_id": "p8avuFvYQ8g",
                    "title": "Hari Hara Veera Mallu New Release Date | ఆలస్యమైనా.. అదిరిపోయే సెంటిమెంట్‌తో వస్తున్న వీరమల్లు -TV9",
                    "published_at": "2025-06-22T05:11:33Z",
                    "video_url": "https://www.youtube.com/watch?v=p8avuFvYQ8g",
                    "channel_title": "TV9 Entertainment"
                },
                {
                    "video_id": "_4bDIg2Id9E",
                    "title": "అమీర్‌కు అవమానం.. ఖాన్స్‌కు పరాభవం..! | Aamir Khan | Shah Rukh Khan | Salman Khan - TV9",
                    "published_at": "2025-06-22T05:12:00Z",
                    "video_url": "https://www.youtube.com/watch?v=_4bDIg2Id9E",
                    "channel_title": "TV9 Entertainment"
                }
            ]
        }
    ]



def process_data(data):
    """Process the JSON data into a structured format"""
    
    all_videos = []
    channel_stats = {}
    
    for channel_data in data:
        channel_name = channel_data["channel_title"]
        videos = channel_data["videos"]
        
        channel_stats[channel_name] = {
            "total_videos": len(videos)
        }
        
        for video in videos:
            published_date = datetime.fromisoformat(video["published_at"].replace('Z', '+00:00'))
            
            video_info = {
                "channel": channel_name,
                "video_id": video["video_id"],
                "title": video["title"],
                "published_at": published_date,
                "video_url": video["video_url"],
            }
            all_videos.append(video_info)

    return pd.DataFrame(all_videos), channel_stats

def create_channel_details(data):
    """Create detailed channel information"""
    # Process the data first
    df, channel_stats = process_data(data)
    
    st.markdown("### 🏢 Channel Details")
    
    for channel, stats in channel_stats.items():
        with st.expander(f"📺 {channel} | {stats["total_videos"]} videos"):
            
            st.markdown("**Recent Videos:**")
            channel_videos = df[df['channel'] == channel].sort_values('published_at', ascending=False)
            
            for _, video in channel_videos.iterrows():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                    **{video['title']}** | *{video['published_at'].strftime('%Y-%m-%d %H:%M')}* 
                    """)
                
                with col2:
                    st.markdown(f"[🔗 Watch]({video['video_url']})")
                st.markdown("---")
                
def main():
    # Header
    st.markdown('<h1 class="main-header">📺 YouTube Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="sidebar-header">⚙️ Dashboard Controls</div>', unsafe_allow_html=True)
        
        # Data input options
        data_source = st.radio(
            "Select Data Source:",
            ["Use Sample Data", "Upload JSON File", "Paste JSON Data"]
        )
        
        data = None
        
        if data_source == "Use Sample Data":
            data = load_sample_data()
            st.success("✅ Sample data loaded")
    
    if data:
        try:
            create_channel_details(data)
            
                
        except Exception as e:
            st.error(f"❌ Error processing data: {str(e)}")
            st.info("Please check your data format and try again.")

if __name__ == "__main__":
    main()