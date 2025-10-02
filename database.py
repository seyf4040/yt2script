import sqlite3
from datetime import datetime
import os


class Database:
    def __init__(self, db_path='transcripts.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                youtube_url TEXT NOT NULL,
                video_title TEXT,
                transcript TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_transcript(self, youtube_url, video_title, transcript):
        """Save a new transcript to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transcripts (youtube_url, video_title, transcript)
            VALUES (?, ?, ?)
        ''', (youtube_url, video_title, transcript))
        
        transcript_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return transcript_id
    
    def get_transcript(self, transcript_id):
        """Get a specific transcript by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, youtube_url, video_title, transcript, created_at
            FROM transcripts
            WHERE id = ?
        ''', (transcript_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_transcripts(self):
        """Get all transcripts ordered by most recent first"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, youtube_url, video_title, 
                   substr(transcript, 1, 200) as preview,
                   created_at
            FROM transcripts
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_transcript(self, transcript_id):
        """Delete a transcript by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM transcripts WHERE id = ?', (transcript_id,))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        return affected > 0