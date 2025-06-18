import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
import time
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq
import os
from urllib.parse import urlparse, parse_qs

# Page configuration
st.set_page_config(
    page_title="YouTube Video Processor",
    page_icon="🎥",
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
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def extract_video_id(youtube_url):
    """Extract video ID from various YouTube URL formats."""
    try:
        # Handle different YouTube URL formats
        if 'youtu.be/' in youtube_url:
            return youtube_url.split('youtu.be/')[-1].split('?')[0]
        elif 'youtube.com/watch' in youtube_url:
            parsed_url = urlparse(youtube_url)
            return parse_qs(parsed_url.query)['v'][0]
        elif 'youtube.com/embed/' in youtube_url:
            return youtube_url.split('embed/')[-1].split('?')[0]
        else:
            return None
    except:
        return None

def get_video_info(video_id):
    """Get video title and channel name using YouTube API or web scraping."""
    try:
        # Try to get info from YouTube's oEmbed API
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            title = data.get('title', 'Title not found')
            channel_name = data.get('author_name', 'Channel not found')
            return title, channel_name
        else:
            return None, None
    except Exception as e:
        st.error(f"Error fetching video info: {str(e)}")
        return None, None

def get_transcript(video_id):
    """Get transcript for a YouTube video."""
    try:
        # Try to get transcript in English first, then any available language
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        transcript = None
        
        # Try different approaches to get transcript
        try:
            # Try English first
            transcript = transcript_list.find_transcript(['en'])
        except:
            try:
                # Try manually created English transcript
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except:
                try:
                    # Try any manually created transcript
                    for t in transcript_list:
                        if t.is_manually_created:
                            transcript = t
                            break
                except:
                    pass
                
                # If no manual transcript, try auto-generated
                if not transcript:
                    try:
                        # Get any available transcript
                        available_transcripts = list(transcript_list)
                        if available_transcripts:
                            transcript = available_transcripts[0]
                    except:
                        return None
        
        if not transcript:
            return None
        
        # Fetch the transcript data
        transcript_data = transcript.fetch()
        
        # Handle different transcript data formats
        if isinstance(transcript_data, list):
            # Standard format: list of dictionaries with 'text' key
            full_transcript = " ".join([
                item.get('text', '') if isinstance(item, dict) else str(item.text)
                for item in transcript_data
            ])
        else:
            # Handle other formats
            full_transcript = str(transcript_data)
        
        return full_transcript.strip()
        
    except Exception as e:
        print(f"Error getting transcript for video {video_id}: {str(e)}")
        return None

def summarize_with_groq(transcript, groq_api_key):
    """Generate summary using Groq's DeepSeek model."""
    try:
        client = Groq(api_key=groq_api_key)
        
        # Limit transcript length to avoid token limits
        max_chars = 15000  # Approximate limit for context
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "..."
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at summarizing YouTube video content. Create concise, informative summaries that capture the key points and main message of the video."
                },
                {
                    "role": "user",
                    "content": f"Please provide a 5-6 line summary of this YouTube video transcript, focusing on the most important and valuable information:\n\n{transcript}"
                }
            ],
            model="deepseek-r1-distill-llama-70b",
            temperature=0.3,
            max_tokens=200
        )
        
        return chat_completion.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"Error generating summary with Groq: {str(e)}")
        return "Summary generation failed"

def process_youtube_links(df, groq_api_key, progress_bar, status_text):
    """Process all YouTube links in the dataframe."""
    results = []
    
    # Assume the first column contains YouTube URLs
    url_column = df.columns[0]
    youtube_urls = df[url_column].dropna().tolist()
    
    total_urls = len(youtube_urls)
    
    for i, url in enumerate(youtube_urls):
        try:
            status_text.text(f"Processing video {i+1}/{total_urls}: {url[:50]}...")
            
            # Extract video ID
            video_id = extract_video_id(url)
            if not video_id:
                results.append({
                    'youtube_url': url,
                    'channel_name': 'Invalid URL',
                    'title': 'Invalid URL',
                    'summary': 'Could not extract video ID from URL'
                })
                continue
            
            # Get video info
            title, channel_name = get_video_info(video_id)
            if not title or not channel_name:
                results.append({
                    'youtube_url': url,
                    'channel_name': 'Info not found',
                    'title': 'Info not found',
                    'summary': 'Could not fetch video information'
                })
                continue
            
            # Get transcript
            transcript = get_transcript(video_id)
            if not transcript:
                results.append({
                    'youtube_url': url,
                    'channel_name': channel_name,
                    'title': title,
                    'summary': 'Transcript not available for this video'
                })
                continue
            
            # Generate summary
            summary = summarize_with_groq(transcript, groq_api_key)
            
            results.append({
                'youtube_url': url,
                'channel_name': channel_name,
                'title': title,
                'summary': summary
            })
            
            # Update progress
            progress_bar.progress((i + 1) / total_urls)
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            st.error(f"Error processing {url}: {str(e)}")
            results.append({
                'youtube_url': url,
                'channel_name': 'Error',
                'title': 'Error',
                'summary': f'Processing error: {str(e)}'
            })
    
    status_text.text("Processing complete!")
    return pd.DataFrame(results)

def main():
    # Header
    st.markdown('<h1 class="main-header">🎥 YouTube Video Processor</h1>', unsafe_allow_html=True)
    st.markdown("Upload an Excel file with YouTube links to get video summaries using AI!")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Groq API Key input
        groq_api_key = st.text_input(
            "Groq API Key",
            type="password",
            help="Enter your Groq API key to generate summaries"
        )
        
        if not groq_api_key:
            st.markdown('<div class="info-box">Please enter your Groq API key to proceed.</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # File upload
        st.header("📁 Upload File")
        uploaded_file = st.file_uploader(
            "Choose an Excel file",
            type=['csv', 'xlsx', 'xls'],
            help="Upload a CSV or Excel file containing YouTube links"
        )
        
        if uploaded_file:
            st.success("File uploaded successfully!")
        
        st.markdown("---")
        st.markdown("### 📋 Instructions")
        st.markdown("""
        1. Enter your Groq API key
        2. Upload an Excel/CSV file with YouTube links
        3. Click 'Process Videos' to start
        4. Download the results when complete
        """)
    
    # Main content
    if uploaded_file and groq_api_key:
        try:
            # Read the uploaded file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.markdown('<div class="success-box">File loaded successfully!</div>', unsafe_allow_html=True)
            
            # Display file info
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            
            # Show preview
            st.subheader("📊 File Preview")
            st.dataframe(df.head(), use_container_width=True)
            
            # Process button
            if st.button("🚀 Process Videos", type="primary", use_container_width=True):
                if len(df) == 0:
                    st.error("The uploaded file is empty!")
                    return
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process the videos
                with st.spinner("Processing videos... This may take a while."):
                    results_df = process_youtube_links(df, groq_api_key, progress_bar, status_text)
                
                # Display results
                st.subheader("✅ Processing Results")
                st.dataframe(results_df, use_container_width=True)
                
                # Success/Error summary
                successful = len(results_df[~results_df['summary'].str.contains('error|failed|not available', case=False, na=False)])
                total = len(results_df)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Processed", total)
                with col2:
                    st.metric("Successful", successful)
                with col3:
                    st.metric("Failed", total - successful)
                
                # Download button
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    results_df.to_excel(writer, index=False, sheet_name='YouTube_Results')
                
                st.download_button(
                    label="📥 Download Results (Excel)",
                    data=output.getvalue(),
                    file_name="youtube_video_summaries.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
                
                # Display individual results for reference
                st.subheader("🔍 Detailed Results")
                for idx, row in results_df.iterrows():
                    with st.expander(f"Video {idx + 1}: {row['title'][:50]}..."):
                        st.write(f"**URL:** {row['youtube_url']}")
                        st.write(f"**Channel:** {row['channel_name']}")
                        st.write(f"**Title:** {row['title']}")
                        st.write(f"**Summary:** {row['summary']}")
                
        except Exception as e:
            st.markdown(f'<div class="error-box">Error loading file: {str(e)}</div>', unsafe_allow_html=True)
    
    elif not groq_api_key:
        st.markdown('<div class="info-box">Please enter your Groq API key in the sidebar to get started.</div>', unsafe_allow_html=True)
    
    elif not uploaded_file:
        st.markdown('<div class="info-box">Please upload an Excel or CSV file in the sidebar to get started.</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("**Note:** This application requires a valid Groq API key and processes YouTube videos that have available transcripts.")

if __name__ == "__main__":
    main()