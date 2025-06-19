import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
import time
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from groq import Groq
import os
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import HumanMessage, SystemMessage
import tiktoken

load_dotenv()

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
    """Get transcript for a YouTube video with language priority: en -> te -> any available."""
    try:
        # Configure proxy
        proxy_config = WebshareProxyConfig(
            proxy_username="emppxwos",
            proxy_password="taeciknm5urr",
        )
        
        # Get available transcripts
        # transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript_list = YouTubeTranscriptApi(proxy_config=proxy_config).list_transcripts(video_id)
        print(f"Available transcripts for video {video_id}: {[t.language_code for t in transcript_list]}")
        
        transcript = None
        
        # Priority 1: Try English (en)
        try:
            transcript = transcript_list.find_transcript(['en'])
            print(f"Found English transcript for video {video_id}")
        except:
            print("No English transcript available")
            
            # Priority 2: Try Telugu (te)
            try:
                transcript = transcript_list.find_transcript(['te'])
                print(f"Found Telugu transcript for video {video_id}")
            except:
                print("No Telugu transcript available")
                
                # Priority 3: Try any available transcript
                try:
                    available_transcripts = list(transcript_list)
                    if available_transcripts:
                        transcript = available_transcripts[0]
                        print(f"Found transcript in {transcript.language_code} for video {video_id}")
                    else:
                        print(f"No transcripts available for video {video_id}")
                        return None
                except Exception as e:
                    print(f"Error accessing transcript list: {str(e)}")
                    return None
        
        # If we found a transcript, fetch the data
        if transcript:
            try:
                transcript_data = transcript.fetch()
                print(f"Successfully fetched transcript data for video {video_id}")
                
                # Extract text from transcript data
                print(f"Transcript data type: {type(transcript_data)}")
                if transcript_data:
                    print(f"First few items: {transcript_data[:2] if isinstance(transcript_data, list) else 'Not a list'}")
                
                full_transcript = ""
                
                if isinstance(transcript_data, list) and transcript_data:
                    # Handle list of dictionaries
                    for item in transcript_data:
                        if isinstance(item, dict):
                            # Try different possible keys for text content
                            text = item.get('text', '') or item.get('content', '') or item.get('transcript', '')
                            if text and text.strip():
                                full_transcript += text.strip() + " "
                        elif hasattr(item, 'text'):
                            # Handle objects with text attribute
                            if item.text and item.text.strip():
                                full_transcript += item.text.strip() + " "
                        elif isinstance(item, str):
                            # Handle direct string items
                            if item.strip():
                                full_transcript += item.strip() + " "
                
                elif isinstance(transcript_data, str):
                    # Handle direct string format
                    full_transcript = transcript_data.strip()
                
                elif hasattr(transcript_data, '__iter__'):
                    # Handle other iterable formats
                    try:
                        for item in transcript_data:
                            if isinstance(item, dict):
                                text = item.get('text', '') or item.get('content', '')
                                if text:
                                    full_transcript += text.strip() + " "
                            elif hasattr(item, 'text'):
                                if item.text:
                                    full_transcript += item.text.strip() + " "
                            elif isinstance(item, str):
                                full_transcript += item.strip() + " "
                    except Exception as iter_error:
                        print(f"Error iterating transcript data: {str(iter_error)}")
                        return None
                
                else:
                    print(f"Unexpected transcript data format for video {video_id}: {type(transcript_data)}")
                    # Try to convert to string as last resort
                    try:
                        full_transcript = str(transcript_data)
                    except:
                        return None
                
                # Clean up and return
                full_transcript = full_transcript.strip()
                if full_transcript:
                    print(f"Successfully extracted transcript with {len(full_transcript)} characters")
                    return full_transcript
                else:
                    print(f"No text content found in transcript data for video {video_id}")
                    return None
                    
            except Exception as e:
                print(f"Error fetching transcript data for video {video_id}: {str(e)}")
                return None
        else:
            print(f"No transcript found for video {video_id}")
            return None
            
    except Exception as e:
        print(f"Error getting transcript for video {video_id}: {str(e)}")
        # Check if it's a specific "no transcript" error
        if "No transcripts" in str(e) or "transcript" in str(e).lower():
            print(f"Video {video_id} has no available transcripts")
        return None

def count_tokens(text, model="gpt-3.5-turbo"):
    """Count tokens in text using tiktoken (approximate for DeepSeek)."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except:
        # Fallback: approximate 4 characters per token
        return len(text) // 4

def summarize_with_groq(transcript, groq_api_key):
    """Generate summary using Groq's DeepSeek model with chunking for large transcripts."""
    try:
        # Initialize LangChain Groq client
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="deepseek-r1-distill-llama-70b",
            temperature=0.3,
            max_tokens=2048
        )
        
        # DeepSeek R1 context limit is approximately 32k tokens
        # Use 80% of that for safety: 32k * 0.8 = ~25.6k tokens
        max_tokens_per_chunk = int(32000 * 0.8)
        
        # Count tokens in transcript
        total_tokens = count_tokens(transcript)
        print(f"Total transcript tokens: {total_tokens}")
        
        if total_tokens <= max_tokens_per_chunk:
            # Single chunk processing
            return generate_single_summary(llm, transcript)
        else:
            # Multi-chunk processing
            return generate_chunked_summary(llm, transcript, max_tokens_per_chunk)
            
    except Exception as e:
        print(f"Error in summarize_with_groq: {str(e)}")
        return "Summary generation failed"

def detect_transcript_language(transcript):
    """Detect the primary language of the transcript."""
    # Simple language detection based on common patterns
    sample = transcript[:500].lower()  # Use first 500 chars for detection
    
    # Telugu indicators
    telugu_chars = ['అ', 'ఆ', 'ఇ', 'ఈ', 'ఉ', 'ఊ', 'ఋ', 'ఎ', 'ఏ', 'ఐ', 'ఒ', 'ఓ', 'ఔ', 'క', 'గ', 'చ', 'జ', 'ట', 'డ', 'త', 'ద', 'న', 'ప', 'బ', 'మ', 'య', 'ర', 'ల', 'వ', 'శ', 'ష', 'స', 'హ']
    if any(char in transcript for char in telugu_chars):
        return 'telugu'
    
    # Hindi indicators  
    # hindi_chars = ['अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ए', 'ऐ', 'ओ', 'औ', 'क', 'ग', 'च', 'ज', 'ट', 'ड', 'त', 'द', 'न', 'प', 'ब', 'म', 'य', 'र', 'ल', 'व', 'श', 'ष', 'स', 'ह']
    # if any(char in transcript for char in hindi_chars):
    #     return 'hindi'
    
    # Add more language patterns as needed
    # Default to English if no specific patterns found
    return 'english'

def generate_single_summary(llm, transcript):
    """Generate summary for a single transcript that fits within token limits."""
    try:
        # Detect transcript language
        detected_language = detect_transcript_language(transcript)
        
        # Language-specific system messages
        language_instructions = {
            'telugu': """You are an expert YouTube video summarizer who specializes in Telugu content. Your task is to create concise, informative summaries in Telugu that capture the essence of video content.

            Guidelines:
            - తెలుగులో సంక్షిప్త మరియు సమాచారంతో కూడిన సారాంశం రాయండి
            - ముఖ్య అంశాలు, వాదనలు మరియు చర్య తీసుకోవాల్సిన సమాచారంపై దృష్టి పెట్టండి
            - అసలు టోన్ మరియు సందర్భాన్ని కొనసాగించండి
            - అనవసర మరియు నింపుట కంటెంట్‌ను నివారించండి
            - వీక్షకులకు అత్యంత విలువైన సమాచారానికి ప్రాధాన్యత ఇవ్వండి""",
            
            'hindi': """You are an expert YouTube video summarizer who specializes in Hindi content. Your task is to create concise, informative summaries in Hindi that capture the essence of video content.

            Guidelines:
            - हिंदी में संक्षिप्त और जानकारीपूर्ण सारांश लिखें
            - मुख्य अंतर्दृष्टि, मुख्य तर्कों और कार्यनीति की जानकारी पर ध्यान दें
            - मूल टोन और संदर्भ को बनाए रखें
            - अनावश्यक और भराव सामग्री से बचें
            - दर्शकों के लिए सबसे मूल्यवान जानकारी को प्राथमिकता दें""",
            
            'english': """You are an expert YouTube video summarizer. Your task is to create concise, informative summaries that capture the essence of video content.

            Guidelines:
            - Focus on key insights, main arguments, and actionable information
            - Maintain the original tone and context
            - Avoid redundancy and filler content
            - Prioritize the most valuable information for viewers"""
        }
        
        # Language-specific user prompts
        user_prompts = {
            'telugu': f"""ఈ YouTube వీడియో ట్రాన్స్‌క్రిప్ట్‌ను విశ్లేషించి, ఈ అంశాలను కలిగి ఉన్న సమగ్ర 4-5 వాక్య సారాంశం అందించండి:
            1. వీడియో యొక్క ముఖ్య అంశం/థీమ్
            2. ప్రధాన అంశాలు లేదా వాదనలు
            3. ముఖ్యమైన అంతర్దృష్టులు లేదా ముఖ్య విషయాలు
            4. ఏదైనా చర్య తీసుకోవాల్సిన సమాచారం లేదా తీర్మానాలు

            ట్రాన్స్‌క్రిప్ట్:
            {transcript}

            వీక్షకులు వీడియో యొక్క విలువను అర్థం చేసుకోవడంలో సహాయపడే స్పష్టమైన, ఆకర్షణీయమైన సారాంశం అందించండి:""",
            
            'hindi': f"""इस YouTube वीडियो ट्रांसक्रिप्ट का विश्लेषण करें और एक व्यापक 4-5 वाक्य सारांश प्रदान करें जो इन बातों को शामिल करे:
            1. वीडियो का मुख्य विषय/थीम
            2. प्रस्तुत मुख्य बिंदु या तर्क
            3. महत्वपूर्ण अंतर्दृष्टि या मुख्य बातें
            4. कोई भी कार्यनीति की जानकारी या निष्कर्ष

            ट्रांसक्रिप्ट:
            {transcript}

            एक स्पष्ट, आकर्षक सारांश प्रदान करें जो दर्शकों को वीडियो के मूल्य को समझने में मदद करे:""",
                        
                        'english': f"""Analyze this YouTube video transcript and provide a comprehensive 4-5 line summary that captures:
            1. The main topic/theme of the video
            2. Key points or arguments presented
            3. Important insights or takeaways
            4. Any actionable information or conclusions

            Transcript:
            {transcript}

            Provide a clear, engaging summary that would help viewers understand the video's value:"""
        }
        
        messages = [
            SystemMessage(content=language_instructions.get(detected_language, language_instructions['english'])),
            HumanMessage(content=user_prompts.get(detected_language, user_prompts['english']))
        ]
        
        response = llm.invoke(messages)
        summary = response.content.strip()
        print(f"Generated single summary: {summary}")
        return remove_think_tags(summary)
        
    except Exception as e:
        print(f"Error in generate_single_summary: {str(e)}")
        return "Single summary generation failed"

def generate_chunked_summary(llm, transcript, max_tokens_per_chunk):
    """Generate summary for large transcripts using chunking strategy."""
    try:
        # Detect transcript language
        detected_language = detect_transcript_language(transcript)
        
        # Split transcript into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens_per_chunk * 3,  # Approximate characters per chunk
            chunk_overlap=200,  # Small overlap to maintain context
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_text(transcript)
        print(f"Split transcript into {len(chunks)} chunks")
        
        # Language-specific chunk prompts
        chunk_system_messages = {
            'telugu': """మీరు వీడియో ట్రాన్స్‌క్రిప్ట్ భాగాల సంక్షిప్త సారాంశాలు రూపకల్పనలో నిపుణుడు. ప్రతి భాగం నుండి అత్యధిక ముఖ్యమైన సమాచారాన్ని వెలికితీయడంపై దృష్టి పెట్టండి.""",
            
            'hindi': """आप वीडियो ट्रांसक्रिप्ट खंडों के संक्षिप्त सारांश बनाने में विशेषज्ञ हैं। प्रत्येक खंड से सबसे महत्वपूर्ण जानकारी निकालने पर ध्यान दें।""",
            
            'english': """You are an expert at creating concise summaries of video transcript segments. Focus on extracting the most important information from each segment."""
        }
        
        chunk_user_prompts = {
            'telugu': """ఈ వీడియో ట్రాన్స్‌క్రిప్ట్ భాగాన్ని సరిగ్గా 2-3 స్పష్టమైన, సమాచారంతో కూడిన వాక్యాలలో సంక్షేపించండి. దృష్టి పెట్టవలసినవి:
            - ఈ భాగంలో చర్చించిన ముఖ్య అంశాలు
            - ప్రదర్శించిన ముఖ్య అంతర్దృష్టులు లేదా సమాచారం
            - వీక్షకులు తెలుసుకోవాల్సిన ముఖ్యమైన అంశాలు

            ట్రాన్స్‌క్రిప్ట్ భాగం:
            {chunk}

            సంక్షిప్త 2-3 వాక్య సారాంశం అందించండి:""",
                        
                        'hindi': """इस वीडियो ट्रांसक्रिप्ट खंड को बिल्कुल 2-3 स्पष्ट, जानकारीपूर्ण वाक्यों में सारांशित करें। इन पर ध्यान दें:
            - इस खंड में चर्चा किए गए मुख्य विषय
            - प्रस्तुत मुख्य अंतर्दृष्टि या जानकारी
            - महत्वपूर्ण बिंदु जो दर्शकों को जानने चाहिए

            ट्रांसक्रिप्ट खंड:
            {chunk}

            संक्षिप्त 2-3 वाक्य सारांश प्रदान करें:""",
                        
                        'english': """Summarize this video transcript segment in exactly 2-3 clear, informative lines. Focus on:
            - Main topics discussed in this segment
            - Key insights or information presented
            - Important points that viewers should know

            Transcript segment:
            {chunk}

            Provide a concise 2-3 line summary:"""
        }
        
        # Generate summary for each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}")
            
            chunk_messages = [
                SystemMessage(content=chunk_system_messages.get(detected_language, chunk_system_messages['english'])),
                HumanMessage(content=chunk_user_prompts.get(detected_language, chunk_user_prompts['english']).format(chunk=chunk))
            ]
            
            try:
                chunk_response = llm.invoke(chunk_messages)
                chunk_summary = chunk_response.content.strip()
                chunk_summaries.append(remove_think_tags(chunk_summary))
                print(f"Chunk {i+1} summary: {chunk_summary}")
            except Exception as e:
                print(f"Error summarizing chunk {i+1}: {str(e)}")
                chunk_summaries.append(f"Chunk {i+1}: Summary generation failed")
        
        # Generate final comprehensive summary
        if chunk_summaries:
            return generate_final_summary(llm, chunk_summaries, detected_language)
        else:
            return "Failed to generate chunk summaries"
            
    except Exception as e:
        print(f"Error in generate_chunked_summary: {str(e)}")
        return "Chunked summary generation failed"

def generate_final_summary(llm, chunk_summaries, detected_language='english'):
    """Generate final summary from chunk summaries."""
    try:
        combined_summaries = "\n\n".join([f"Segment {i+1}: {summary}" for i, summary in enumerate(chunk_summaries)])
        
        # Language-specific final summary prompts
        final_system_messages = {
            'telugu': """మీరు అనేక వీడియో భాగాల నుండి వచ్చిన సమాచారాన్ని ఒక సమన్వయమైన, సమగ్రమైన సారాంశంలో సంయోజనలో నిపుణుడు. సహజంగా ప్రవహించే మరియు పూర్తి వీడియో కథనాన్ని తెలియజేసే ఏకీకృత సారాంశం రూపొందించండి.""",
            
            'hindi': """आप कई वीडियो खंडों की जानकारी को एक सुसंगत, व्यापक सारांश में संयोजित करने में विशेषज्ञ हैं। एक एकीकृत सारांश बनाएं जो प्राकृतिक रूप से प्रवाहित हो और पूर्ण वीडियो कथा को कैप्चर करे।""",
            
            'english': """You are an expert at synthesizing information from multiple video segments into a cohesive, comprehensive summary. Create a unified summary that flows naturally and captures the complete video narrative."""
        }
        
        final_user_prompts = {
            'telugu': f"""YouTube वीडियो నుండి వచ్చిన ఈ భాగ సారాంశాల ఆధారంగా, ఈ అంశాలను కలిగి ఉన్న పూర్తి 4-5 వాక్య చివరి సారాంశం రూపొందించండి:

            1. మొత్తం వీడియో యొక్క సమగ్ర థీమ్ మరియు ముఖ్య సందేశాన్ని కలిగి ఉండాలి
            2. అన్ని భాగాలలో అత్యధిక ముఖ్యమైన అంతర్దృష్టులను హైలైట్ చేయాలి
            3. తార్కిక, ప్రవహించే కథనంలో సమాచారాన్ని ప్రదర్శించాలి
            4. సంభావ్య వీక్షకులకు స్పష్టమైన విలువను అందించాలి
            5. సమన్వయం మరియు పునరావృతం నివారించాలి

            భాగ సారాంశాలు:
            {combined_summaries}

            పూర్తి వీడియో యొక్క శుద్ధమైన, ఆకర్షణీయమైన 4-5 వాక్య సారాంశం రూపొందించండి:""",
                        
                        'hindi': f"""इस YouTube वीडियो के खंड सारांशों के आधार पर, एक व्यापक 4-5 वाक्य अंतिम सारांश बनाएं जो:

            1. पूरे वीडियो की समग्र थीम और मुख्य संदेश को कैप्चर करे
            2. सभी खंडों में सबसे महत्वपूर्ण अंतर्दृष्टि को हाइलाइट करे
            3. तार्किक, प्रवाहित कथा में जानकारी प्रस्तुत करे
            4. संभावित दर्शकों को स्पष्ट मूल्य प्रदान करे
            5. सुसंगति बनाए रखे और दोहराव से बचे

            खंड सारांश:
            {combined_summaries}

            पूर्ण वीडियो का एक परिष्कृत, आकर्षक 4-5 वाक्य सारांश बनाएं:""",
                        
                        'english': f"""Based on these segment summaries from a YouTube video, create a comprehensive 4-5 line final summary that:

            1. Captures the overall theme and main message of the entire video
            2. Highlights the most important insights across all segments  
            3. Presents information in a logical, flowing narrative
            4. Provides clear value to potential viewers
            5. Maintains coherence and avoids repetition

            Segment summaries:
            {combined_summaries}

            Create a polished, engaging 4-5 line summary of the complete video:"""
        }
        
        final_messages = [
            SystemMessage(content=final_system_messages.get(detected_language, final_system_messages['english'])),
            HumanMessage(content=final_user_prompts.get(detected_language, final_user_prompts['english']))
        ]
        
        response = llm.invoke(final_messages)
        final_summary = response.content.strip()
        print(f"Generated final summary: {final_summary}")
        return remove_think_tags(final_summary)
        
    except Exception as e:
        print(f"Error in generate_final_summary: {str(e)}")
        return "Final summary generation failed"

def remove_think_tags(text):
        pattern = r'<think>.*?</think>'
        cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
        return cleaned_text.strip()

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
            print(f"Extracted Video ID: {video_id} from URL: {url}")
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
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not groq_api_key:
            st.markdown('<div class="info-box">Please enter your Groq API key to proceed.</div>', unsafe_allow_html=True)
        
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
        1. Upload an Excel/CSV file with YouTube links
        2. Click 'Process Videos' to start
        3. Download the results when complete
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
                    st.session_state['results_df'] = results_df
                
            if 'results_df' in st.session_state:   
                results_df = st.session_state['results_df']

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
    
if __name__ == "__main__":
    main()