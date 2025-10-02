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


def download_pdf(transcript_id, version):
    """Download PDF from API"""
    headers = {
        'Authorization': f'Bearer {APP_PASSWORD}'
    }
    
    url = f"{API_URL}/download-pdf/{transcript_id}/{version}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Failed to generate PDF: {response.json().get('error', 'Unknown error')}")
            return None
    except Exception as e:
        st.error(f"Error downloading PDF: {str(e)}")
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
    
    # AI Disclaimer
    st.info("⚠️ **AI-Powered Tool:** This application uses OpenAI's Whisper and GPT models to transcribe and format content. While we strive for accuracy, AI-generated transcripts may contain errors, omissions, or inaccuracies. Please review and verify important content.")
    
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
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**1. Audio Extraction**")
        st.write("Downloads audio from YouTube video")
    
    with col2:
        st.markdown("**2. Transcription**")
        st.write("Uses OpenAI Whisper API to convert speech to text")
    
    with col3:
        st.markdown("**3. Cleaning**")
        st.write("GPT cleans and formats the transcript")
    
    with col4:
        st.markdown("**4. Formatting**")
        st.write("Creates structured version with highlights")


# PAGE 2: Transcript Result
elif page == "Transcript Result":
    st.title("📝 Transcript Result")
    st.markdown("---")
    
    # AI Disclaimer
    st.warning("⚠️ **AI Disclaimer:** This transcript was generated using AI technology (OpenAI Whisper & GPT). AI systems can make mistakes, mishear words, or misinterpret context. Please verify accuracy for critical use cases.")
    
    if st.session_state.current_transcript:
        transcript = st.session_state.current_transcript
        
        # Display video info
        st.subheader(transcript.get('title', 'Untitled Video'))
        st.caption(f"Source: {transcript.get('url', 'N/A')}")
        st.markdown("---")
        
        # Create tabs for different versions
        tab1, tab2 = st.tabs(["📋 Clean Transcript", "✨ Formatted Version"])
        
        with tab1:
            st.markdown("### Clean Transcript")
            st.caption("Plain text version with proper punctuation and paragraphs")
            
            transcript_text = transcript.get('transcript', '')
            
            # Show in a nice text area
            st.text_area(
                "Transcript",
                value=transcript_text,
                height=500,
                label_visibility="collapsed"
            )
            
            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 Download as TXT",
                    data=transcript_text,
                    file_name=f"transcript_clean_{transcript.get('id', 'unknown')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col2:
                if st.button("📄 Download as PDF", key="clean_pdf", use_container_width=True):
                    with st.spinner("Generating PDF..."):
                        pdf_data = download_pdf(transcript.get('id'), 'clean')
                        if pdf_data:
                            st.download_button(
                                label="💾 Save PDF",
                                data=pdf_data,
                                file_name=f"transcript_clean_{transcript.get('id', 'unknown')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
        
        with tab2:
            st.markdown("### Formatted Version")
            st.caption("Structured version with titles, sections, highlights, and key takeaways")
            
            formatted_text = transcript.get('formatted_transcript', '')
            
            if formatted_text:
                # Display as markdown for better formatting
                st.markdown(formatted_text)
                
                st.markdown("---")
                
                # Download buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.download_button(
                        label="📥 Download as Markdown",
                        data=formatted_text,
                        file_name=f"transcript_formatted_{transcript.get('id', 'unknown')}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                with col2:
                    st.download_button(
                        label="📥 Download as Text",
                        data=formatted_text,
                        file_name=f"transcript_formatted_{transcript.get('id', 'unknown')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                with col3:
                    if st.button("📄 Download as PDF", key="formatted_pdf", use_container_width=True):
                        with st.spinner("Generating PDF..."):
                            pdf_data = download_pdf(transcript.get('id'), 'formatted')
                            if pdf_data:
                                st.download_button(
                                    label="💾 Save PDF",
                                    data=pdf_data,
                                    file_name=f"transcript_formatted_{transcript.get('id', 'unknown')}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
            else:
                st.info("Formatted version not available for this transcript.")
        
        # Clear button
        st.markdown("---")
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
st.sidebar.caption("YouTube Transcription Tool v2.0")
st.sidebar.caption("Now with formatted transcripts!")
st.sidebar.markdown("---")
st.sidebar.caption("⚠️ **Disclaimer:** This tool uses AI (OpenAI Whisper & GPT) for transcription and formatting. AI may produce errors or inaccuracies. Always verify important content.")
st.sidebar.caption("Not affiliated with YouTube or Google.")