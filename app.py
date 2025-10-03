import os
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
from openai import OpenAI
from database import Database
from functools import wraps
from dotenv import load_dotenv
import logging
from pdf_generator import generate_transcript_pdf
from pydub import AudioSegment

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize database
db = Database()

# Simple password protection
APP_PASSWORD = os.getenv('APP_PASSWORD', 'changeme')

# Cost optimization: Use cheaper model for cleaning
CLEANING_MODEL = os.getenv('CLEANING_MODEL', 'gpt-4o-mini')

# Whisper API limit is 25MB
MAX_FILE_SIZE_MB = 24  # Leave 1MB buffer


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
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '96',  # Further reduced for longer videos
        }],
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'extract_flat': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'age_limit': None,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
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


def split_audio(audio_file_path, chunk_length_ms=600000):
    """
    Split audio file into chunks of specified length (default 10 minutes)
    Returns list of chunk file paths
    """
    logger.info(f"Splitting audio file into chunks...")
    
    # Load audio file
    audio = AudioSegment.from_mp3(audio_file_path)
    
    # Calculate number of chunks
    total_length_ms = len(audio)
    num_chunks = (total_length_ms + chunk_length_ms - 1) // chunk_length_ms
    
    logger.info(f"Audio length: {total_length_ms/1000/60:.1f} minutes, splitting into {num_chunks} chunks")
    
    chunk_files = []
    temp_dir = tempfile.gettempdir()
    base_name = os.path.basename(audio_file_path).replace('.mp3', '')
    
    for i in range(num_chunks):
        start_ms = i * chunk_length_ms
        end_ms = min((i + 1) * chunk_length_ms, total_length_ms)
        
        chunk = audio[start_ms:end_ms]
        chunk_path = os.path.join(temp_dir, f"{base_name}_chunk_{i}.mp3")
        chunk.export(chunk_path, format="mp3", bitrate="96k")
        
        chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
        chunk_duration_min = ((end_ms - start_ms) / 1000) / 60
        logger.info(f"Chunk {i+1}/{num_chunks}: {chunk_size_mb:.1f}MB ({chunk_duration_min:.1f} minutes)")
        
        chunk_files.append(chunk_path)
    
    return chunk_files


def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI Whisper API with automatic chunking for large files"""
    try:
        # Check file size
        file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
        logger.info(f"Audio file size: {file_size_mb:.2f}MB")
        
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.info(f"File exceeds {MAX_FILE_SIZE_MB}MB limit, splitting into chunks...")
            
            # Split into chunks
            chunk_files = split_audio(audio_file_path, chunk_length_ms=600000)  # 10 min chunks
            
            # Transcribe each chunk
            transcripts = []
            for i, chunk_file in enumerate(chunk_files):
                logger.info(f"Transcribing chunk {i+1}/{len(chunk_files)}...")
                
                with open(chunk_file, 'rb') as audio_file:
                    chunk_transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                    transcripts.append(chunk_transcript)
                
                # Clean up chunk file
                try:
                    os.remove(chunk_file)
                except:
                    pass
            
            # Combine transcripts
            full_transcript = " ".join(transcripts)
            logger.info(f"Combined {len(chunk_files)} chunks into full transcript")
            return full_transcript
            
        else:
            # File is small enough, transcribe directly
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
    """Use GPT to clean and format the transcript"""
    system_prompt = """You are a transcript editor. Your job is to:
1. Add proper punctuation and capitalization
2. Split the text into well-structured paragraphs
3. Remove filler words (um, uh, like, you know, etc.)
4. Fix grammatical errors
5. Keep the original meaning and content intact

Return only the cleaned transcript without any additional comments."""
    
    try:
        logger.info(f"Cleaning transcript with {CLEANING_MODEL}")
        response = client.chat.completions.create(
            model=CLEANING_MODEL,
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
        logger.warning("Returning raw transcript due to cleaning error")
        return raw_transcript


def format_transcript(clean_transcript, video_title):
    """Create a formatted version with structure, highlights, and bullet points"""
    system_prompt = """You are a professional content formatter. Your task is to transform a transcript into a well-structured document while preserving the original content as much as possible.

Guidelines:
1. Create a clear title based on the main topic (if the provided title isn't descriptive enough)
2. Divide the content into logical sections with descriptive subtitles
3. Within each section, preserve the original text but organize it with:
   - Paragraph breaks for readability
   - Bullet points (•) for lists, steps, or key points when appropriate
   - **Bold text** to highlight the most important concepts, terms, or conclusions
4. Add a "Key Takeaways" section at the end with 3-5 bullet points of the most important insights
5. DO NOT add information that wasn't in the original transcript
6. DO NOT change the speaker's words or meaning - only reorganize and highlight
7. Keep the conversational tone when present

Format your response as markdown with the following structure:
# [Title]

## [Section 1 Name]
[Content with bold highlights and bullets where appropriate]

## [Section 2 Name]
[Content with bold highlights and bullets where appropriate]

...

## Key Takeaways
• [Main point 1]
• [Main point 2]
• [Main point 3]"""

    try:
        logger.info(f"Formatting transcript with {CLEANING_MODEL}")
        response = client.chat.completions.create(
            model=CLEANING_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Video Title: {video_title}\n\nTranscript:\n{clean_transcript}"}
            ],
            temperature=0.3
        )
        logger.info("Transcript formatting completed")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error formatting transcript: {str(e)}")
        logger.warning("Returning clean transcript due to formatting error")
        return clean_transcript


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model': CLEANING_MODEL,
        'disclaimer': 'This service uses AI (OpenAI Whisper & GPT). AI may produce errors or inaccuracies. Verify important content.'
    }), 200


@app.route('/transcribe', methods=['POST'])
@require_auth
def transcribe():
    """Main endpoint to transcribe a YouTube video"""
    data = request.get_json()
    youtube_url = data.get('youtube_url')
    
    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    if 'youtube.com' not in youtube_url and 'youtu.be' not in youtube_url:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    audio_file = None
    try:
        logger.info(f"Starting transcription for: {youtube_url}")
        
        # Step 1: Extract audio
        logger.info("Step 1: Extracting audio...")
        audio_file, video_title = extract_audio(youtube_url)
        
        # Step 2: Transcribe with Whisper (auto-chunks if needed)
        logger.info("Step 2: Transcribing audio...")
        raw_transcript = transcribe_audio(audio_file)
        
        # Step 3: Clean with GPT
        logger.info("Step 3: Cleaning transcript...")
        clean_text = clean_transcript(raw_transcript)
        
        # Step 4: Format with structure and highlights
        logger.info("Step 4: Creating formatted version...")
        formatted_text = format_transcript(clean_text, video_title)
        
        # Step 5: Save to database
        logger.info("Step 5: Saving to database...")
        transcript_id = db.save_transcript(youtube_url, video_title, clean_text, formatted_text)
        
        logger.info(f"Transcription completed successfully. ID: {transcript_id}")
        
        return jsonify({
            'id': transcript_id,
            'title': video_title,
            'transcript': clean_text,
            'formatted_transcript': formatted_text,
            'url': youtube_url,
            'disclaimer': 'AI-Generated Content: This transcript was created using AI (OpenAI Whisper & GPT). AI may produce errors, mishear words, or misinterpret context. Please verify accuracy for critical applications.'
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


@app.route('/download-pdf/<int:transcript_id>/<version>', methods=['GET'])
@require_auth
def download_pdf(transcript_id, version):
    """Generate and download PDF of transcript"""
    try:
        # Validate version
        if version not in ['clean', 'formatted']:
            return jsonify({'error': 'Invalid version. Use "clean" or "formatted"'}), 400
        
        # Get transcript from database
        transcript = db.get_transcript(transcript_id)
        
        if not transcript:
            return jsonify({'error': 'Transcript not found'}), 404
        
        logger.info(f"Generating {version} PDF for transcript {transcript_id}")
        
        # Generate PDF
        pdf_buffer = generate_transcript_pdf(transcript, version=version)
        
        # Create filename
        video_title = transcript.get('video_title', 'transcript')
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:50]
        filename = f"{safe_title}_{version}.pdf"
        
        logger.info(f"PDF generated successfully: {filename}")
        
        # Send file
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return jsonify({'error': f'Failed to generate PDF: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"Starting Flask app on port {port}")
    logger.info(f"Using {CLEANING_MODEL} for transcript cleaning")
    logger.info(f"Auto-chunking enabled for files > {MAX_FILE_SIZE_MB}MB")
    app.run(host='0.0.0.0', port=port, debug=False)