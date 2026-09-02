import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from typing import Optional
import os
from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM_NAME, DEV_SHOW_OTP

class EmailService:
    """Service for sending emails (OTP, welcome, etc.)"""
    
    @staticmethod
    def send_otp_email(to_email: str, otp: str, name: str = "User") -> bool:
        """Send OTP verification email with RFC 5322 compliant dual text/html MIME structure"""
        
        # In dev mode with explicit flag, print to console
        if DEV_SHOW_OTP:
            print(f"\n{'='*60}")
            print(f"[EMAIL] EMAIL OTP (DEV MODE)")
            print(f"{'='*60}")
            print(f"To: {to_email}")
            print(f"Name: {name}")
            print(f"OTP: {otp}")
            print(f"{'='*60}\n")
            return True

        if not EMAIL_USER or not EMAIL_PASSWORD:
            print(f"[WARNING] Cannot send OTP email to {to_email}: EMAIL_USER or EMAIL_PASSWORD environment variables are not configured.")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
            msg['To'] = to_email
            msg['Reply-To'] = EMAIL_USER
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = '🔐 Verify Your WealthSense Account'
            
            # Plain text part for strict spam filter compliance (RFC 2046)
            text_body = (
                f"Hi {name},\n\n"
                f"Welcome to WealthSense!\n"
                f"Your verification code is: {otp}\n\n"
                f"This code expires in 10 minutes.\n\n"
                f"© 2026 WealthSense"
            )
            
            # HTML email body
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #00f8ff, #9b59ff); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .header h1 {{ color: white; margin: 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .otp-box {{ background: white; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; border: 2px solid #00f8ff; }}
                    .otp {{ font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #00f8ff; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 Email Verification</h1>
                    </div>
                    <div class="content">
                        <p>Hi <strong>{name}</strong>,</p>
                        <p>Welcome to WealthSense! To complete your registration, please verify your email address with the code below:</p>
                        
                        <div class="otp-box">
                            <div class="otp">{otp}</div>
                        </div>
                        
                        <p><strong>This code expires in 10 minutes.</strong></p>
                        <p>If you didn't request this verification, please ignore this email.</p>
                        
                        <div class="footer">
                            <p>© 2026 WealthSense - AI-Powered Portfolio Management</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Attach plain text first, then HTML as per RFC 2046
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)
            
            print(f"[SUCCESS] OTP email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Email sending failed to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(to_email: str, name: str) -> bool:
        """Send welcome email after successful registration"""
        
        if DEV_SHOW_OTP or not EMAIL_USER or not EMAIL_PASSWORD:
            print(f"[EMAIL] Welcome email skipped for {to_email} (Dev mode or missing credentials)")
            return True
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
            msg['To'] = to_email
            msg['Reply-To'] = EMAIL_USER
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = '🎉 Welcome to WealthSense!'
            
            text_body = f"Hi {name},\n\nWelcome to WealthSense! Your account has been successfully created."
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #00f8ff, #9b59ff); padding: 30px; text-align: center;">
                    <h1 style="color: white;">Welcome to WealthSense! 🎉</h1>
                </div>
                <div style="padding: 30px; background: #f9f9f9;">
                    <p>Hi <strong>{name}</strong>,</p>
                    <p>Your account has been successfully created!</p>
                    <p>You can now:</p>
                    <ul>
                        <li>📊 Track your portfolio in real-time</li>
                        <li>🤖 Get AI-powered stock predictions</li>
                        <li>💬 Chat with our AI assistant</li>
                        <li>📰 Stay updated with market news</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Welcome email failed to {to_email}: {str(e)}")
            return False

email_service = EmailService()
