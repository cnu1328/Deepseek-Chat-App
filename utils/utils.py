import os
import re
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from .prompt import Chunk_Summary_Prompt, Final_Summary_Prompt


class CustomException(Exception):
    """
    Custom Exceptoin to handle the errors.
    """

class YouTubeSummaryService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(YouTubeSummaryService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            load_dotenv()
            self.initialized = True

    def get_video_id_from_url(self, url: str) -> str:
        """
        Extract video ID from URL.

        Args:
            url(str): Youtube video url
        
        Returns:
            Youtube video's video ID
        """
        
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        print(parsed_url, query_params)

        if "v" in query_params:
            return query_params["v"][0]

        return "no_video_id"

    def get_transcript_from_video(self, url: str) -> str:
        """
        Get transcript text from YouTube video.

        Args:
            url(str): youtube video url

        Returns:
            Youtube video's transcripted text
        
        """
        video_id = self.get_video_id_from_url(url)

        try:
            if video_id == "no_video_id":
                raise CustomException("Invalid URL. Please provide a valid YouTube video URL.")

            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages='te')
            transcript_text = " ".join([entry["text"] for entry in transcript])
            return transcript_text.replace("\n", " ").replace("'", "")
        except Exception as e:
            raise CustomException(f"An Exception occured Here: {str(e)}")

    def create_chunks(self, transcript_text: str) -> list:
        """
        Split transcript text into processable chunks.

        Args:
            transcript_text (str): Youtube video's transcripted text

        Returns:
            list of processable chunks
        
        """
        try:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500)
            return text_splitter.split_text(transcript_text)
        except Exception as e:
            raise CustomException(f"An Exception occured: {str(e)}")

    def remove_think_tags(self, text: str) -> str:
        """
        Remove <think> tags from text.
        """
        pattern = r'<think>.*?</think>'
        return re.sub(pattern, '', text, flags=re.DOTALL).strip()

    def get_final_summary_from_chunk_summaries(self, chunks: list, model_name: str) -> str:
        """
        Summarize text chunks and generate the final summary.
        
        Args:
            chunks (list): processable chunks of transcriptted text

        Returns:
            A final summary for youtube video
        """
        try:
            llm = ChatGroq(groq_api_key=os.getenv("GROQ_API_KEY"), model_name=model_name)
            chunk_qa_chain = create_stuff_documents_chain(llm, Chunk_Summary_Prompt)

            summaries = [chunk_qa_chain.invoke({"input": chunk, "context": ""}) for chunk in chunks]
            combined_summary = " ".join([self.remove_think_tags(summary) for summary in summaries])

            final_qa_chain = create_stuff_documents_chain(llm, Final_Summary_Prompt)
            final_summary = final_qa_chain.invoke({"input": combined_summary, "context": ""})
            return final_summary

        except Exception as e:
            raise CustomException(f"An Exception occured: {str(e)}")

    
    def get_summary_from_video_url(self, url: str, model_name: str) -> str:
        """
        Get summary of a YouTube video from URL.
        
        Args:
            url (str): youtube video url

        Returns:
            A complete summary of youtube video
        """

        try:
            transcript_text = self.get_transcript_from_video(url)
            chunks = self.create_chunks(transcript_text)
            final_summary = self.get_final_summary_from_chunk_summaries(chunks, model_name)

            return self.remove_think_tags(final_summary), transcript_text
        
        except Exception as e:
            raise CustomException(f"An Exception occured: {str(e)}")

    @staticmethod
    def is_valid_youtube_url(url: str) -> bool:
        """
        Check if the provided URL is a valid YouTube video URL.

        Args:
            url (str): The input URL.

        Returns:
            bool: True if the URL is a valid YouTube video link, otherwise False.
        """
        youtube_regex = (
            r"^(https?:\/\/)?(www\.)?"
            r"(youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)"
            r"([a-zA-Z0-9_-]{11})"
        )
        return re.match(youtube_regex, url) is not None
