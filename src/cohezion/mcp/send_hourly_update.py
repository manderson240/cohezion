import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def load_env_manual():
    env_path = Path("/home/mike-anderson/dev/cohezion/.env")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)


def send_email(subject, body, recipient=None):
    load_env_manual()

    sender_email = os.getenv("NOTIFICATION_EMAIL")
    password = os.getenv("NOTIFICATION_PASSWORD")
    recipient_email = recipient or os.getenv("NOTIFICATION_RECIPIENT")

    if not all([sender_email, password, recipient_email]):
        print("Error: Email credentials not found in .env")
        return False

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        # Using Gmail SMTP
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.close()
        print(f"Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python3 send_hourly_update.py <subject> <body_file_path>")
        sys.exit(1)

    subject = sys.argv[1]
    body_path = Path(sys.argv[2])

    if not body_path.exists():
        print(f"Error: Body file {body_path} not found")
        sys.exit(1)

    with open(body_path) as f:
        body = f.read()

    send_email(subject, body)
