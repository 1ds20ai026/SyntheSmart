import streamlit as st
import validators
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain.chains.summarize import load_summarize_chain
from langchain_community.document_loaders import YoutubeLoader, UnstructuredURLLoader
from pytube import YouTube
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Must be the first Streamlit command
st.set_page_config(
    page_title="Content Summarizer",
    page_icon="📚",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        padding: 1rem;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .sub-header {
        font-size: 1.5rem;
        color: #424242;
        margin-bottom: 2rem;
        text-align: center;
    }
    .summary-container {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .point-header {
        color: #1E88E5;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #1E88E5;
        color: white;
        width: 100%;
        padding: 0.5rem;
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.markdown('<h1 class="main-header">📚 SyntheSmart</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI Powered Content Summarization</p>', unsafe_allow_html=True)

# Create two columns for the URL input
col1, col2 = st.columns([3, 1])
with col1:
    generic_url = st.text_input("Enter URL", placeholder="Paste your YouTube or website URL here...")
with col2:
    st.markdown("<br>", unsafe_allow_html=True)  # Add some spacing
    summarize_button = st.button("📝 Summarize", use_container_width=True)


# Rest of your imports and setup code...

# Initialize Groq LLM with API key from environment variable
def initialize_llm():
    return ChatGroq(
        model="gemma-7b-it",
        groq_api_key=os.getenv('GROQ_API_KEY'),  # Load API key from .env
        temperature=0.5
    )

map_prompt_template = """
Analyze the following text and identify the key points and main ideas:
"{text}"
SUMMARY:
"""
map_prompt = PromptTemplate(template=map_prompt_template, input_variables=["text"])

combine_prompt_template = """
Create a comprehensive point-wise summary of the text. Include:
1. Main topics and key ideas
2. Important details and examples
3. Any significant conclusions or findings

Format the summary as bullet points with clear headers for each section.
Text: "{text}"

POINT-WISE SUMMARY:
"""
combine_prompt = PromptTemplate(template=combine_prompt_template, input_variables=["text"])

# Content Loader Function
def load_content(url):
    try:
        if "youtube.com" in url or "youtu.be" in url:
            try:
                # First try using just YoutubeLoader
                loader = YoutubeLoader.from_youtube_url(
                    url,
                    add_video_info=True,
                    language=["en"]
                )
                docs = loader.load()
                
                try:
                    # Try to get video info for display, but don't fail if it doesn't work
                    video = YouTube(url)
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(video.thumbnail_url, width=200)
                    with col2:
                        st.markdown(f"**Title:** {video.title}")
                        st.markdown(f"**Channel:** {video.author}")
                        st.markdown(f"**Duration:** {video.length} seconds")
                except Exception as video_info_error:
                    st.warning("Could not load video details, but transcript is available.")
                
                return docs
                
            except Exception as yt_error:
                st.error(f"Error accessing YouTube video: {str(yt_error)}")
                st.info("Trying alternative method to access transcript...")
                
                # You might want to add alternative YouTube transcript methods here
                # For example, using youtube_transcript_api
                try:
                    from youtube_transcript_api import YouTubeTranscriptApi
                    
                    # Extract video ID from URL
                    video_id = url.split('v=')[1] if 'v=' in url else url.split('/')[-1]
                    if '&' in video_id:
                        video_id = video_id.split('&')[0]
                    
                    # Get transcript
                    transcript = YouTubeTranscriptApi.get_transcript(video_id)
                    
                    # Convert transcript to document format
                    text = ' '.join([entry['text'] for entry in transcript])
                    from langchain.schema import Document
                    return [Document(page_content=text)]
                    
                except Exception as alt_error:
                    st.error("Could not access video transcript through any available method.")
                    st.error(f"Error details: {str(alt_error)}")
                    return None
        else:
            loader = UnstructuredURLLoader(
                urls=[url],
                ssl_verify=False,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
                }
            )
            return loader.load()
            
    except Exception as e:
        st.error(f"Error loading content: {str(e)}")
        return None
# Main Summarization Logic
if summarize_button:
    if not generic_url.strip():
        st.error("⚠️ Please provide a URL to get started")
    elif not validators.url(generic_url):
        st.error("⚠️ Please enter a valid URL (YouTube video or website)")
    else:
        try:
            with st.spinner("🔍 Analyzing content..."):
                llm = initialize_llm()
                docs = load_content(generic_url)
                
                if docs:
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Update progress
                    status_text.text("Creating summary chain...")
                    progress_bar.progress(30)
                    
                    chain = load_summarize_chain(
                        llm,
                        chain_type="map_reduce",
                        map_prompt=map_prompt,
                        combine_prompt=combine_prompt,
                        verbose=True
                    )
                    
                    status_text.text("Generating summary...")
                    progress_bar.progress(60)
                    
                    output_summary = chain.run(docs)
                    
                    progress_bar.progress(100)
                    status_text.empty()
                    
                    # Display Result
                    st.markdown("### 📋 Summary")
                    st.markdown('<div class="summary-container">', unsafe_allow_html=True)
                    
                    # Convert the summary into HTML with styling
                    formatted_summary = output_summary.replace("•", "○")  # Replace bullets for consistency
                    st.markdown(formatted_summary)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Add download button for the summary
                    st.download_button(
                        label="📥 Download Summary",
                        data=output_summary,
                        file_name="content_summary.txt",
                        mime="text/plain"
                    )
                else:
                    st.error("Failed to load content from the URL")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Add footer
st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        Made with ❤️ using Streamlit and LangChain
    </div>
""", unsafe_allow_html=True)
