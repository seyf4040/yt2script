"""
Enhanced database module with multi-user support
"""

import sqlite3
from datetime import datetime
import os
import secrets
from models import User


class Database:
    def __init__(self, db_path='transcripts.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with all required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'pending',
                temp_password BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Account requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                processed_by INTEGER,
                rejection_reason TEXT,
                FOREIGN KEY (processed_by) REFERENCES users(id)
            )
        ''')
        
        # Original transcripts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                youtube_url TEXT NOT NULL,
                video_title TEXT,
                transcript TEXT NOT NULL,
                formatted_transcript TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add user_id column if it doesn't exist
        cursor.execute("PRAGMA table_info(transcripts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            cursor.execute('ALTER TABLE transcripts ADD COLUMN user_id INTEGER REFERENCES users(id)')
        
        if 'formatted_transcript' not in columns:
            cursor.execute('ALTER TABLE transcripts ADD COLUMN formatted_transcript TEXT')
        
        # Add is_duplicate column to track duplicated transcripts
        if 'is_duplicate' not in columns:
            cursor.execute('ALTER TABLE transcripts ADD COLUMN is_duplicate BOOLEAN DEFAULT 0')
        
        if 'original_transcript_id' not in columns:
            cursor.execute('ALTER TABLE transcripts ADD COLUMN original_transcript_id INTEGER REFERENCES transcripts(id)')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_youtube_url ON transcripts(youtube_url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_transcripts ON transcripts(user_id, created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email ON users(email)')
        
        conn.commit()
        conn.close()
    
    # ========== USER MANAGEMENT ==========
    
    def create_user(self, email, password_hash, role='user', status='active', temp_password=False):
        """Create a new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (email, password_hash, role, status, temp_password)
                VALUES (?, ?, ?, ?, ?)
            ''', (email.lower(), password_hash, role, status, temp_password))
            
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row['id'],
                email=row['email'],
                password_hash=row['password_hash'],
                role=row['role'],
                status=row['status'],
                temp_password=bool(row['temp_password']),
                created_at=row['created_at'],
                last_login=row['last_login']
            )
        return None
    
    def get_user_by_email(self, email):
        """Get user by email"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email.lower(),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row['id'],
                email=row['email'],
                password_hash=row['password_hash'],
                role=row['role'],
                status=row['status'],
                temp_password=bool(row['temp_password']),
                created_at=row['created_at'],
                last_login=row['last_login']
            )
        return None
    
    def update_user_password(self, user_id, new_password_hash, temp_password=False):
        """Update user password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET password_hash = ?, temp_password = ?
            WHERE id = ?
        ''', (new_password_hash, temp_password, user_id))
        
        conn.commit()
        conn.close()
    
    def update_last_login(self, user_id):
        """Update user's last login timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def get_all_users(self):
        """Get all users (admin only)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_user_status(self, user_id, status):
        """Update user status (active/disabled)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET status = ? WHERE id = ?', (status, user_id))
        conn.commit()
        conn.close()
    
    # ========== ACCOUNT REQUESTS ==========
    
    def create_account_request(self, email):
        """Create a new account request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if already requested
        cursor.execute('''
            SELECT id FROM account_requests 
            WHERE email = ? AND status = 'pending'
        ''', (email.lower(),))
        
        if cursor.fetchone():
            conn.close()
            return None  # Already has pending request
        
        cursor.execute('''
            INSERT INTO account_requests (email, status)
            VALUES (?, 'pending')
        ''', (email.lower(),))
        
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id
    
    def get_pending_requests(self):
        """Get all pending account requests"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM account_requests 
            WHERE status = 'pending'
            ORDER BY requested_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def approve_account_request(self, request_id, admin_id):
        """Approve an account request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE account_requests 
            SET status = 'approved', 
                processed_at = CURRENT_TIMESTAMP,
                processed_by = ?
            WHERE id = ?
        ''', (admin_id, request_id))
        
        conn.commit()
        conn.close()
    
    def reject_account_request(self, request_id, admin_id, reason=None):
        """Reject an account request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE account_requests 
            SET status = 'rejected',
                processed_at = CURRENT_TIMESTAMP,
                processed_by = ?,
                rejection_reason = ?
            WHERE id = ?
        ''', (admin_id, reason, request_id))
        
        conn.commit()
        conn.close()
    
    def get_request_by_id(self, request_id):
        """Get account request by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM account_requests WHERE id = ?', (request_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    # ========== TRANSCRIPTS WITH USER ISOLATION ==========
    
    def save_transcript(self, user_id, youtube_url, video_title, transcript, 
                       formatted_transcript=None, is_duplicate=False, original_id=None):
        """Save a new transcript for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transcripts 
            (user_id, youtube_url, video_title, transcript, formatted_transcript, 
             is_duplicate, original_transcript_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, youtube_url, video_title, transcript, formatted_transcript,
              is_duplicate, original_id))
        
        transcript_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return transcript_id
    
    def find_transcript_by_url(self, youtube_url):
        """Find existing transcript by URL (any user) for deduplication"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM transcripts 
            WHERE youtube_url = ? AND is_duplicate = 0
            ORDER BY created_at DESC
            LIMIT 1
        ''', (youtube_url,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def copy_transcript_for_user(self, original_id, user_id):
        """Copy an existing transcript for a new user (deduplication)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get original transcript
        cursor.execute('SELECT * FROM transcripts WHERE id = ?', (original_id,))
        original = cursor.fetchone()
        
        if not original:
            conn.close()
            return None
        
        # Create copy
        cursor.execute('''
            INSERT INTO transcripts 
            (user_id, youtube_url, video_title, transcript, formatted_transcript,
             is_duplicate, original_transcript_id)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        ''', (user_id, original['youtube_url'], original['video_title'],
              original['transcript'], original['formatted_transcript'], original_id))
        
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return new_id
    
    def get_transcript(self, transcript_id, user_id=None):
        """Get a specific transcript (with optional user ownership check)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT * FROM transcripts
                WHERE id = ? AND user_id = ?
            ''', (transcript_id, user_id))
        else:
            cursor.execute('SELECT * FROM transcripts WHERE id = ?', (transcript_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_user_transcripts(self, user_id):
        """Get all transcripts for a specific user"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, youtube_url, video_title, 
                   substr(transcript, 1, 200) as preview,
                   is_duplicate, original_transcript_id,
                   created_at
            FROM transcripts
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_all_transcripts(self):
        """Get all transcripts (admin only - for backward compatibility)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, youtube_url, video_title, 
                   substr(transcript, 1, 200) as preview,
                   user_id, is_duplicate,
                   created_at
            FROM transcripts
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_transcript(self, transcript_id, user_id=None):
        """Delete a transcript (with optional user ownership check)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                DELETE FROM transcripts 
                WHERE id = ? AND user_id = ?
            ''', (transcript_id, user_id))
        else:
            cursor.execute('DELETE FROM transcripts WHERE id = ?', (transcript_id,))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        return affected > 0
    
    # ========== ADMIN UTILITIES ==========
    
    def get_stats(self):
        """Get system statistics (admin)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        stats = {}
        
        # Total users
        cursor.execute('SELECT COUNT(*) as count FROM users')
        stats['total_users'] = cursor.fetchone()['count']
        
        # Active users
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE status = 'active'")
        stats['active_users'] = cursor.fetchone()['count']
        
        # Pending requests
        cursor.execute("SELECT COUNT(*) as count FROM account_requests WHERE status = 'pending'")
        stats['pending_requests'] = cursor.fetchone()['count']
        
        # Total transcripts
        cursor.execute('SELECT COUNT(*) as count FROM transcripts')
        stats['total_transcripts'] = cursor.fetchone()['count']
        
        # Original transcripts (not duplicates)
        cursor.execute('SELECT COUNT(*) as count FROM transcripts WHERE is_duplicate = 0')
        stats['original_transcripts'] = cursor.fetchone()['count']
        
        # Duplicate transcripts
        cursor.execute('SELECT COUNT(*) as count FROM transcripts WHERE is_duplicate = 1')
        stats['duplicate_transcripts'] = cursor.fetchone()['count']
        
        # API calls saved
        stats['api_calls_saved'] = stats['duplicate_transcripts']
        
        conn.close()
        return stats