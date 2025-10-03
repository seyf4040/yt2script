"""
Email service using SMTP (Real Python approach)
Supports Gmail, Office365, and custom SMTP servers
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


logger = logging.getLogger(__name__)


class EmailService:
    """SMTP Email Service"""
    
    def __init__(self):
        """Initialize email service with environment variables"""
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('EMAIL_FROM', self.smtp_username)
        self.app_name = os.getenv('APP_NAME', 'YouTube Transcription Tool')
        self.app_url = os.getenv('APP_URL', 'http://localhost:8501')
        
        # Validate configuration
        if not self.smtp_username or not self.smtp_password:
            logger.warning("Email service not configured. Set SMTP_USERNAME and SMTP_PASSWORD")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Email service configured: {self.smtp_server}:{self.smtp_port}")
    
    def send_email(self, to_email, subject, html_content, text_content=None):
        """
        Send an email using SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text alternative (optional)
        
        Returns:
            (success: bool, error: str or None)
        """
        if not self.enabled:
            logger.error("Email service not enabled")
            return False, "Email service not configured"
        
        try:
            # Create message
            from_name = os.getenv('EMAIL_FROM_NAME', self.app_name)
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.app_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Add plain text version (fallback)
            if not text_content:
                text_content = self._html_to_text(html_content)
            
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            
            message.attach(part1)
            message.attach(part2)
            
            # Create secure SSL context
            context = ssl.create_default_context()
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, to_email, message.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True, None
            
        except smtplib.SMTPAuthenticationError:
            error = "SMTP authentication failed. Check username and password."
            logger.error(error)
            return False, error
        except smtplib.SMTPException as e:
            error = f"SMTP error: {str(e)}"
            logger.error(error)
            return False, error
        except Exception as e:
            error = f"Failed to send email: {str(e)}"
            logger.error(error)
            return False, error
    
    def _html_to_text(self, html):
        """Simple HTML to text conversion for plain text alternative"""
        import re
        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html)
        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    # ========== PRE-DEFINED EMAIL TEMPLATES ==========
    
    def send_account_request_notification(self, admin_email, requester_email):
        """Notify admin of new account request"""
        subject = f"New Account Request - {self.app_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">New Account Request</h2>
                
                <p>A new user has requested an account:</p>
                
                <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Email:</strong> {requester_email}<br>
                    <strong>Requested:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                
                <p>Please review and approve/reject this request in the admin dashboard:</p>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{self.app_url}" 
                       style="background-color: #3498db; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Go to Admin Dashboard
                    </a>
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated notification from {self.app_name}
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(admin_email, subject, html_content)
    
    def send_account_approved_email(self, user_email, temp_password):
        """Send account approval email with temporary password"""
        subject = f"Your Account Has Been Approved - {self.app_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #27ae60;">✓ Account Approved!</h2>
                
                <p>Great news! Your account request has been approved.</p>
                
                <p>You can now log in with the following credentials:</p>
                
                <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; 
                            margin: 20px 0; border-left: 4px solid #27ae60;">
                    <strong>Email:</strong> {user_email}<br>
                    <strong>Temporary Password:</strong> <code style="background-color: #fff; 
                           padding: 2px 6px; border-radius: 3px;">{temp_password}</code>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; 
                            margin: 20px 0; border-left: 4px solid #ffc107;">
                    <strong>⚠️ Important:</strong>
                    <ul style="margin: 10px 0;">
                        <li>This is a temporary password</li>
                        <li>You will be required to change it on your first login</li>
                        <li>Choose a strong password with at least 12 characters</li>
                    </ul>
                </div>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{self.app_url}" 
                       style="background-color: #27ae60; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Log In Now
                    </a>
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    If you didn't request this account, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user_email, subject, html_content)
    
    def send_account_rejected_email(self, user_email, reason=None):
        """Send account rejection email"""
        subject = f"Account Request Update - {self.app_name}"
        
        reason_text = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">Account Request Update</h2>
                
                <p>Thank you for your interest in {self.app_name}.</p>
                
                <p>Unfortunately, we are unable to approve your account request at this time.</p>
                
                {reason_text}
                
                <p>If you have questions or believe this is an error, please contact support.</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated notification from {self.app_name}
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user_email, subject, html_content)
    
    def send_password_changed_email(self, user_email):
        """Send password change confirmation"""
        subject = f"Password Changed - {self.app_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Password Changed</h2>
                
                <p>Your password has been successfully changed.</p>
                
                <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; 
                            margin: 20px 0; border-left: 4px solid #27ae60;">
                    <strong>Account:</strong> {user_email}<br>
                    <strong>Changed:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; 
                            margin: 20px 0; border-left: 4px solid #ffc107;">
                    <strong>⚠️ Security Notice:</strong><br>
                    If you did not make this change, please contact support immediately.
                </div>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated notification from {self.app_name}
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user_email, subject, html_content)
    
    def test_connection(self):
        """Test email service connection"""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.smtp_username, self.smtp_password)
            
            logger.info("Email service test successful")
            return True, "Connection successful"
        except Exception as e:
            error = f"Connection failed: {str(e)}"
            logger.error(error)
            return False, error


# Singleton instance
email_service = EmailService()