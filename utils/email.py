import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def send_contractor_email(to_email: str, username: str, password: str, identifier: str):
    # Load email credentials from environment variables
    EMAIL_ADDRESS = settings.EMAIL_ADDRESS
    EMAIL_PASSWORD = settings.EMAIL_PASSWORD

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise RuntimeError("Email credentials not configured")

    subject = "Your Contractor Account Credentials"
    body = f"""
    Hello {username},

    Your contractor account has been created successfully.

    Username: {username}
    Identifier: {identifier}
    Password: {password}

    Please log in and change your password immediately for security.

    Regards,
    Site Lens Team
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Connect securely to Gmail SMTP server
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
    print(f"Contractor credentials sent to {to_email}")
