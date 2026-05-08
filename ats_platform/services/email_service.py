import os
import aiosmtplib

from email.message import EmailMessage

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))


async def send_otp_email(receiver_email: str, otp: str):

    message = EmailMessage()

    message["From"] = SMTP_EMAIL
    message["To"] = receiver_email
    message["Subject"] = "TalentHit Email Verification OTP"

    message.set_content(f"""
Your TalentHit verification OTP is:

{otp}

This OTP will expire in 5 minutes.

Do not share this OTP with anyone.
""")

    await aiosmtplib.send(
        message,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        start_tls=True,
        username=SMTP_EMAIL,
        password=SMTP_PASSWORD,
    )