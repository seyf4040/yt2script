import streamlit as st
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
API_URL = os.getenv('API_URL', 'http://localhost:8080')
APP_PASSWORD = os.getenv('APP_PASSWORD', 'changeme')

# Page config
st.set_page_config(
    page_title="YouTube Transcription Tool",
    page_icon="🎥",
    layout="wide"
)


def make_api_request(endpoint, method='GET', data=None):
    """Helper function to make authenticated API requests"""
    # print("Password:", APP_PASSWORD)  # Debugging line to check password
    headers = {
        'Authorization': f'Bearer {APP_PASSWORD}',
        'Content-Type': 'application/json'
    }
    
    url = f"{API_URL}{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers)
        
        return response
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None


def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp_str


# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["New Transcription", "Transcript Result", "History"])

# Initialize session state
if 'current_transcript' not in st.session_state:
    st.session_state.current_transcript = None
if 'selected_history_id' not in st.session_state:
    st.session_state.selected_history_id = None


# PAGE 1: New Transcription
if page == "New Transcription":
    st.title("🎥 YouTube Video Transcription")
    st.markdown("---")
    
    st.write("Enter a YouTube URL to transcribe the video and get a clean, formatted transcript.")
    
    with st.form("transcription_form"):
        youtube_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste the full YouTube video URL"
        )
        
        submitted = st.form_submit_button("Transcribe Video", type="primary")
        
        if submitted:
            if not youtube_url:
                st.error("Please enter a YouTube URL")
            else:
                with st.spinner("Processing... This may take a few minutes."):
                    st.info("📥 Extracting audio from YouTube...")
                    
                    response = make_api_request(
                        '/transcribe',
                        method='POST',
                        data={'youtube_url': youtube_url}
                    )
                    
                    if response and response.status_code == 200:
                        result = response.json()
                        st.session_state.current_transcript = result
                        st.success("✅ Transcription completed successfully!")
                        st.info("Go to 'Transcript Result' to view the transcript.")
                    elif response:
                        st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                    else:
                        st.error("Failed to connect to the API")
    
    # Display some info
    st.markdown("---")
    st.subheader("How it works")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**1. Audio Extraction**")
        st.write("Downloads audio from YouTube video")
    
    with col2:
        st.markdown("**2. Transcription**")
        st.write("Uses OpenAI Whisper API to convert speech to text")
    
    with col3:
        st.markdown("**3. Enhancement**")
        st.write("GPT-4 cleans and formats the transcript")


# PAGE 2: Transcript Result
elif page == "Transcript Result":
    st.title("📝 Transcript Result")
    st.markdown("---")
    
    if st.session_state.current_transcript:
        transcript = st.session_state.current_transcript
        
        # Display video info
        st.subheader(transcript.get('title', 'Untitled Video'))
        st.caption(f"Source: {transcript.get('url', 'N/A')}")
        st.markdown("---")
        
        # Display transcript
        st.markdown("### Clean Transcript")
        transcript_text = transcript.get('transcript', '')
        
        # Show in a nice text area
        st.text_area(
            "Transcript",
            value=transcript_text,
            height=400,
            label_visibility="collapsed"
        )
        
        # Download button
        st.download_button(
            label="📥 Download Transcript",
            data=transcript_text,
            file_name=f"transcript_{transcript.get('id', 'unknown')}.txt",
            mime="text/plain"
        )
        
        # Clear button
        if st.button("Clear Result"):
            st.session_state.current_transcript = None
            st.rerun()
    
    else:
        st.info("No transcript to display. Go to 'New Transcription' to create one.")


# PAGE 3: History
elif page == "History":
    st.title("📚 Transcription History")
    st.markdown("---")
    
    if st.button("🔄 Refresh History"):
        st.rerun()
    
    response = make_api_request('/history')
    
    if response and response.status_code == 200:
        history = response.json().get('history', [])
        
        if history:
            st.write(f"Total transcripts: {len(history)}")
            st.markdown("---")
            
            for item in history:
                with st.expander(
                    f"🎥 {item['video_title']} - {format_timestamp(item['created_at'])}"
                ):
                    st.write(f"**ID:** {item['id']}")
                    st.write(f"**URL:** [{item['youtube_url']}]({item['youtube_url']})")
                    st.write(f"**Created:** {format_timestamp(item['created_at'])}")
                    
                    if item.get('preview'):
                        st.text(item['preview'] + "...")
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.button("View Full", key=f"view_{item['id']}"):
                            # Load full transcript
                            full_response = make_api_request(f"/transcript/{item['id']}")
                            if full_response and full_response.status_code == 200:
                                st.session_state.current_transcript = full_response.json()
                                st.info("Go to 'Transcript Result' to view")
        else:
            st.info("No transcripts found. Create your first transcription!")
    
    else:
        st.error("Failed to load history")


# Footer
st.sidebar.markdown("---")
st.sidebar.caption("YouTube Transcription Tool v1.0")