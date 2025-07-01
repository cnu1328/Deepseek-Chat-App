import asyncio
import aiohttp
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional, Callable
import time
import json
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

load_dotenv()

class YouTubeSearcher:
    """
    Asynchronous YouTube video searcher with API key rotation and quota optimization.
    """
    
    def __init__(self):
        """
        Initialize the YouTube searcher with API keys.
        
        Args:
            api_keys: List of YouTube Data API v3 keys for rotation
        """
        
        self.api_keys = self._load_env()
        self.current_key_index = 0
        self.base_url = "https://www.googleapis.com/youtube/v3/search"
        self.ist_timezone = pytz.timezone('Asia/Kolkata')
        
        # Quota management (100 units per search request)
        self.quota_used = 0
        self.requests_made = 0

    def _load_env(self):
        api_list_raw = os.getenv("YOUTUBE_API_KEY_LIST")

        if api_list_raw:
            api_list = [url.strip() for url in api_list_raw.split('#')]
        else:
            api_list = []

        return api_list

    
    def get_next_api_key(self) -> str:
        """Rotate to the next API key."""
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def get_time_filter(self, days: float) -> str:
        """
        Generate RFC 3339 timestamp for publishedAfter parameter.
        
        Args:
            days: Number of days to look back
            
        Returns:
            RFC 3339 formatted timestamp string
        """
        now = datetime.now(self.ist_timezone)
        time_delta = timedelta(days=days)
        published_after = now - time_delta
        return published_after.isoformat()
    
    async def search_videos_for_period(
        self, 
        session: aiohttp.ClientSession,
        query: str, 
        days: float
    ) -> List[Dict]:
        """
        Search videos for a specific time period.
        
        Args:
            session: aiohttp session for making requests
            query: Search query/hashtag
            days: Time period in days to search
            max_results: Maximum number of results to fetch
            
        Returns:
            List of video information dictionaries
        """
        videos = []
        page_token = None
        results_per_request = 50  # Maximum allowed by YouTube API
        
        published_after = self.get_time_filter(days)
        
        while len(videos) < 500:
            try:
                # Prepare request parameters
                params = {
                    'part': 'snippet',
                    'q': query,
                    'type': 'video',
                    'order': 'date',  # Order by upload date
                    'publishedAfter': published_after,
                    'maxResults': 50,
                    'key': self.get_next_api_key()
                }
                
                if page_token:
                    params['pageToken'] = page_token
                
                # Make API request
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Process video items
                        for item in data.get('items', []):
                            video_info = self.extract_video_info(item)
                            if video_info:
                                videos.append(video_info)
                        
                        # Update quota tracking
                        self.quota_used += 100
                        self.requests_made += 1
                        
                        # Check for next page
                        page_token = data.get('nextPageToken')
                        if not page_token:
                            break
                            
                    elif response.status == 403:
                        # Quota exceeded, try next API key
                        print(f"Quota exceeded for current API key. Switching to next key.")
                        if self.current_key_index == 0:  # Completed full rotation
                            print("All API keys exhausted. Stopping search.")
                            break
                        continue
                        
                    else:
                        print(f"API request failed with status {response.status}")
                        break
                        
            except Exception as e:
                print(f"Error in search request: {str(e)}")
                break
                
            # Small delay to be respectful to the API
            await asyncio.sleep(0.1)
        
        return videos
    
    def extract_video_info(self, item: Dict) -> Optional[Dict]:
        """
        Extract relevant video information from API response item.
        
        Args:
            item: YouTube API response item
            
        Returns:
            Dictionary with video information or None if invalid
        """
        try:
            snippet = item.get('snippet', {})
            video_id = item.get('id', {}).get('videoId')
            
            if not video_id:
                return None
            
            # Parse and convert publish date to IST
            published_at = snippet.get('publishedAt')
            if published_at:
                # Parse UTC datetime
                published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                # Convert to IST
                published_date = published_date.astimezone(self.ist_timezone)
            else:
                published_date = None
            
            return {
                'channel_name': snippet.get('channelTitle', 'Unknown Channel'),
                'video_title': snippet.get('title', 'No Title'),
                'video_link': f"https://www.youtube.com/watch?v={video_id}",
                'published_date': published_date,
                'description': snippet.get('description', ''),
                'channel_id': snippet.get('channelId', ''),
                'video_id': video_id
            }
            
        except Exception as e:
            print(f"Error extracting video info: {str(e)}")
            return None
    
    async def search_videos_async(
        self, 
        query: str, 
        time_periods_days: List[float],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        Asynchronously search for videos across multiple time periods.
        
        Args:
            query: Search query/hashtag
            time_periods_days: List of time periods in days to search
            max_results_per_period: Maximum results per time period
            progress_callback: Optional callback for progress updates
            
        Returns:
            Consolidated list of unique videos
        """
        all_videos = []
        total_periods = len(time_periods_days)
        
        # Create aiohttp session with optimized settings
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        
        async with aiohttp.ClientSession(
            timeout=timeout, 
            connector=connector
        ) as session:
            
            for i, days in enumerate(time_periods_days):
                if progress_callback:
                    progress = (i / total_periods)
                    period_name = self.get_period_name(days)
                    progress_callback(progress, f"Searching videos from {period_name}...")
                
                try:
                    period_videos = await self.search_videos_for_period(
                        session, query, days
                    )
                    all_videos.extend(period_videos)
                    
                    if progress_callback:
                        progress_callback(
                            (i + 1) / total_periods,
                            f"Found {len(period_videos)} videos from {period_name}"
                        )
                    
                except Exception as e:
                    print(f"Error searching for period {days} days: {str(e)}")
                    continue
        
        # Remove duplicates based on video_id
        unique_videos = {}
        for video in all_videos:
            video_id = video.get('video_id')
            if video_id and video_id not in unique_videos:
                unique_videos[video_id] = video
        
        final_videos = list(unique_videos.values())
        
        # Sort by published date (newest first)
        final_videos.sort(key=lambda x: x['published_date'] or datetime.min.replace(tzinfo=self.ist_timezone), reverse=True)
        
        if progress_callback:
            progress_callback(1.0, f"Completed! Found {len(final_videos)} unique videos. Used {self.quota_used} quota units.")
        
        print(f"Search completed:")
        print(f"- Total unique videos: {len(final_videos)}")
        print(f"- API requests made: {self.requests_made}")
        print(f"- Quota units used: {self.quota_used}")
        print(f"- API keys rotated: {len(self.api_keys)}")
        
        return final_videos
    
    def get_period_name(self, days: float) -> str:
        """Convert days to human-readable period name."""
        if days >= 30:
            months = int(days / 30)
            return f"last {months} month{'s' if months > 1 else ''}"
        elif days >= 1:
            return f"last {int(days)} day{'s' if days > 1 else ''}"
        else:
            hours = int(days * 24)
            return f"last {hours} hour{'s' if hours > 1 else ''}"
    
    def get_quota_info(self) -> Dict:
        """Get current quota usage information."""
        return {
            'quota_used': self.quota_used,
            'requests_made': self.requests_made,
            'api_keys_count': len(self.api_keys),
            'estimated_daily_quota_per_key': 10000,  # Default YouTube API quota
            'total_available_quota': len(self.api_keys) * 10000
        }