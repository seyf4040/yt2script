import streamlit as st
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv('API_URL', 'http://localhost:8080')

# Page config
st.set_page_config(
    page_title="YouTube Transcription Tool",
    page_icon="🎥",
    layout="wide"
)

# Initialize session state
if "api_session" not in st.session_state:
    st.session_state.api_session = requests.Session()
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'current_transcript' not in st.session_state:
    st.session_state.current_transcript = None


# ========== HELPER FUNCTIONS ==========

def check_auth():
    """Check if user is authenticated"""
    try:
        response = st.session_state.api_session.get(f"{API_URL}/auth/current-user")
        if response.status_code == 200:
            data = response.json()
            if data.get('authenticated'):
                st.session_state.authenticated = True
                st.session_state.user = data['user']
                return True
    except:
        pass
    
    st.session_state.authenticated = False
    st.session_state.user = None
    return False


def login(email, password):
    """Login user"""
    try:
        response = st.session_state.api_session.post(
            f"{API_URL}/auth/login",
            json={'email': email, 'password': password}
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.authenticated = True
            st.session_state.user = data['user']
            return True, data.get('temp_password', False), None
        else:
            error = response.json().get('error', 'Login failed')
            return False, False, error
    except Exception as e:
        return False, False, str(e)


def logout():
    """Logout user"""
    try:
        st.session_state.api_session.post(f"{API_URL}/auth/logout")
    except:
        pass
    
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.current_transcript = None


def request_account(email):
    """Request a new account"""
    try:
        response = st.session_state.api_session.post(
            f"{API_URL}/auth/request-account",
            json={'email': email}
        )
        
        if response.status_code == 200:
            return True, response.json().get('message', 'Request submitted')
        else:
            error = response.json().get('error', 'Request failed')
            return False, error
    except Exception as e:
        return False, str(e)


def change_password(current_password, new_password):
    """Change user password"""
    try:
        response = st.session_state.api_session.post(
            f"{API_URL}/auth/change-password",
            json={
                'current_password': current_password,
                'new_password': new_password
            }
        )
        
        if response.status_code == 200:
            return True, None
        else:
            error = response.json().get('error', 'Password change failed')
            return False, error
    except Exception as e:
        return False, str(e)


def make_api_request(endpoint, method='GET', data=None):
    """Helper function to make authenticated API requests"""
    headers = {'Content-Type': 'application/json'}
    url = f"{API_URL}{endpoint}"
    
    try:
        if method == 'GET':
            response = st.session_state.api_session.get(url, headers=headers)
        elif method == 'POST':
            response = st.session_state.api_session.post(url, json=data, headers=headers)
        
        return response
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None


def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp_str


# ========== AUTHENTICATION PAGES ==========

def show_login_page():
    """Display login page"""
    st.title("🎥 YouTube Transcription Tool")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔐 Login")
        
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    with st.spinner("Logging in..."):
                        success, temp_pass, error = login(email, password)
                        
                        if success:
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error(error)
    
    with col2:
        st.subheader("📝 Request Account")
        st.write("Don't have an account? Request access and an admin will review your request.")
        
        with st.form("request_form"):
            request_email = st.text_input("Your Email", key="request_email")
            request_submit = st.form_submit_button("Request Account", use_container_width=True)
            
            if request_submit:
                if not request_email:
                    st.error("Please enter your email")
                else:
                    with st.spinner("Submitting request..."):
                        success, message = request_account(request_email)
                        
                        if success:
                            st.success(message)
                            st.info("You will receive an email when your account is approved.")
                        else:
                            st.error(message)
    
    # Info section
    st.markdown("---")
    st.subheader("ℹ️ About This Tool")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🎤 AI-Powered**")
        st.write("Uses OpenAI Whisper for accurate transcription")
    
    with col2:
        st.markdown("**✨ Smart Formatting**")
        st.write("Automatically structures and highlights content")
    
    with col3:
        st.markdown("**💾 History**")
        st.write("Save and manage all your transcriptions")


def show_password_change_page():
    """Display password change page (for temp passwords)"""
    st.title("🔐 Change Password")
    st.warning("⚠️ You must change your temporary password before continuing.")
    
    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password (min 12 chars)", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        st.info("""
        **Password Requirements:**
        - At least 12 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 digit
        - At least 1 special character (!@#$%^&*...)
        """)
        
        submit = st.form_submit_button("Change Password", use_container_width=True)
        
        if submit:
            if not current_password or not new_password or not confirm_password:
                st.error("Please fill in all fields")
            elif new_password != confirm_password:
                st.error("New passwords don't match")
            else:
                with st.spinner("Changing password..."):
                    success, error = change_password(current_password, new_password)
                    
                    if success:
                        st.success("✅ Password changed successfully!")
                        st.session_state.user['temp_password'] = False
                        st.info("Redirecting...")
                        st.rerun()
                    else:
                        st.error(error)


# ========== ADMIN PAGES ==========

def show_admin_dashboard():
    """Display admin dashboard"""
    st.title("👑 Admin Dashboard")
    st.markdown("---")
    
    # Get statistics
    response = make_api_request('/admin/stats')
    
    if response and response.status_code == 200:
        stats = response.json()
        
        # Display stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Users", stats.get('total_users', 0))
        
        with col2:
            st.metric("Active Users", stats.get('active_users', 0))
        
        with col3:
            st.metric("Pending Requests", stats.get('pending_requests', 0))
        
        with col4:
            api_saved = stats.get('api_calls_saved', 0)
            cost_saved = api_saved * 0.08
            st.metric("Cost Saved", f"${cost_saved:.2f}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Transcripts", stats.get('total_transcripts', 0))
        
        with col2:
            duplicate_pct = 0
            total = stats.get('total_transcripts', 0)
            if total > 0:
                duplicate_pct = (stats.get('duplicate_transcripts', 0) / total) * 100
            st.metric("Duplicates", f"{duplicate_pct:.1f}%")


def show_pending_requests_page():
    """Display pending account requests (admin only)"""
    st.title("📬 Pending Account Requests")
    st.markdown("---")
    
    response = make_api_request('/admin/pending-requests')
    
    if response and response.status_code == 200:
        requests_data = response.json().get('requests', [])
        
        if not requests_data:
            st.info("No pending requests")
        else:
            st.write(f"**{len(requests_data)} pending request(s)**")
            st.markdown("---")
            
            for req in requests_data:
                with st.expander(f"📧 {req['email']} - {format_timestamp(req['requested_at'])}"):
                    st.write(f"**Request ID:** {req['id']}")
                    st.write(f"**Email:** {req['email']}")
                    st.write(f"**Requested:** {format_timestamp(req['requested_at'])}")
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{req['id']}"):
                            with st.spinner("Approving..."):
                                resp = make_api_request(
                                    f"/admin/approve-request/{req['id']}",
                                    method='POST'
                                )
                                
                                if resp and resp.status_code == 200:
                                    st.success("Account approved! Email sent to user.")
                                    st.rerun()
                                else:
                                    error = resp.json().get('error', 'Failed') if resp else 'Failed'
                                    st.error(error)
                    
                    with col2:
                        if st.button("❌ Reject", key=f"reject_{req['id']}"):
                            st.session_state[f"rejecting_{req['id']}"] = True
                    
                    # Show rejection reason form if button clicked
                    if st.session_state.get(f"rejecting_{req['id']}", False):
                        reason = st.text_area("Rejection reason (optional)", key=f"reason_{req['id']}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("Confirm Reject", key=f"confirm_reject_{req['id']}"):
                                with st.spinner("Rejecting..."):
                                    resp = make_api_request(
                                        f"/admin/reject-request/{req['id']}",
                                        method='POST',
                                        data={'reason': reason}
                                    )
                                    
                                    if resp and resp.status_code == 200:
                                        st.success("Request rejected")
                                        st.session_state[f"rejecting_{req['id']}"] = False
                                        st.rerun()
                                    else:
                                        st.error("Failed to reject")
                        
                        with col_b:
                            if st.button("Cancel", key=f"cancel_reject_{req['id']}"):
                                st.session_state[f"rejecting_{req['id']}"] = False
                                st.rerun()


def show_user_management_page():
    """Display user management page (admin only)"""
    st.title("👥 User Management")
    st.markdown("---")
    
    response = make_api_request('/admin/users')
    
    if response and response.status_code == 200:
        users = response.json().get('users', [])
        
        st.write(f"**Total Users:** {len(users)}")
        st.markdown("---")
        
        for user in users:
            status_emoji = "✅" if user['status'] == 'active' else "⏸️"
            role_emoji = "👑" if user['role'] == 'admin' else "👤"
            
            with st.expander(f"{status_emoji} {role_emoji} {user['email']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {user['id']}")
                    st.write(f"**Email:** {user['email']}")
                    st.write(f"**Role:** {user['role']}")
                
                with col2:
                    st.write(f"**Status:** {user['status']}")
                    st.write(f"**Created:** {format_timestamp(user['created_at'])}")
                    if user.get('last_login'):
                        st.write(f"**Last Login:** {format_timestamp(user['last_login'])}")
                
                # Admin actions
                if user['role'] != 'admin':  # Can't disable admins
                    st.markdown("---")
                    if user['status'] == 'active':
                        if st.button(f"🚫 Disable User", key=f"disable_{user['id']}"):
                            resp = make_api_request(
                                f"/admin/user/{user['id']}/disable",
                                method='POST'
                            )
                            if resp and resp.status_code == 200:
                                st.success("User disabled")
                                st.rerun()
                    else:
                        if st.button(f"✅ Enable User", key=f"enable_{user['id']}"):
                            resp = make_api_request(
                                f"/admin/user/{user['id']}/enable",
                                method='POST'
                            )
                            if resp and resp.status_code == 200:
                                st.success("User enabled")
                                st.rerun()


# ========== USER PAGES (Updated from original) ==========

def show_new_transcription_page():
    """New transcription page"""
    st.title("🎥 YouTube Video Transcription")
    st.markdown("---")
    
    st.info("⚠️ **AI-Powered Tool:** This application uses OpenAI's Whisper and GPT models. AI may contain errors - verify important content.")
    
    st.write("Enter a YouTube URL to transcribe the video and get a clean, formatted transcript.")
    
    with st.form("transcription_form"):
        youtube_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste the full YouTube video URL"
        )
        
        submitted = st.form_submit_button("Transcribe Video", type="primary")
        
        if submitted:
            if not youtube_url:
                st.error("Please enter a YouTube URL")
            else:
                with st.spinner("Processing... This may take a few minutes."):
                    st.info("📥 Checking for existing transcript...")
                    
                    response = make_api_request(
                        '/transcribe',
                        method='POST',
                        data={'youtube_url': youtube_url}
                    )
                    
                    if response and response.status_code == 200:
                        result = response.json()
                        st.session_state.current_transcript = result
                        
                        if result.get('duplicated'):
                            st.success("✅ Found existing transcript - copied instantly! (No API cost)")
                        else:
                            st.success("✅ New transcription completed successfully!")
                        
                        st.info("Go to 'Transcript Result' to view the transcript.")
                    elif response:
                        st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                    else:
                        st.error("Failed to connect to the API")
    
    # How it works
    st.markdown("---")
    st.subheader("How it works")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**1. Check Duplicates**")
        st.write("First checks if video was already transcribed")
    
    with col2:
        st.markdown("**2. Extract Audio**")
        st.write("Downloads audio from YouTube video (if new)")
    
    with col3:
        st.markdown("**3. Transcribe**")
        st.write("Uses OpenAI Whisper API to convert speech to text")
    
    with col4:
        st.markdown("**4. Format**")
        st.write("GPT cleans and structures the transcript")


def show_transcript_result_page():
    """Transcript result page"""
    st.title("📝 Transcript Result")
    st.markdown("---")
    
    st.warning("⚠️ **AI Disclaimer:** AI may make mistakes, mishear words, or misinterpret context. Verify accuracy for critical use.")
    
    if st.session_state.current_transcript:
        transcript = st.session_state.current_transcript
        
        # Show duplicate badge
        if transcript.get('duplicated'):
            st.success("🔄 This transcript was copied from an existing transcription (no API cost incurred)")
        
        # Display video info
        st.subheader(transcript.get('title', 'Untitled Video'))
        st.caption(f"Source: {transcript.get('url', 'N/A')}")
        st.markdown("---")
        
        # Create tabs
        tab1, tab2 = st.tabs(["📋 Clean Transcript", "✨ Formatted Version"])
        
        with tab1:
            st.markdown("### Clean Transcript")
            st.caption("Plain text version with proper punctuation and paragraphs")
            
            transcript_text = transcript.get('transcript', '')
            
            st.text_area(
                "Transcript",
                value=transcript_text,
                height=500,
                label_visibility="collapsed"
            )
            
            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 Download as TXT",
                    data=transcript_text,
                    file_name=f"transcript_clean_{transcript.get('id', 'unknown')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col2:
                st.write("PDF download available after implementing download endpoint")
        
        with tab2:
            st.markdown("### Formatted Version")
            st.caption("Structured version with titles, sections, highlights, and key takeaways")
            
            formatted_text = transcript.get('formatted_transcript', '')
            
            if formatted_text:
                st.markdown(formatted_text)
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 Download as Markdown",
                        data=formatted_text,
                        file_name=f"transcript_formatted_{transcript.get('id', 'unknown')}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                with col2:
                    st.download_button(
                        label="📥 Download as Text",
                        data=formatted_text,
                        file_name=f"transcript_formatted_{transcript.get('id', 'unknown')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
            else:
                st.info("Formatted version not available")
        
        # Clear button
        st.markdown("---")
        if st.button("Clear Result"):
            st.session_state.current_transcript = None
            st.rerun()
    
    else:
        st.info("No transcript to display. Go to 'New Transcription' to create one.")


def show_history_page():
    """History page"""
    st.title("📚 Transcription History")
    st.markdown("---")
    
    if st.button("🔄 Refresh History"):
        st.rerun()
    
    response = make_api_request('/history')
    
    if response and response.status_code == 200:
        history = response.json().get('history', [])
        
        if history:
            st.write(f"Total transcripts: {len(history)}")
            st.markdown("---")
            
            for item in history:
                # Show duplicate badge
                duplicate_badge = "🔄 Duplicated" if item.get('is_duplicate') else "✨ Original"
                
                with st.expander(
                    f"🎥 {item['video_title']} - {format_timestamp(item['created_at'])} | {duplicate_badge}"
                ):
                    st.write(f"**ID:** {item['id']}")
                    st.write(f"**URL:** [{item['youtube_url']}]({item['youtube_url']})")
                    st.write(f"**Created:** {format_timestamp(item['created_at'])}")
                    
                    if item.get('is_duplicate'):
                        st.info("🔄 This transcript was copied from an existing transcription")
                    
                    if item.get('preview'):
                        st.text(item['preview'] + "...")
                    
                    if st.button("View Full", key=f"view_{item['id']}"):
                        full_response = make_api_request(f"/transcript/{item['id']}")
                        if full_response and full_response.status_code == 200:
                            st.session_state.current_transcript = full_response.json()
                            st.info("Go to 'Transcript Result' to view")
        else:
            st.info("No transcripts found. Create your first transcription!")
    else:
        st.error("Failed to load history")


# ========== MAIN APP LOGIC ==========

def main():
    """Main application logic"""
    
    # Check authentication on load
    if not st.session_state.authenticated:
        check_auth()
    
    # Show login page if not authenticated
    if not st.session_state.authenticated:
        show_login_page()
        return
    
    # Check for temp password
    if st.session_state.user and st.session_state.user.get('temp_password'):
        show_password_change_page()
        return
    
    # Get user info
    user = st.session_state.user
    is_admin = user.get('role') == 'admin'
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # User info
    st.sidebar.markdown("---")
    st.sidebar.write(f"**Logged in as:**")
    st.sidebar.write(user['email'])
    if is_admin:
        st.sidebar.write("👑 **Admin**")
    
    # Navigation options
    if is_admin:
        pages = {
            "New Transcription": "user",
            "Transcript Result": "user",
            "History": "user",
            "---": "divider",
            "Admin Dashboard": "admin",
            "Pending Requests": "admin",
            "User Management": "admin",
        }
    else:
        pages = {
            "New Transcription": "user",
            "Transcript Result": "user",
            "History": "user",
        }
    
    # Create navigation
    page_options = [k for k in pages.keys() if k != "---"]
    page = st.sidebar.radio("Go to", page_options)
    
    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()
    
    # Display selected page
    if page == "New Transcription":
        show_new_transcription_page()
    elif page == "Transcript Result":
        show_transcript_result_page()
    elif page == "History":
        show_history_page()
    elif page == "Admin Dashboard":
        show_admin_dashboard()
    elif page == "Pending Requests":
        show_pending_requests_page()
    elif page == "User Management":
        show_user_management_page()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("YouTube Transcription Tool v3.0")
    st.sidebar.caption("Multi-User Edition")
    st.sidebar.markdown("---")
    st.sidebar.caption("⚠️ AI-powered. Verify accuracy.")


if __name__ == "__main__":
    main()