import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
from openai import OpenAI
from database import Database
from functools import wraps
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize OpenAI client - FIXED: Uncommented
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize database
db = Database()

# Simple password protection
APP_PASSWORD = os.getenv('APP_PASSWORD', 'changeme')


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        logger.info(f"Auth attempt: {auth_header[:20] if auth_header else 'None'}...")
        if not auth_header or auth_header != f"Bearer {APP_PASSWORD}":
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


def extract_audio(youtube_url):
    """Extract audio from YouTube video using yt-dlp with enhanced error handling"""
    temp_dir = tempfile.gettempdir()
    output_template = os.path.join(temp_dir, '%(id)s.%(ext)s')
    
    # Enhanced yt-dlp options for better compatibility
    ydl_opts = {
        'format': 'bestaudio/best',  # FIXED: Uncommented to ensure best audio quality
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_template,
        'quiet': False,  # Changed to False for better debugging
        'no_warnings': False,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        # Enhanced options for better YouTube compatibility
        'extract_flat': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        # Cookie handling - optional, remove if causing issues
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        # Additional options for restricted content
        'age_limit': None,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Extracting info from: {youtube_url}")
            info = ydl.extract_info(youtube_url, download=True)
            
            if info is None:
                raise Exception("Failed to extract video information")
            
            video_id = info.get('id')
            video_title = info.get('title', 'Unknown Title')
            
            if not video_id:
                raise Exception("Could not extract video ID")
            
            audio_file = os.path.join(temp_dir, f"{video_id}.mp3")
            
            # Check if file exists
            if not os.path.exists(audio_file):
                raise Exception(f"Audio file not found after extraction: {audio_file}")
            
            logger.info(f"Successfully extracted: {video_title}")
            return audio_file, video_title
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Private video" in error_msg:
            raise Exception("This video is private and cannot be accessed")
        elif "Video unavailable" in error_msg:
            raise Exception("This video is unavailable or has been removed")
        elif "age" in error_msg.lower():
            raise Exception("Age-restricted video. Cannot download without authentication")
        elif "copyright" in error_msg.lower():
            raise Exception("This video is blocked due to copyright restrictions")
        else:
            raise Exception(f"YouTube download error: {error_msg}")
    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}")
        raise


def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI Whisper API"""
    try:
        logger.info(f"Transcribing audio file: {audio_file_path}")
        with open(audio_file_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        logger.info("Transcription completed")
        return transcript
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise Exception(f"Transcription failed: {str(e)}")


def clean_transcript(raw_transcript):
    """Use GPT-4 to clean and format the transcript"""
    system_prompt = """You are a transcript editor. Your job is to:
1. Add proper punctuation and capitalization
2. Split the text into well-structured paragraphs
3. Remove filler words (um, uh, like, you know, etc.)
4. Fix grammatical errors
5. Keep the original meaning and content intact

Return only the cleaned transcript without any additional comments."""
    
    try:
        logger.info("Cleaning transcript with GPT-4")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_transcript}
            ],
            temperature=0.3
        )
        logger.info("Transcript cleaning completed")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error cleaning transcript: {str(e)}")
        # Return raw transcript if cleaning fails
        logger.warning("Returning raw transcript due to cleaning error")
        return raw_transcript


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/transcribe', methods=['POST'])
@require_auth
def transcribe():
    """Main endpoint to transcribe a YouTube video"""
    data = request.get_json()
    youtube_url = data.get('youtube_url')
    
    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    # Validate YouTube URL format
    if 'youtube.com' not in youtube_url and 'youtu.be' not in youtube_url:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    audio_file = None
    try:
        logger.info(f"Starting transcription for: {youtube_url}")
        
        # Step 1: Extract audio
        logger.info("Step 1: Extracting audio...")
        audio_file, video_title = extract_audio(youtube_url)
        
        # Step 2: Transcribe with Whisper
        logger.info("Step 2: Transcribing audio...")
        raw_transcript = transcribe_audio(audio_file)
        
        # Step 3: Clean with GPT-4
        logger.info("Step 3: Cleaning transcript...")
        clean_text = clean_transcript(raw_transcript)
        
        # Step 4: Save to database
        logger.info("Step 4: Saving to database...")
        transcript_id = db.save_transcript(youtube_url, video_title, clean_text)
        
        logger.info(f"Transcription completed successfully. ID: {transcript_id}")
        
        return jsonify({
            'id': transcript_id,
            'title': video_title,
            'transcript': clean_text,
            'url': youtube_url
        }), 200
        
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        # Cleanup audio file
        if audio_file and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
                logger.info(f"Cleaned up audio file: {audio_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup audio file: {str(e)}")


@app.route('/history', methods=['GET'])
@require_auth
def get_history():
    """Get all transcript history"""
    try:
        history = db.get_all_transcripts()
        return jsonify({'history': history}), 200
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/transcript/<int:transcript_id>', methods=['GET'])
@require_auth
def get_transcript(transcript_id):
    """Get a specific transcript by ID"""
    try:
        transcript = db.get_transcript(transcript_id)
        if transcript:
            return jsonify(transcript), 200
        else:
            return jsonify({'error': 'Transcript not found'}), 404
    except Exception as e:
        logger.error(f"Error fetching transcript: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)