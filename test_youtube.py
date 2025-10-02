#!/usr/bin/env python3
"""
Test script to verify YouTube download functionality
Run this to test if your fixes are working correctly
"""

import os
import sys
import tempfile
import yt_dlp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test URLs (use short, public videos)
TEST_URLS = [
    "https://www.youtube.com/watch?v=NqxiF84-eSM",  # Short test video
    # Add more test URLs as needed
]


def test_ytdlp_installation():
    """Test if yt-dlp is properly installed"""
    print("=" * 60)
    print("TEST 1: Checking yt-dlp installation")
    print("=" * 60)
    
    try:
        import yt_dlp
        print(f"✅ yt-dlp is installed")
        print(f"   Version: {yt_dlp.version.__version__}")
        return True
    except ImportError:
        print("❌ yt-dlp is not installed")
        print("   Install with: pip install yt-dlp")
        return False


def test_ffmpeg_installation():
    """Test if FFmpeg is properly installed"""
    print("\n" + "=" * 60)
    print("TEST 2: Checking FFmpeg installation")
    print("=" * 60)
    
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg is installed")
            print(f"   {version_line}")
            return True
        else:
            print("❌ FFmpeg returned an error")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg is not installed or not in PATH")
        print("   Install instructions:")
        print("   - macOS: brew install ffmpeg")
        print("   - Ubuntu: sudo apt-get install ffmpeg")
        print("   - Windows: Download from ffmpeg.org")
        return False
    except Exception as e:
        print(f"❌ Error checking FFmpeg: {str(e)}")
        return False


def test_openai_key():
    """Test if OpenAI API key is set"""
    print("\n" + "=" * 60)
    print("TEST 3: Checking OpenAI API Key")
    print("=" * 60)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 11 else "***"
        print(f"✅ OPENAI_API_KEY is set")
        print(f"   Key: {masked_key}")
        
        # Test if key is valid format
        if api_key.startswith('sk-'):
            print(f"   Format: Valid (starts with sk-)")
        else:
            print(f"   ⚠️  Warning: Key doesn't start with 'sk-'")
        return True
    else:
        print("❌ OPENAI_API_KEY is not set")
        print("   Set it in .env file or environment")
        return False


def test_youtube_download(url):
    """Test downloading audio from YouTube"""
    print("\n" + "=" * 60)
    print(f"TEST 4: Testing YouTube Download")
    print("=" * 60)
    print(f"URL: {url}")
    
    temp_dir = tempfile.gettempdir()
    output_template = os.path.join(temp_dir, 'test_%(id)s.%(ext)s')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'referer': 'https://www.youtube.com/',
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'age_limit': None,
        'geo_bypass': True,
    }
    
    try:
        print("\nDownloading...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info:
                video_id = info.get('id')
                video_title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                
                audio_file = os.path.join(temp_dir, f"test_{video_id}.mp3")
                
                print(f"\n✅ Download successful!")
                print(f"   Title: {video_title}")
                print(f"   Duration: {duration}s")
                print(f"   File: {audio_file}")
                
                # Check if file exists
                if os.path.exists(audio_file):
                    file_size = os.path.getsize(audio_file)
                    print(f"   File size: {file_size / 1024 / 1024:.2f} MB")
                    
                    # Cleanup
                    os.remove(audio_file)
                    print(f"   Cleanup: File removed")
                    return True
                else:
                    print(f"   ❌ Audio file not found at expected location")
                    return False
            else:
                print("❌ Failed to extract video information")
                return False
                
    except yt_dlp.utils.DownloadError as e:
        print(f"❌ Download Error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return False


def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n" + "=" * 60)
    print("TEST 5: Testing OpenAI API Connection")
    print("=" * 60)
    
    try:
        from openai import OpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  Skipping: No API key found")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # Test with a simple request
        print("Making test API call...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=5
        )
        
        print("✅ OpenAI API is working!")
        print(f"   Response: {response.choices[0].message.content}")
        return True
        
    except ImportError:
        print("❌ OpenAI library not installed")
        print("   Install with: pip install openai")
        return False
    except Exception as e:
        print(f"❌ OpenAI API Error: {str(e)}")
        print("   Check your API key and billing status")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("YouTube Transcription Tool - System Test")
    print("=" * 60 + "\n")
    
    results = {
        'yt-dlp': test_ytdlp_installation(),
        'ffmpeg': test_ffmpeg_installation(),
        'openai_key': test_openai_key(),
        'youtube': False,
        'openai_api': False
    }
    
    # Only test YouTube download if basic requirements are met
    if results['yt-dlp'] and results['ffmpeg']:
        results['youtube'] = test_youtube_download(TEST_URLS[0])
    else:
        print("\n⚠️  Skipping YouTube download test (missing dependencies)")
    
    # Only test OpenAI if key is set
    if results['openai_key']:
        results['openai_api'] = test_openai_connection()
    else:
        print("\n⚠️  Skipping OpenAI API test (no API key)")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your system is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())