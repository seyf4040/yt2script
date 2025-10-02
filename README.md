# YouTube Transcription Tool

A complete web application that transcribes YouTube videos using OpenAI's Whisper API and cleans the transcripts with GPT-4.

## ⚠️ Important Disclaimers

### AI-Generated Content
**This application uses artificial intelligence (OpenAI Whisper and GPT models) to transcribe and format video content. Please be aware:**

- ✋ **AI systems can make mistakes** - Transcripts may contain errors, mishear words, or misinterpret context
- 📝 **Accuracy is not guaranteed** - Always verify important information against the original source
- 🔍 **Review critical content** - Do not rely solely on AI-generated transcripts for legal, medical, financial, or other critical applications
- 🎯 **Context matters** - AI may struggle with accents, technical terminology, proper nouns, or unclear audio
- 🔒 **Your responsibility** - Users are responsible for verifying the accuracy of transcripts for their specific use case

### Privacy & Content
- 🎥 **Not affiliated with YouTube or Google** - This is an independent third-party tool
- 📹 **Respect copyright** - Only transcribe videos you have permission to use
- 🔐 **Content privacy** - Transcripts are stored in your local database; keep your OpenAI API key secure

### Use At Your Own Risk
This software is provided "as is" without warranty of any kind. The developers are not liable for any damages or issues arising from the use of AI-generated transcripts.

---

## Features

- 🎥 Extract audio from any YouTube video
- 🎤 Transcribe audio using OpenAI Whisper API
- ✨ Clean and format transcripts with GPT-4
- 📄 Export as PDF, TXT, or Markdown
- 🌍 UTF-8 support (Turkish, Spanish, French, etc.)
- 💾 Store transcripts in SQLite database
- 📚 View history of all transcriptions
- 🔒 Simple password authentication

## Architecture

- **Backend**: Flask API for processing
- **Frontend**: Streamlit for UI
- **Database**: SQLite for storage
- **AI Models**: OpenAI Whisper (transcription) + GPT (formatting)
- **Deployment**: Docker container on Google Cloud Run

## Prerequisites

- Python 3.11+
- OpenAI API key
- Docker (for deployment)
- Google Cloud SDK (for Cloud Run deployment)
- FFmpeg (for audio processing)
- DejaVu fonts (for UTF-8/international character support)

## Local Development Setup

### 1. Clone and Install Dependencies

```bash
# Create project directory
mkdir youtube-transcription
cd youtube-transcription

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install fonts for UTF-8 support (Turkish, etc.)
sudo apt-get install fonts-dejavu-core fonts-dejavu-extra  # Linux
brew install --cask font-dejavu  # macOS
```

### 2. Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

### 3. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
OPENAI_API_KEY=sk-your-actual-api-key
APP_PASSWORD=your-secure-password
API_URL=http://localhost:8080
PORT=8080
```

### 4. Run Locally

**Terminal 1 - Start Flask API:**
```bash
source venv/bin/activate
python app.py
```

**Terminal 2 - Start Streamlit UI:**
```bash
source venv/bin/activate
streamlit run ui.py
```

Visit:
- **Streamlit UI**: http://localhost:8501
- **Flask API**: http://localhost:8080/health

## Docker Deployment

### Build Docker Image

```bash
docker build -t youtube-transcription .
```

### Run Docker Container Locally

```bash
docker run -p 8080:8080 -p 8501:8501 \
  -e OPENAI_API_KEY=your-key \
  -e APP_PASSWORD=your-password \
  youtube-transcription
```

## Google Cloud Run Deployment

### 1. Setup Google Cloud Project

```bash
# Install Google Cloud SDK if not already installed
# Visit: https://cloud.google.com/sdk/docs/install

# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Build and Push Image

```bash
# Configure Docker for GCP
gcloud auth configure-docker

# Build and tag image
docker build -t gcr.io/YOUR_PROJECT_ID/youtube-transcription .

# Push to Google Container Registry
docker push gcr.io/YOUR_PROJECT_ID/youtube-transcription
```

### 3. Deploy to Cloud Run

```bash
gcloud run deploy youtube-transcription \
  --image gcr.io/YOUR_PROJECT_ID/youtube-transcription \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8501 \
  --set-env-vars OPENAI_API_KEY=your-key,APP_PASSWORD=your-password,API_URL=http://localhost:8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900 \
  --max-instances 1 \
  --min-instances 0
```

**Cost Optimization Notes:**
- `--min-instances 0`: Scales to zero when not in use (no cost)
- `--max-instances 1`: Limits concurrent instances
- `--memory 2Gi --cpu 2`: Adequate for transcription tasks
- `--timeout 900`: 15 minutes for long videos

### 4. Access Your Application

After deployment, Cloud Run provides a URL:
```
https://youtube-transcription-xxxxx-uc.a.run.app
```

Visit this URL to access your Streamlit interface.

## Authentication

The app uses simple Bearer token authentication:
- Set `APP_PASSWORD` environment variable
- All API requests require `Authorization: Bearer <APP_PASSWORD>` header
- Streamlit UI automatically includes this header

For production, consider using:
- Google Cloud IAM authentication
- OAuth 2.0
- Firebase Authentication

## Project Structure

```
youtube-transcription/
├── app.py              # Flask backend API
├── ui.py               # Streamlit frontend
├── database.py         # SQLite database handler
├── pdf_generator.py    # PDF generation with UTF-8 support
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
├── start.sh            # Startup script
├── .env.example        # Environment variables template
├── README.md           # This file
└── transcripts.db      # SQLite database (created on first run)
```

## API Endpoints

### `POST /transcribe`
Transcribe a YouTube video.

**Request:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=..."
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Video Title",
  "transcript": "Clean transcript text...",
  "formatted_transcript": "# Formatted markdown...",
  "url": "https://www.youtube.com/watch?v=..."
}
```

### `GET /history`
Get all transcription history.

### `GET /transcript/<id>`
Get a specific transcript by ID.

### `GET /download-pdf/<id>/<version>`
Download transcript as PDF (`version`: 'clean' or 'formatted').

### `GET /health`
Health check endpoint.

## Database Schema

```sql
CREATE TABLE transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    youtube_url TEXT NOT NULL,
    video_title TEXT,
    transcript TEXT NOT NULL,
    formatted_transcript TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage

1. **New Transcription**:
   - Navigate to "New Transcription" page
   - Read the AI disclaimer
   - Paste a YouTube URL
   - Click "Transcribe Video"
   - Wait for processing (1-5 minutes depending on video length)

2. **View Result**:
   - Go to "Transcript Result" page
   - View both clean and formatted versions
   - Download as TXT, MD, or PDF

3. **Browse History**:
   - Go to "History" page
   - View all past transcriptions
   - Click "View Full" to load a previous transcript

## Cost Estimates (Google Cloud Run)

**Assumptions:**
- 10 transcriptions per month
- Average video: 10 minutes
- Processing time: 2-3 minutes per video

**Estimated Monthly Cost:**
- Cloud Run: $0-2 (with scale-to-zero)
- OpenAI Whisper API: ~$0.06 per 10-min video
- GPT-4o-mini API: ~$0.02 per transcript
- **Total: ~$1-2/month** for moderate usage

**Cost Optimization Tips:**
- Use `--min-instances 0` to scale to zero
- Set reasonable `--timeout` limits
- Monitor usage in Google Cloud Console
- Consider using GPT-3.5-turbo for even lower costs

## Accuracy & Quality

### What AI Does Well:
✅ Clear speech in quiet environments
✅ Standard accents and pronunciation
✅ Common vocabulary and phrases
✅ Well-structured content
✅ Good audio quality

### Where AI May Struggle:
⚠️ Heavy accents or dialects
⚠️ Technical jargon or specialized terminology
⚠️ Multiple speakers talking over each other
⚠️ Background noise or poor audio quality
⚠️ Proper nouns (names, places, brands)
⚠️ Numbers, dates, and specific data
⚠️ Sarcasm, idioms, or cultural references

### Improving Accuracy:
- Use videos with clear audio
- Avoid videos with heavy background noise
- Review and edit AI-generated transcripts
- Cross-reference critical information
- Consider manual verification for important content

## Troubleshooting

### FFmpeg Not Found
```bash
# Install FFmpeg
# macOS: brew install ffmpeg
# Ubuntu: apt-get install ffmpeg
```

### OpenAI API Errors
- Verify API key is correct
- Check API quota and billing
- Ensure key has Whisper API access

### Turkish/International Characters Not Showing
```bash
# Install DejaVu fonts
sudo apt-get install fonts-dejavu-core fonts-dejavu-extra  # Linux
brew install --cask font-dejavu  # macOS
```

### Database Locked
- Only one user at a time (SQLite limitation)
- For production with multiple users, migrate to PostgreSQL

### Cloud Run Timeout
- Increase `--timeout` for longer videos
- Default is 300 seconds (5 minutes)
- Maximum is 3600 seconds (60 minutes)

## Security Considerations

1. **API Key Management**: Use Google Secret Manager in production
2. **Authentication**: Current password auth is basic; upgrade to OAuth for production
3. **Rate Limiting**: Add rate limiting to prevent abuse
4. **Input Validation**: Validate YouTube URLs before processing
5. **HTTPS**: Cloud Run provides HTTPS by default
6. **AI Safety**: Be aware that AI may misinterpret content; verify critical information

## Limitations

- SQLite doesn't support concurrent writes (single user by design)
- Video length limited by Cloud Run timeout (max 60 minutes)
- No video quality selection (uses best audio)
- No support for playlists or batch processing
- **AI transcripts may contain errors** - always verify important content
- Language support depends on Whisper model capabilities
- Requires internet connection for API calls

## Responsible AI Use

### Best Practices:
✅ Always review AI-generated transcripts before sharing
✅ Verify accuracy for professional or academic use
✅ Cite the original video source, not just the transcript
✅ Be transparent that content is AI-generated
✅ Don't use for medical, legal, or financial advice without verification
✅ Respect copyright and fair use guidelines

### Ethical Considerations:
- Obtain permission for copyrighted content
- Be aware of AI biases and limitations
- Don't use transcripts to misrepresent content
- Respect speaker privacy and consent
- Follow OpenAI's usage policies

## Future Enhancements

- [ ] Support for multiple audio formats
- [ ] Batch processing of multiple videos
- [ ] Speaker diarization (identify different speakers)
- [ ] Translation support
- [ ] Better authentication (OAuth)
- [ ] PostgreSQL for multi-user support
- [ ] Webhook notifications
- [ ] Human-in-the-loop corrections
- [ ] Confidence scores for transcription accuracy
- [ ] Custom vocabulary support

## License

MIT License - feel free to use and modify for your needs.

## Support

For issues or questions:
1. Check troubleshooting section
2. Review Google Cloud Run logs: `gcloud run logs read`
3. Check OpenAI API status
4. Verify environment variables are set correctly

## Disclaimer (Legal)

THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

**AI Content:** Transcripts are generated using artificial intelligence and may contain errors. Users are solely responsible for verifying accuracy and appropriateness for their intended use.

## Contributing

Contributions welcome! This is an open-source project designed to help people access video content through transcription. Please be mindful of AI limitations and ethical considerations when contributing.

---

**Remember:** This tool uses AI to transcribe content. Always verify important information and use responsibly! 🤖✨