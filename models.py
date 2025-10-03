"""
User models and authentication for YouTube Transcription Tool
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re


class User(UserMixin):
    """User model for Flask-Login"""
    
    def __init__(self, id, email, password_hash, role='user', status='active', 
                 temp_password=False, created_at=None, last_login=None):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.role = role  # 'admin' or 'user'
        self.status = status  # 'pending', 'active', 'disabled'
        self.temp_password = temp_password
        self.created_at = created_at
        self.last_login = last_login
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_active(self):
        """Check if account is active (required by Flask-Login)"""
        return self.status == 'active'
    
    def get_id(self):
        """Return user id as string (required by Flask-Login)"""
        return str(self.id)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'status': self.status,
            'temp_password': self.temp_password,
            'created_at': self.created_at,
            'last_login': self.last_login
        }


class PasswordValidator:
    """Password strength validation"""
    
    MIN_LENGTH = 12
    
    @staticmethod
    def validate(password):
        """
        Validate password strength
        Returns: (is_valid, error_message)
        """
        if len(password) < PasswordValidator.MIN_LENGTH:
            return False, f"Password must be at least {PasswordValidator.MIN_LENGTH} characters"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, None


class EmailValidator:
    """Email validation"""
    
    # Basic email regex
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Common disposable email domains to block
    DISPOSABLE_DOMAINS = {
        'tempmail.com', 'throwaway.email', 'guerrillamail.com',
        '10minutemail.com', 'mailinator.com', 'trashmail.com'
    }
    
    @staticmethod
    def validate(email):
        """
        Validate email format and check for disposable domains
        Returns: (is_valid, error_message)
        """
        if not email or not isinstance(email, str):
            return False, "Email is required"
        
        email = email.lower().strip()
        
        if not EmailValidator.EMAIL_REGEX.match(email):
            return False, "Invalid email format"
        
        domain = email.split('@')[1]
        if domain in EmailValidator.DISPOSABLE_DOMAINS:
            return False, "Disposable email addresses are not allowed"
        
        return True, None