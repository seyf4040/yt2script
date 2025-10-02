# YouTube Transcription Tool

A complete web application that transcribes YouTube videos using OpenAI's Whisper API and cleans the transcripts with GPT-4.

## Features

- 🎥 Extract audio from any YouTube video
- 🎤 Transcribe audio using OpenAI Whisper API
- ✨ Clean and format transcripts with GPT-4
- 💾 Store transcripts in SQLite database
- 📚 View history of all transcriptions
- 🔒 Simple password authentication

## Architecture

- **Backend**: Flask API for processing
- **Frontend**: Streamlit for UI
- **Database**: SQLite for storage
- **Deployment**: Docker container on Google Cloud Run

## Prerequisites

- Python 3.11+
- OpenAI API key
- Docker (for deployment)
- Google Cloud SDK (for Cloud Run deployment)
- FFmpeg (for audio processing)

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

### 4. Set Environment Variables via Secret Manager (More Secure)

```bash
# Create secrets
echo -n "your-openai-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-password" | gcloud secrets create app-password --data-file=-

# Deploy with secrets
gcloud run deploy youtube-transcription \
  --image gcr.io/YOUR_PROJECT_ID/youtube-transcription \
  --platform managed \
  --region us-central1 \
  --update-secrets OPENAI_API_KEY=openai-api-key:latest,APP_PASSWORD=app-password:latest \
  --set-env-vars API_URL=http://localhost:8080
```

### 5. Access Your Application

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
  "url": "https://www.youtube.com/watch?v=..."
}
```

### `GET /history`
Get all transcription history.

### `GET /transcript/<id>`
Get a specific transcript by ID.

### `GET /health`
Health check endpoint.

## Database Schema

```sql
CREATE TABLE transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    youtube_url TEXT NOT NULL,
    video_title TEXT,
    transcript TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage

1. **New Transcription**:
   - Navigate to "New Transcription" page
   - Paste a YouTube URL
   - Click "Transcribe Video"
   - Wait for processing (1-5 minutes depending on video length)

2. **View Result**:
   - Go to "Transcript Result" page
   - View and download the clean transcript

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
- OpenAI Whisper API: ~$0.60 per hour of audio
- GPT-4 API: ~$0.03-0.06 per transcript
- **Total: $5-10/month** for moderate usage

**Cost Optimization Tips:**
- Use `--min-instances 0` to scale to zero
- Set reasonable `--timeout` limits
- Monitor usage in Google Cloud Console
- Consider using GPT-3.5-turbo instead of GPT-4 for cleaning

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

### Database Locked
- Only one user at a time (SQLite limitation)
- For production with multiple users, migrate to PostgreSQL

### Cloud Run Timeout
- Increase `--timeout` for longer videos
- Default is 300 seconds (5 minutes)
- Maximum is 3600 seconds (60 minutes)

### Memory Issues
- Increase `--memory` if processing large files
- Consider chunking very long videos

## Security Considerations

1. **API Key Management**: Use Google Secret Manager in production
2. **Authentication**: Current password auth is basic; upgrade to OAuth for production
3. **Rate Limiting**: Add rate limiting to prevent abuse
4. **Input Validation**: Validate YouTube URLs before processing
5. **HTTPS**: Cloud Run provides HTTPS by default

## Limitations

- SQLite doesn't support concurrent writes (single user by design)
- Video length limited by Cloud Run timeout (max 60 minutes)
- No video quality selection (uses best audio)
- No support for playlists or batch processing

## Future Enhancements

- [ ] Support for multiple audio formats
- [ ] Batch processing of multiple videos
- [ ] Export to multiple formats (PDF, DOCX)
- [ ] Speaker diarization
- [ ] Translation support
- [ ] Better authentication (OAuth)
- [ ] PostgreSQL for multi-user support
- [ ] Webhook notifications when transcription completes

## License

MIT License - feel free to use and modify for your needs.

## Support

For issues or questions:
1. Check troubleshooting section
2. Review Google Cloud Run logs: `gcloud run logs read`
3. Check OpenAI API status
4. Verify environment variables are set correctly

## Contributing

Contributions welcome! This is a personal project but feel free to fork and enhance.