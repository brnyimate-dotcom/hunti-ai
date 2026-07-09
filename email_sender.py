import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load keys
load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def send_pitch_email(recipient_email: str, subject: str, body: str) -> str:
    """
    Sends an email using the Gmail App Password.
    Returns a success message or raises an Exception.
    """
    if not EMAIL_USER or not EMAIL_PASS:
        raise ValueError("Email credentials not found in .env file!")

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = recipient_email
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        return f"✅ Email sent successfully to {recipient_email}!"
    except Exception as e:
        raise RuntimeError(f"Failed to send email: {e}")