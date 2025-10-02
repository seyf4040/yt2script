#!/usr/bin/env python3
"""
Migration script to add formatted transcripts to existing database entries
Run this after updating to the new version with formatted transcript support
"""

import sqlite3
import os
from openai import OpenAI
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
CLEANING_MODEL = os.getenv('CLEANING_MODEL', 'gpt-4o-mini')

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
        print(f"  Formatting with {CLEANING_MODEL}...")
        response = client.chat.completions.create(
            model=CLEANING_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Video Title: {video_title}\n\nTranscript:\n{clean_transcript}"}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"  Error formatting: {str(e)}")
        return None


def migrate_database(db_path='transcripts.db', skip_existing=True, delay_seconds=2):
    """
    Migrate existing transcripts to add formatted versions
    
    Args:
        db_path: Path to the database file
        skip_existing: If True, skip transcripts that already have formatted versions
        delay_seconds: Delay between API calls to avoid rate limits
    """
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    # Check if API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not set in environment")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if formatted_transcript column exists
    cursor.execute("PRAGMA table_info(transcripts)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'formatted_transcript' not in columns:
        print("Adding formatted_transcript column...")
        cursor.execute('ALTER TABLE transcripts ADD COLUMN formatted_transcript TEXT')
        conn.commit()
        print("✅ Column added")
    
    # Get all transcripts that need formatting
    if skip_existing:
        query = '''
            SELECT id, video_title, transcript 
            FROM transcripts 
            WHERE formatted_transcript IS NULL OR formatted_transcript = ''
            ORDER BY id
        '''
    else:
        query = 'SELECT id, video_title, transcript FROM transcripts ORDER BY id'
    
    cursor.execute(query)
    transcripts = cursor.fetchall()
    
    if not transcripts:
        print("✅ No transcripts need migration")
        conn.close()
        return
    
    print(f"\n📊 Found {len(transcripts)} transcript(s) to migrate")
    print(f"💰 Estimated cost: ${len(transcripts) * 0.02:.2f} (at ~$0.02 per transcript)")
    
    proceed = input("\nProceed with migration? (y/n): ")
    if proceed.lower() != 'y':
        print("Migration cancelled")
        conn.close()
        return
    
    print("\n🚀 Starting migration...\n")
    
    success_count = 0
    error_count = 0
    
    for i, row in enumerate(transcripts, 1):
        transcript_id = row['id']
        video_title = row['video_title'] or 'Untitled'
        transcript_text = row['transcript']
        
        print(f"[{i}/{len(transcripts)}] Processing ID {transcript_id}: {video_title[:50]}...")
        
        try:
            formatted_text = format_transcript(transcript_text, video_title)
            
            if formatted_text:
                # Update database
                cursor.execute(
                    'UPDATE transcripts SET formatted_transcript = ? WHERE id = ?',
                    (formatted_text, transcript_id)
                )
                conn.commit()
                print(f"  ✅ Success")
                success_count += 1
            else:
                print(f"  ⚠️  Formatting returned None")
                error_count += 1
            
            # Delay to avoid rate limits
            if i < len(transcripts):
                print(f"  ⏳ Waiting {delay_seconds} seconds...")
                time.sleep(delay_seconds)
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            error_count += 1
            continue
    
    conn.close()
    
    print("\n" + "="*60)
    print("MIGRATION COMPLETE")
    print("="*60)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total: {len(transcripts)}")


def preview_formatting(db_path='transcripts.db', transcript_id=None):
    """Preview the formatted version of a transcript without saving"""
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if transcript_id:
        cursor.execute('SELECT id, video_title, transcript FROM transcripts WHERE id = ?', (transcript_id,))
    else:
        cursor.execute('SELECT id, video_title, transcript FROM transcripts ORDER BY id DESC LIMIT 1')
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("❌ No transcript found")
        return
    
    print(f"\n📝 Preview for ID {row['id']}: {row['video_title']}")
    print("="*60)
    
    formatted = format_transcript(row['transcript'], row['video_title'])
    
    if formatted:
        print(formatted)
        print("\n" + "="*60)
        print("Preview complete. Run migrate_database() to save formatted versions.")
    else:
        print("❌ Formatting failed")


if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("YouTube Transcription Tool - Migration Script")
    print("="*60)
    print("\nThis script will add formatted versions to existing transcripts.")
    print("It will use the OpenAI API, which will incur costs (~$0.02 per transcript).\n")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'preview':
            # Preview mode
            transcript_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
            preview_formatting(transcript_id=transcript_id)
        elif command == 'migrate':
            # Full migration
            migrate_database()
        else:
            print("Usage:")
            print("  python migrate_formatted.py migrate    # Migrate all transcripts")
            print("  python migrate_formatted.py preview    # Preview last transcript")
            print("  python migrate_formatted.py preview 5  # Preview transcript ID 5")
    else:
        # Interactive mode
        print("Commands:")
        print("1. Migrate all transcripts")
        print("2. Preview formatting")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ")
        
        if choice == '1':
            migrate_database()
        elif choice == '2':
            transcript_id = input("Enter transcript ID (or press Enter for latest): ")
            preview_formatting(transcript_id=int(transcript_id) if transcript_id else None)
        else:
            print("Exiting...")