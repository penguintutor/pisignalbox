import json
import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)

def send_reset_email(config_path, to_email, reset_url):
    # Attempt to load the JSON config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.warning("mail_config.json not found. Skipping password reset email.")
        return
    except json.JSONDecodeError:
        logger.warning("mail_config.json is malformed. Skipping password reset email.")
        return

    # Construct the email
    msg = EmailMessage()
    msg['Subject'] = 'Password Reset Request'
    msg['From'] = config.get('SMTP_USER')
    msg['To'] = to_email
    msg.set_content(f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, simply ignore this email and no changes will be made.
''')

    # Send the email
    try:
        # Use SMTP_SSL for port 465
        with smtplib.SMTP_SSL(config.get('SMTP_SERVER'), config.get('SMTP_PORT', 465)) as server:
            server.login(config.get('SMTP_USER'), config.get('SMTP_PASS'))
            server.send_message(msg)
            logger.info(f"Password reset email sent to {to_email}")
    except Exception as e:
        logger.warning(f"Failed to send email via SMTP: {e}")