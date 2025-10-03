#!/usr/bin/env python3
"""
Migration script to upgrade from single-user to multi-user system (FIXED)
Run this ONCE before deploying the new version
"""

import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash
from datetime import datetime
import shutil


def backup_database(db_path):
    """Create a backup of the database"""
    if not os.path.exists(db_path):
        print(f"✓ No existing database found at {db_path}")
        return None
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path


def init_database_schema(db_path):
    """Initialize complete database schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n--- Creating tables ---")
        
        # 1. Users table
        print("Creating users table...")
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
        print("✓ Users table created")
        
        # 2. Account requests table
        print("Creating account_requests table...")
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
        print("✓ Account_requests table created")
        
        # 3. Check if transcripts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcripts'")
        transcripts_exists = cursor.fetchone() is not None
        
        if transcripts_exists:
            print("Transcripts table exists, adding new columns...")
            
            # Get existing columns
            cursor.execute("PRAGMA table_info(transcripts)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            # Add user_id if not exists
            if 'user_id' not in existing_columns:
                print("  Adding user_id column...")
                cursor.execute('ALTER TABLE transcripts ADD COLUMN user_id INTEGER REFERENCES users(id)')
            
            # Add is_duplicate if not exists
            if 'is_duplicate' not in existing_columns:
                print("  Adding is_duplicate column...")
                cursor.execute('ALTER TABLE transcripts ADD COLUMN is_duplicate BOOLEAN DEFAULT 0')
            
            # Add original_transcript_id if not exists
            if 'original_transcript_id' not in existing_columns:
                print("  Adding original_transcript_id column...")
                cursor.execute('ALTER TABLE transcripts ADD COLUMN original_transcript_id INTEGER REFERENCES transcripts(id)')
            
            # Add formatted_transcript if not exists
            if 'formatted_transcript' not in existing_columns:
                print("  Adding formatted_transcript column...")
                cursor.execute('ALTER TABLE transcripts ADD COLUMN formatted_transcript TEXT')
            
            print("✓ Transcripts table updated")
        else:
            print("Creating transcripts table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    youtube_url TEXT NOT NULL,
                    video_title TEXT,
                    transcript TEXT NOT NULL,
                    formatted_transcript TEXT,
                    user_id INTEGER REFERENCES users(id),
                    is_duplicate BOOLEAN DEFAULT 0,
                    original_transcript_id INTEGER REFERENCES transcripts(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✓ Transcripts table created")
        
        # 4. Create indexes
        print("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_youtube_url ON transcripts(youtube_url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_transcripts ON transcripts(user_id, created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email ON users(email)')
        print("✓ Indexes created")
        
        conn.commit()
        print("\n✓ Database schema initialization complete")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error initializing schema: {str(e)}")
        return False
    finally:
        conn.close()


def create_admin_account(db_path, email, password):
    """Create the initial admin account"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if admin already exists
        cursor.execute("SELECT id FROM users WHERE role = 'admin'")
        if cursor.fetchone():
            print("✓ Admin account already exists")
            admin_id = cursor.execute("SELECT id FROM users WHERE role = 'admin'").fetchone()[0]
            conn.close()
            return admin_id
        
        # Create admin
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (email, password_hash, role, status, temp_password)
            VALUES (?, ?, 'admin', 'active', 0)
        ''', (email.lower(), password_hash))
        
        admin_id = cursor.lastrowid
        conn.commit()
        
        print(f"✓ Admin account created: {email}")
        return admin_id
        
    except sqlite3.IntegrityError as e:
        print(f"✗ Error: User with email {email} already exists")
        return None
    except Exception as e:
        print(f"✗ Error creating admin: {str(e)}")
        conn.rollback()
        return None
    finally:
        conn.close()


def migrate_existing_transcripts(db_path, admin_id):
    """Assign existing transcripts to admin user"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if user_id column exists
        cursor.execute("PRAGMA table_info(transcripts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print("✗ user_id column does not exist yet")
            conn.close()
            return
        
        # Count transcripts without user_id
        cursor.execute("SELECT COUNT(*) FROM transcripts WHERE user_id IS NULL")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("✓ No unassigned transcripts found")
            conn.close()
            return
        
        # Assign to admin
        cursor.execute("UPDATE transcripts SET user_id = ? WHERE user_id IS NULL", (admin_id,))
        conn.commit()
        
        print(f"✓ Assigned {count} existing transcripts to admin")
        
    except Exception as e:
        print(f"✗ Error migrating transcripts: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


def verify_migration(db_path):
    """Verify that migration was successful"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("MIGRATION VERIFICATION")
    print("="*60)
    
    try:
        # Check users table
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"✓ Users table: {user_count} user(s)")
        
        # Check admin exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        print(f"✓ Admin accounts: {admin_count}")
        
        # Check account_requests table
        cursor.execute("SELECT COUNT(*) FROM account_requests")
        request_count = cursor.fetchone()[0]
        print(f"✓ Account requests table: {request_count} request(s)")
        
        # Check transcripts have user_id column
        cursor.execute("PRAGMA table_info(transcripts)")
        columns = [col[1] for col in cursor.fetchall()]
        has_user_id = 'user_id' in columns
        print(f"✓ Transcripts table has user_id: {has_user_id}")
        
        # Check unassigned transcripts
        if has_user_id:
            cursor.execute("SELECT COUNT(*) FROM transcripts WHERE user_id IS NULL")
            unassigned = cursor.fetchone()[0]
            print(f"✓ Unassigned transcripts: {unassigned}")
        
        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        indexes = cursor.fetchall()
        print(f"✓ Indexes created: {len(indexes)}")
        
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Verification failed: {str(e)}")
        return False
    finally:
        conn.close()


def main():
    """Main migration function"""
    print("="*60)
    print("YouTube Transcription Tool - Multi-User Migration (FIXED)")
    print("="*60)
    print()
    
    # Get database path
    db_path = input("Database path (default: transcripts.db): ").strip() or 'transcripts.db'
    
    print(f"\nUsing database: {db_path}")
    
    # Step 1: Backup
    print("\n[1/6] Creating backup...")
    backup_path = backup_database(db_path)
    
    # Step 2: Initialize schema
    print("\n[2/6] Initializing database schema...")
    if not init_database_schema(db_path):
        print("\n✗ Schema initialization failed. Check errors above.")
        sys.exit(1)
    
    # Step 3: Get admin credentials
    print("\n[3/6] Admin account setup")
    print("You need to create an admin account to manage users.")
    
    admin_email = input("Admin email: ").strip()
    while not admin_email or '@' not in admin_email:
        print("Invalid email address")
        admin_email = input("Admin email: ").strip()
    
    admin_password = input("Admin password (min 12 chars): ").strip()
    while len(admin_password) < 12:
        print("Password must be at least 12 characters")
        admin_password = input("Admin password (min 12 chars): ").strip()
    
    # Step 4: Create admin account
    print("\n[4/6] Creating admin account...")
    admin_id = create_admin_account(db_path, admin_email, admin_password)
    
    if not admin_id:
        print("\n✗ Failed to create admin account")
        sys.exit(1)
    
    # Step 5: Migrate existing transcripts
    print("\n[5/6] Migrating existing transcripts...")
    migrate_existing_transcripts(db_path, admin_id)
    
    # Step 6: Verification
    print("\n[6/6] Verifying migration...")
    if not verify_migration(db_path):
        print("\n⚠️  Migration completed with warnings. Please check above.")
    
    # Success message
    print("\n" + "="*60)
    print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Update your .env file with required variables:")
    print("   - SECRET_KEY (for sessions)")
    print("   - SMTP_USERNAME, SMTP_PASSWORD (for emails)")
    print("   - SMTP_SERVER, SMTP_PORT (default: Gmail)")
    print()
    print("2. Install new dependencies:")
    print("   pip install Flask-Login")
    print()
    print("3. Test the admin login:")
    print(f"   Email: {admin_email}")
    print(f"   Password: [your password]")
    print()
    print("4. Start the application and test!")
    print()
    
    if backup_path:
        print(f"Backup saved at: {backup_path}")
        print("Keep this backup until you verify everything works!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during migration: {str(e)}")
        print("Your original database is backed up. Check the error and try again.")
        import traceback
        traceback.print_exc()
        sys.exit(1)