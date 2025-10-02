import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
from openai import OpenAI
from database import Database
from functools import wraps
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize OpenAI client
# client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize database
db = Database()

# Simple password protection
APP_PASSWORD = os.getenv('APP_PASSWORD', 'changeme')


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        print("Auth Header:", auth_header)  # Debugging line to check auth header
        if not auth_header or auth_header != f"Bearer {APP_PASSWORD}":
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


def extract_audio(youtube_url):
    """Extract audio from YouTube video using yt-dlp"""
    temp_dir = tempfile.gettempdir()
    output_template = os.path.join(temp_dir, '%(id)s.%(ext)s')
    
    ydl_opts = {
        # 'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_template,
        'quiet': True,
        'cookiefile': 'cookies.txt',
        'nocheckcertificate': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        video_id = info['id']
        video_title = info['title']
        audio_file = os.path.join(temp_dir, f"{video_id}.mp3")
        
    return audio_file, video_title


def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI Whisper API"""
    with open(audio_file_path, 'rb') as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcript


def clean_transcript(raw_transcript):
    """Use GPT-4 to clean and format the transcript"""
    system_prompt = """You are a transcript editor. Your job is to:
1. Add proper punctuation and capitalization
2. Split the text into well-structured paragraphs
3. Remove filler words (um, uh, like, you know, etc.)
4. Fix grammatical errors
5. Keep the original meaning and content intact

Return only the cleaned transcript without any additional comments."""
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_transcript}
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content


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
    
    try:
        # Step 1: Extract audio
        audio_file, video_title = extract_audio(youtube_url)
        
        # Step 2: Transcribe with Whisper
        raw_transcript = transcribe_audio(audio_file)
        
        # Step 3: Clean with GPT-4
        clean_text = clean_transcript(raw_transcript)
        
        # Step 4: Save to database
        transcript_id = db.save_transcript(youtube_url, video_title, clean_text)
        
        # Cleanup
        if os.path.exists(audio_file):
            os.remove(audio_file)
        
        return jsonify({
            'id': transcript_id,
            'title': video_title,
            'transcript': clean_text,
            'url': youtube_url
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/history', methods=['GET'])
@require_auth
def get_history():
    """Get all transcript history"""
    try:
        history = db.get_all_transcripts()
        return jsonify({'history': history}), 200
    except Exception as e:
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
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)