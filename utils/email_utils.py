# utils/email_utils.py
import smtplib
from email.message import EmailMessage
import os
import mimetypes

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "vinayks705@gmail.com"  # your Gmail
EMAIL_PASSWORD = "orcktbihudzvroju"     # app-specific password

def send_email(to_addr, subject, body):
    """Send a simple email without attachments."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_addr
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Email sent to {to_addr}: {subject}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def send_email_with_attachment(to_addr, subject, body, attachment_path=None):
    """Send email with optional attachment."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_addr
    msg.set_content(body)

    if attachment_path:
        if not os.path.exists(attachment_path):
            print(f"⚠️ Attachment not found: {attachment_path}")
        else:
            filename = os.path.basename(attachment_path)
            # Try to guess MIME type
            mime_type, _ = mimetypes.guess_type(attachment_path)
            if mime_type is None:
                mime_type = "application/octet-stream"
            maintype, subtype = mime_type.split("/", 1)
            
            with open(attachment_path, "rb") as f:
                file_data = f.read()
            
            msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=filename)
            print(f"📎 Attachment added: {filename}")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Email with attachment sent to {to_addr}: {subject}")
    except Exception as e:
        print(f"❌ Failed to send email with attachment: {e}")
