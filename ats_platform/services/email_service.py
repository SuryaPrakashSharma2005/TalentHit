import os
import asyncio
import resend

resend.api_key = os.getenv("RESEND_API_KEY")


async def send_otp_email(receiver_email: str, otp: str):
    try:
        params = {
            "from": "TalentHit <onboarding@resend.dev>",
            "to": [receiver_email],
            "subject": "Your TalentHit Verification Code",
            "html": f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>TalentHit OTP Verification</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        margin: 0;
                        padding: 0;
                        background-color: #f4f4f4;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #ffffff;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 24px;
                        font-weight: 600;
                    }}
                    .content {{
                        padding: 40px 30px;
                        text-align: center;
                    }}
                    .otp-code {{
                        background-color: #f8f9fa;
                        border: 2px dashed #667eea;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 30px 0;
                        font-size: 32px;
                        font-weight: bold;
                        color: #333;
                        letter-spacing: 4px;
                        display: inline-block;
                    }}
                    .message {{
                        color: #666;
                        font-size: 16px;
                        line-height: 1.6;
                        margin-bottom: 20px;
                    }}
                    .warning {{
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        color: #856404;
                        padding: 15px;
                        border-radius: 4px;
                        font-size: 14px;
                        margin-top: 20px;
                    }}
                    .footer {{
                        background-color: #f8f9fa;
                        padding: 20px 30px;
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                    }}
                    .footer p {{
                        margin: 5px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 TalentHit</h1>
                        <p>Secure Verification</p>
                    </div>
                    <div class="content">
                        <h2>Welcome to TalentHit!</h2>
                        <p class="message">
                            To complete your registration and secure your account, please use the verification code below:
                        </p>
                        <div class="otp-code">{otp}</div>
                        <p class="message">
                            This code will expire in <strong>5 minutes</strong> for security reasons.
                        </p>
                        <div class="warning">
                            ⚠️ If you didn't request this code, please ignore this email. Your account remains secure.
                        </div>
                    </div>
                    <div class="footer">
                        <p><strong>TalentHit</strong> - Connecting Talent with Opportunity</p>
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; 2024 TalentHit. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
        }

        # Run the synchronous resend call in a thread to avoid blocking
        result = await asyncio.to_thread(resend.Emails.send, params)
        return result
    except Exception as e:
        print(f"Failed to send OTP email to {receiver_email}: {str(e)}")
        raise e