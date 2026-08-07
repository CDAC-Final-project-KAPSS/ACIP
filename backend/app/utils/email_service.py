import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "p4shinde2003@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

def send_otp_email(to_email: str, otp_code: str):
    if not SMTP_PASSWORD or SMTP_PASSWORD == "your_google_app_password_here":
        print(f"MOCK EMAIL to {to_email}: OTP is {otp_code} (SMTP_PASSWORD not set)")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = "ACIP Platform - Your Verification Code"
        
        body = f"""
        Hello,
        
        Your verification code for the ACIP Platform is: {otp_code}
        
        This code will expire shortly.
        
        Regards,
        ACIP Security Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
