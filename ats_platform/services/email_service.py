import os
import aiosmtplib

from email.message import EmailMessage

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))


async def send_otp_email(receiver_email: str, otp: str):

    print("SMTP EMAIL:", SMTP_EMAIL)
    print("SMTP HOST:", SMTP_HOST)
    print("SMTP PORT:", SMTP_PORT)

    message = EmailMessage()

    message["From"] = SMTP_EMAIL
    message["To"] = receiver_email
    message["Subject"] = "TalentHit OTP Verification"

    message.set_content(f"""
Your OTP is: {otp}

This OTP expires in 5 minutes.
""")

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_EMAIL,
            password=SMTP_PASSWORD,
            timeout=10
        )

        print("✅ OTP EMAIL SENT")

    except Exception as e:
        print("❌ EMAIL ERROR:", str(e))
        raise Exception(f"Email sending failed: {str(e)}")