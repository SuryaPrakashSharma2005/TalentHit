import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")


async def send_otp_email(receiver_email: str, otp: str):

    params = {
        "from": "TalentHit <onboarding@resend.dev>",
        "to": [receiver_email],
        "subject": "TalentHit OTP Verification",
        "html": f"""
        <div style="font-family: Arial; padding: 20px;">
            <h2>TalentHit Verification</h2>

            <p>Your OTP is:</p>

            <h1>{otp}</h1>

            <p>This OTP expires in 5 minutes.</p>
        </div>
        """,
    }

    resend.Emails.send(params)