from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta, timezone
import json
from typing import List
import os
import re
from collections import defaultdict
import pandas as pd
import streamlit as st
import http.client
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import HumanMessage, SystemMessage
from utils.constants import MODEL_NAME, CHUNK_SIZE, CHUNK_OVERLAP, \
    CHUNK_SYSTEM_MESSAGES, CHUNK_USER_PROMPTS, FINAL_SYSTEM_MESSAGES, FINAL_USER_PROMPTS, \
    ULTRA_CONCISE_SYSTEM_MESSAGES, ULTRA_CONCISE_USER_PROMPTS, SENTIMENT_SYSTEM_MESSAGE, SENTIMENT_USER_PROMPT



class CustomException(Exception):
    """
    Custom Exceptoin to handle the errors.
    """

class CommonFunctionClass:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CommonFunctionClass, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            load_dotenv()
            self.initialized = True

    def load_channel_ids_from_file(df):
        url_column = df.columns[0]
        channel_ids = df[url_column].dropna().tolist()
        return channel_ids
    
class StreamlitServiceClass:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(StreamlitServiceClass, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            load_dotenv()
            self.initialized = True

    def create_channel_details(self, all_videos_df, channel_stats, global_stats, is_metric=False):
        """Create detailed channel information with Streamlit"""

        if is_metric:
            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    label="🏢 Total Channels",
                    value=global_stats["total_channels"]
                )

            with col2:
                st.metric(
                    label="🎥 Total Videos",
                    value=global_stats["total_videos"]
                )
        # st.markdown("---")
        st.markdown("### 🏢 Channel Details")

        for channel, stats in channel_stats.items():
            with st.expander(f"📺 {channel} | {stats['total_videos']} videos"):
                st.markdown("**Recent Videos:**")

                channel_videos = all_videos_df[all_videos_df['channel'] == channel].sort_values('published_at', ascending=True)

                for _, video in channel_videos.iterrows():
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(f"""
                        **{video['title']}** \n
                        🕒 **Published at:** *{video['published_at'].strftime('%I:%M %p')}* 
                        """) #  - %Y-%m-%d

                        if 'four_line_summary' in video and pd.notna(video['four_line_summary']):
                            st.markdown(f"📝 **Summary:** {video['four_line_summary']}")

                    with col2:
                        st.markdown(f"[🔗 Watch]({video['video_url']})")

                    st.markdown("---")
    
class AgentServiceClass:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AgentServiceClass, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            load_dotenv()
            self.base_url = os.getenv("BASE_URL")
            self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
            self.youtube_base_video_url = os.getenv("YOUTUBE_VIDEO_BASE_URL")
            self.groq_api_key = os.getenv("GROQ_API_KEY")
            self.youtube_service = YouTubeServiceClass()
            self.llm = ChatGroq(
                groq_api_key=self.groq_api_key,
                model_name=MODEL_NAME
            )
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,  
                chunk_overlap=CHUNK_OVERLAP,  
            )
            self.initialized = True

    def run_summary_pipeline(self, video_id, value : int, recent_summary: str = None):
        """Process a single YouTube video and return summary or error message."""
        try:

            transcript = self.youtube_service.get_transcript_rapidapi(video_id)
            if not transcript:
                return f"Transcript not available for video id {video_id}"

            if value == 4:
                summary = self.summarize_transcript_four_lines(transcript)
                return summary
            
            elif value == 2:
                summary = self.summarize_two_line_summary(recent_summary)
                return summary
            
            elif value == 1:
                sentiment = self.analyze_the_sentiment(recent_summary)
                return sentiment
            
            
            return "Summary is Not Generated"
            
        except Exception as e:
            return f"Error occured while fetching the transcription"
        
    def analyze_the_sentiment(self, summary):
        final_messages = [
            SystemMessage(content=SENTIMENT_SYSTEM_MESSAGE.get('english')),
            HumanMessage(content=SENTIMENT_USER_PROMPT.get('english').format(summary=summary))
        ]

        response = self.llm.invoke(final_messages)
        final_summary = response.content.strip()

        return self.remove_think_tags(final_summary)
        
    def summarize_transcript_four_lines(self, transcript):
        """Generate summary using Groq's DeepSeek model with chunking for large transcripts."""
        chunks = self.text_splitter.split_text(transcript)

        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            # print(f"Processing chunk {i+1}/{len(chunks)}")
            
            chunk_messages = [
                SystemMessage(content=CHUNK_SYSTEM_MESSAGES.get('english')),
                HumanMessage(content=CHUNK_USER_PROMPTS.get('english').format(chunk=chunk))
            ]
            
            try:
                chunk_response = self.llm.invoke(chunk_messages)
                chunk_summary = chunk_response.content.strip()
                chunk_summaries.append(self.remove_think_tags(chunk_summary))
                # print(f"Chunk {i+1} summary: {chunk_summary}")
            except Exception as e:
                print(f"Error summarizing chunk {i+1}: {str(e)}")

        if chunk_summaries:
            combined_summaries = "\n\n".join([f"Segment {i+1}: {summary}" for i, summary in enumerate(chunk_summaries)])

            final_messages = [
                SystemMessage(content=FINAL_SYSTEM_MESSAGES.get('english')),
                HumanMessage(content=FINAL_USER_PROMPTS.get('english').format(combined_summaries=combined_summaries))
            ]

            response = self. llm.invoke(final_messages)
            final_summary = response.content.strip()
            return self.remove_think_tags(final_summary)
        
        return "Summary is Not Generated for this Video"
    
    def summarize_two_line_summary(self, summary):
        """Generate summary using Groq's DeepSeek model with chunking for large transcripts."""

        final_messages = [
            SystemMessage(content=ULTRA_CONCISE_SYSTEM_MESSAGES.get('english')),
            HumanMessage(content=ULTRA_CONCISE_USER_PROMPTS.get('english').format(summary=summary))
        ]

        response = self. llm.invoke(final_messages)
        final_summary = response.content.strip()

        return self.remove_think_tags(final_summary)
        

    def remove_think_tags(self, text):
        """Remove thinking tags from text."""
        pattern = r'<think>.*?</think>'
        cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
        return cleaned_text.strip()
        



    


class YouTubeServiceClass:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(YouTubeServiceClass, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            load_dotenv()
            self.base_url = os.getenv("BASE_URL")
            self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
            self.youtube_base_video_url = os.getenv("YOUTUBE_VIDEO_BASE_URL")
            self.rapidapi_key = os.getenv("RAPIDAPI_KEY")
            self.rapidapi_host = os.getenv("RAPIDAPI_HOST")
            self.rapidapi_base_url = os.getenv("RAPIDAPI_BASE_URL")
            self.initialized = True

    def get_recent_videos_and_stats_by_channels_v1(self, channel_ids: List[str], hours: int = 24):
        """
        Fetch videos uploaded in the last `hours` from multiple YouTube channels.

        Args:
            channel_ids (List[str]): List of YouTube channel IDs.
            hours (int): Number of past hours to search.

        Returns:
            List[dict]: List of video metadata dictionaries.
        """
        published_after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        all_videos = []
        channel_stats = defaultdict(lambda: {
            "total_channels": 0,
            "total_videos": 0,
        })

        for channel_id in channel_ids:
            params = {
                'part': 'snippet',
                'channelId': channel_id,
                'publishedAfter': published_after,
                'type': 'video',
                'order': 'date',
                'maxResults': 1,
                'key': self.youtube_api_key
            }

            try:
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

                for item in data.get('items', []):
                    video = {
                        'channel_id': channel_id,
                        'channel': item['snippet']['channelTitle'],
                        'video_id': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'published_at': pd.to_datetime(item['snippet']['publishedAt']),
                        'video_url': f"{self.youtube_base_video_url}{item['id']['videoId']}"
                    }

                    channel_stats[video["channel"]]["total_videos"] += 1
                    all_videos.append(video)

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] API Request failed for {channel_id}: {e}")
                st.write(str(e))
                continue
            except KeyError as e:
                print(f"[ERROR] Key error for {channel_id}: {e}")
                st.write(str(e))
                continue

        global_stats = {
            "total_channels": len(channel_stats),
            "total_videos": sum(c["total_videos"] for c in channel_stats.values())
        }

        return pd.DataFrame(all_videos), dict(channel_stats), global_stats
    

    def get_recent_videos_and_stats_by_channels(self, channel_ids: List[str], hours: int = 24):
        """
        Optimized YouTube API version to fetch recent videos using 1 + N quota units.

        Args:
            channel_ids (List[str]): List of YouTube channel IDs.
            hours (int): Number of past hours to search.

        Returns:
            Tuple[pd.DataFrame, dict, dict]: video dataframe, per-channel stats, global stats.
        """
        published_after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        all_videos = []
        channel_stats = defaultdict(lambda: {"total_videos": 0})

        # Step 1: Fetch all channels' upload playlist IDs in a single call (1 quota unit)
        try:
            channels_url = "https://www.googleapis.com/youtube/v3/channels"
            channel_id_str = ",".join(channel_ids)
            params = {
                "part": "contentDetails",
                "id": channel_id_str,
                "key": self.youtube_api_key
            }

            resp = requests.get(channels_url, params=params)
            resp.raise_for_status()
            channel_data = resp.json()
        except Exception as e:
            print(f"[ERROR] Failed to fetch channel details: {e}")
            return pd.DataFrame(), {}, {}

        uploads_map = {}  # channel_id -> uploads playlist id
        for item in channel_data.get("items", []):
            uploads_map[item["id"]] = item["contentDetails"]["relatedPlaylists"]["uploads"]

        # Step 2: Fetch latest video from each uploads playlist (1 quota unit per playlistItems.list call)
        for channel_id, uploads_playlist_id in uploads_map.items():
            try:
                playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
                params = {
                    "part": "snippet",
                    "playlistId": uploads_playlist_id,
                    "maxResults": 1,
                    "key": self.youtube_api_key
                }

                resp = requests.get(playlist_url, params=params)
                resp.raise_for_status()
                playlist_data = resp.json()

                for item in playlist_data.get("items", []):
                    published_at = pd.to_datetime(item["snippet"]["publishedAt"])
                    if published_at >= pd.to_datetime(published_after):
                        video = {
                            'channel_id': channel_id,
                            'channel': item["snippet"]["channelTitle"],
                            'video_id': item["snippet"]["resourceId"]["videoId"],
                            'title': item["snippet"]["title"],
                            'published_at': published_at,
                            'video_url': f"{self.youtube_base_video_url}{item['snippet']['resourceId']['videoId']}"
                        }

                        all_videos.append(video)
                        channel_stats[video["channel"]]["total_videos"] += 1
            except Exception as e:
                print(f"[ERROR] Failed to fetch playlist items for {channel_id}: {e}")
                continue

        global_stats = {
            "total_channels": len(channel_stats),
            "total_videos": sum(c["total_videos"] for c in channel_stats.values())
        }

        return pd.DataFrame(all_videos), dict(channel_stats), global_stats
    
    def get_transcript_rapidapi(self, video_id):
        
        try:
            conn = http.client.HTTPSConnection(self.rapidapi_host)

            headers = {
                'x-rapidapi-key': self.rapidapi_key,
                'x-rapidapi-host': self.rapidapi_host
            }

            conn.request("GET", f"{self.rapidapi_base_url}{video_id}", headers=headers)

            res = conn.getresponse()
            data = res.read()

            json_data = json.loads(data.decode("utf-8"))

            print("Json data :: ", json_data)
            transcript_items = json_data.get("transcript", [])
            full_transcript = " ".join(item.get("text", "") for item in transcript_items)

            print(f"Full Trainscript :: {full_transcript}")

            return full_transcript.strip() if full_transcript.strip() else None
        
        except Exception as e:
            print(f"An exception occurred in get_transcript_rapidapi : {str(e)}")
            st.write(str(e))
            return None