import os
import tempfile
from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, current_user
import yt_dlp
from openai import OpenAI
from database import Database
from models import User, PasswordValidator, EmailValidator
from auth import (admin_required, login_required_api, generate_temp_password, 
                  get_admin_emails, check_login_rate_limit, check_request_rate_limit)
from email_service import email_service
from functools import wraps
from dotenv import load_dotenv
import logging
from pdf_generator import generate_transcript_pdf
from pydub import AudioSegment
from werkzeug.security import generate_password_hash

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Secret key for sessions
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 604800  # 7 days

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize database
db = Database()

# Cost optimization
CLEANING_MODEL = os.getenv('CLEANING_MODEL', 'gpt-4o-mini')
MAX_FILE_SIZE_MB = 24


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return db.get_user_by_id(int(user_id))


# ========== AUTHENTICATION ENDPOINTS ==========

@app.route('/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Check rate limit
    allowed, remaining = check_login_rate_limit(email)
    if not allowed:
        return jsonify({'error': 'Too many login attempts. Please try again later.'}), 429
    
    # Get user
    user = db.get_user_by_email(email)
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Check account status
    if user.status != 'active':
        return jsonify({'error': 'Account is not active'}), 403
    
    # Login user
    login_user(user, remember=True)
    db.update_last_login(user.id)
    
    logger.info(f"User logged in: {email}")
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'temp_password': user.temp_password
    }), 200


@app.route('/auth/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    logout_user()
    return jsonify({'success': True}), 200


@app.route('/auth/current-user', methods=['GET'])
def get_current_user():
    """Get current logged-in user"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        }), 200
    else:
        return jsonify({'authenticated': False}), 200


@app.route('/auth/request-account', methods=['POST'])
def request_account():
    """Request a new account"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Validate email
    valid, error = EmailValidator.validate(email)
    if not valid:
        return jsonify({'error': error}), 400
    
    # Check rate limit
    allowed, remaining = check_request_rate_limit(email)
    if not allowed:
        return jsonify({'error': 'Too many requests. Please try again tomorrow.'}), 429
    
    # Check if user already exists
    existing_user = db.get_user_by_email(email)
    if existing_user:
        return jsonify({'error': 'An account with this email already exists'}), 400
    
    # Create account request
    request_id = db.create_account_request(email)
    
    if not request_id:
        return jsonify({'error': 'You already have a pending account request'}), 400
    
    logger.info(f"New account request: {email}")
    
    # Send notification to admins
    admin_emails = get_admin_emails(db)
    for admin_email in admin_emails:
        try:
            email_service.send_account_request_notification(admin_email, email)
        except Exception as e:
            logger.error(f"Failed to send notification to admin {admin_email}: {str(e)}")
    
    return jsonify({
        'success': True,
        'message': 'Account request submitted. You will receive an email when your request is reviewed.'
    }), 200


@app.route('/auth/change-password', methods=['POST'])
@login_required_api
def change_password():
    """Change user password"""
    data = request.get_json()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password required'}), 400
    
    # Verify current password (unless temp password)
    if not current_user.temp_password:
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Validate new password
    valid, error = PasswordValidator.validate(new_password)
    if not valid:
        return jsonify({'error': error}), 400
    
    # Update password
    new_hash = generate_password_hash(new_password)
    db.update_user_password(current_user.id, new_hash, temp_password=False)
    
    logger.info(f"Password changed for user: {current_user.email}")
    
    # Send confirmation email
    try:
        email_service.send_password_changed_email(current_user.email)
    except Exception as e:
        logger.error(f"Failed to send password change email: {str(e)}")
    
    return jsonify({'success': True}), 200


# ========== ADMIN ENDPOINTS ==========

@app.route('/admin/pending-requests', methods=['GET'])
@admin_required
def get_pending_requests():
    """Get all pending account requests (admin only)"""
    requests = db.get_pending_requests()
    return jsonify({'requests': requests}), 200


@app.route('/admin/approve-request/<int:request_id>', methods=['POST'])
@admin_required
def approve_request(request_id):
    """Approve an account request (admin only)"""
    # Get request
    req = db.get_request_by_id(request_id)
    if not req or req['status'] != 'pending':
        return jsonify({'error': 'Request not found or already processed'}), 404
    
    email = req['email']
    
    # Check if user already exists
    existing_user = db.get_user_by_email(email)
    if existing_user:
        return jsonify({'error': 'User already exists'}), 400
    
    # Generate temporary password
    temp_password = generate_temp_password()
    password_hash = generate_password_hash(temp_password)
    
    # Create user
    user_id = db.create_user(
        email=email,
        password_hash=password_hash,
        role='user',
        status='active',
        temp_password=True
    )
    
    if not user_id:
        return jsonify({'error': 'Failed to create user'}), 500
    
    # Update request status
    db.approve_account_request(request_id, current_user.id)
    
    logger.info(f"Account approved by {current_user.email}: {email}")
    
    # Send approval email with temp password
    try:
        success, error = email_service.send_account_approved_email(email, temp_password)
        if not success:
            logger.error(f"Failed to send approval email: {error}")
            return jsonify({
                'success': True,
                'warning': 'Account created but failed to send email. Please provide password manually.',
                'temp_password': temp_password
            }), 200
    except Exception as e:
        logger.error(f"Email error: {str(e)}")
        return jsonify({
            'success': True,
            'warning': 'Account created but email failed.',
            'temp_password': temp_password
        }), 200
    
    return jsonify({
        'success': True,
        'message': 'Account approved and email sent'
    }), 200


@app.route('/admin/reject-request/<int:request_id>', methods=['POST'])
@admin_required
def reject_request(request_id):
    """Reject an account request (admin only)"""
    data = request.get_json()
    reason = data.get('reason', '')
    
    # Get request
    req = db.get_request_by_id(request_id)
    if not req or req['status'] != 'pending':
        return jsonify({'error': 'Request not found or already processed'}), 404
    
    email = req['email']
    
    # Update request status
    db.reject_account_request(request_id, current_user.id, reason)
    
    logger.info(f"Account rejected by {current_user.email}: {email}")
    
    # Send rejection email
    try:
        email_service.send_account_rejected_email(email, reason)
    except Exception as e:
        logger.error(f"Failed to send rejection email: {str(e)}")
    
    return jsonify({'success': True}), 200


@app.route('/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users (admin only)"""
    users = db.get_all_users()
    return jsonify({'users': users}), 200


@app.route('/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """Get system statistics (admin only)"""
    stats = db.get_stats()
    return jsonify(stats), 200


@app.route('/admin/user/<int:user_id>/disable', methods=['POST'])
@admin_required
def disable_user(user_id):
    """Disable a user account (admin only)"""
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot disable your own account'}), 400
    
    db.update_user_status(user_id, 'disabled')
    logger.info(f"User disabled by {current_user.email}: ID {user_id}")
    
    return jsonify({'success': True}), 200


@app.route('/admin/user/<int:user_id>/enable', methods=['POST'])
@admin_required
def enable_user(user_id):
    """Enable a user account (admin only)"""
    db.update_user_status(user_id, 'active')
    logger.info(f"User enabled by {current_user.email}: ID {user_id}")
    
    return jsonify({'success': True}), 200


# ========== TRANSCRIPTION ENDPOINTS (Updated with User Isolation) ==========

# [Keep all the existing transcription functions: extract_audio, split_audio, 
#  transcribe_audio, clean_transcript, format_transcript - unchanged]

@app.route('/transcribe', methods=['POST'])
@login_required_api
def transcribe():
    """Main endpoint to transcribe a YouTube video (with deduplication)"""
    data = request.get_json()
    youtube_url = data.get('youtube_url')
    
    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    if 'youtube.com' not in youtube_url and 'youtu.be' not in youtube_url:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    # Check for existing transcript (deduplication)
    existing = db.find_transcript_by_url(youtube_url)
    
    if existing:
        # Duplicate without API calls!
        logger.info(f"Found existing transcript for {youtube_url}, duplicating for user {current_user.id}")
        
        new_id = db.copy_transcript_for_user(existing['id'], current_user.id)
        
        return jsonify({
            'id': new_id,
            'title': existing['video_title'],
            'transcript': existing['transcript'],
            'formatted_transcript': existing['formatted_transcript'],
            'url': youtube_url,
            'duplicated': True,
            'message': 'Transcript already exists - copied instantly without API costs!',
            'disclaimer': 'AI-Generated Content: This transcript was created using AI.'
        }), 200
    
    # New transcription - existing logic
    audio_file = None
    try:
        logger.info(f"Starting NEW transcription for: {youtube_url} (User: {current_user.id})")
        
        # [All existing transcription logic here - extract_audio, transcribe_audio, etc.]
        # ... (keeping your existing code)
        
        # When saving to database:
        transcript_id = db.save_transcript(
            user_id=current_user.id,
            youtube_url=youtube_url,
            video_title=video_title,
            transcript=clean_text,
            formatted_transcript=formatted_text,
            is_duplicate=False
        )
        
        logger.info(f"Transcription completed. ID: {transcript_id}")
        
        return jsonify({
            'id': transcript_id,
            'title': video_title,
            'transcript': clean_text,
            'formatted_transcript': formatted_text,
            'url': youtube_url,
            'duplicated': False,
            'disclaimer': 'AI-Generated Content: This transcript was created using AI.'
        }), 200
        
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/history', methods=['GET'])
@login_required_api
def get_history():
    """Get transcript history for current user"""
    if current_user.is_admin():
        # Admins can see all transcripts
        history = db.get_all_transcripts()
    else:
        # Regular users see only their own
        history = db.get_user_transcripts(current_user.id)
    
    return jsonify({'history': history}), 200


@app.route('/transcript/<int:transcript_id>', methods=['GET'])
@login_required_api
def get_transcript(transcript_id):
    """Get a specific transcript (with ownership check)"""
    # Check ownership unless admin
    if current_user.is_admin():
        transcript = db.get_transcript(transcript_id)
    else:
        transcript = db.get_transcript(transcript_id, user_id=current_user.id)
    
    if transcript:
        return jsonify(transcript), 200
    else:
        return jsonify({'error': 'Transcript not found'}), 404


@app.route('/download-pdf/<int:transcript_id>/<version>', methods=['GET'])
@login_required_api
def download_pdf(transcript_id, version):
    """Generate and download PDF of transcript"""
    try:
        if version not in ['clean', 'formatted']:
            return jsonify({'error': 'Invalid version'}), 400
        
        # Check ownership unless admin
        if current_user.is_admin():
            transcript = db.get_transcript(transcript_id)
        else:
            transcript = db.get_transcript(transcript_id, user_id=current_user.id)
        
        if not transcript:
            return jsonify({'error': 'Transcript not found'}), 404
        
        pdf_buffer = generate_transcript_pdf(transcript, version=version)
        
        video_title = transcript.get('video_title', 'transcript')
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_title[:50]}_{version}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    email_status = "configured" if email_service.enabled else "not configured"
    
    return jsonify({
        'status': 'healthy',
        'model': CLEANING_MODEL,
        'email_service': email_status,
        'disclaimer': 'AI-powered service. Verify accuracy for critical applications.'
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"Starting Flask app on port {port}")
    logger.info(f"Multi-user mode enabled with Flask-Login")
    logger.info(f"Email service: {'Enabled' if email_service.enabled else 'Disabled'}")
    app.run(host='0.0.0.0', port=port, debug=False)