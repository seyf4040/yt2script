"""
Authentication utilities and decorators
"""

from functools import wraps
from flask import jsonify
from flask_login import current_user
import secrets
import string
import logging

logger = logging.getLogger(__name__)


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def login_required_api(f):
    """Decorator for API routes requiring authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if current_user.status != 'active':
            return jsonify({'error': 'Account is not active'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def generate_temp_password(length=16):
    """
    Generate a secure temporary password
    
    Returns: A random password with uppercase, lowercase, digits, and special chars
    """
    # Character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = '!@#$%^&*'
    
    # Ensure at least one of each type
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # Fill the rest
    all_chars = uppercase + lowercase + digits + special
    password.extend(secrets.choice(all_chars) for _ in range(length - 4))
    
    # Shuffle to randomize positions
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)


def get_admin_emails(db):
    """
    Get all admin email addresses for notifications
    
    Args:
        db: Database instance
    
    Returns:
        List of admin email addresses
    """
    all_users = db.get_all_users()
    admin_emails = [
        user['email'] for user in all_users 
        if user['role'] == 'admin' and user['status'] == 'active'
    ]
    
    return admin_emails


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.attempts = {}  # {key: [(timestamp, count), ...]}
    
    def check_rate_limit(self, key, max_attempts, window_seconds):
        """
        Check if rate limit is exceeded
        
        Args:
            key: Identifier (email, IP, etc.)
            max_attempts: Maximum attempts allowed
            window_seconds: Time window in seconds
        
        Returns:
            (allowed: bool, remaining: int)
        """
        import time
        
        now = time.time()
        
        # Clean old attempts
        if key in self.attempts:
            self.attempts[key] = [
                (ts, count) for ts, count in self.attempts[key]
                if now - ts < window_seconds
            ]
        else:
            self.attempts[key] = []
        
        # Count recent attempts
        total_attempts = sum(count for _, count in self.attempts[key])
        
        if total_attempts >= max_attempts:
            return False, 0
        
        # Record this attempt
        self.attempts[key].append((now, 1))
        
        remaining = max_attempts - total_attempts - 1
        return True, remaining


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_login_rate_limit(email):
    """Check login attempt rate limit"""
    # 5 attempts per 15 minutes
    allowed, remaining = rate_limiter.check_rate_limit(
        f"login:{email.lower()}", 
        max_attempts=5, 
        window_seconds=900
    )
    
    if not allowed:
        logger.warning(f"Rate limit exceeded for login: {email}")
    
    return allowed, remaining


def check_request_rate_limit(email):
    """Check account request rate limit"""
    # 3 attempts per day
    allowed, remaining = rate_limiter.check_rate_limit(
        f"request:{email.lower()}", 
        max_attempts=3, 
        window_seconds=86400
    )
    
    if not allowed:
        logger.warning(f"Rate limit exceeded for account request: {email}")
    
    return allowed, remaining