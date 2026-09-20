import base64
import hashlib
import hmac
import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env even when this module is imported directly in a test.
load_dotenv(Path(__file__).resolve().parent / ".env")

TOKEN_TTL_HOURS = 24
OTP_TTL_MINUTES = 10


def _secret() -> str:
    return os.getenv("AUTH_SECRET", "CHANGE_ME_LOCAL_ONLY")


def hash_value(value: str) -> str:
    return hashlib.sha256((value.strip() + _secret()).encode("utf-8")).hexdigest()


def make_token(user_id: int, role: str, email: str = "") -> str:
    exp = int((datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).timestamp())
    payload = f"{user_id}|{role}|{email}|{exp}"
    sig = hmac.new(_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode("utf-8")).decode("ascii")


def read_token(token: str):
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        user_id, role, email, exp, sig = raw.split("|", 4)
        payload = f"{user_id}|{role}|{email}|{exp}"
        expected = hmac.new(_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        if int(exp) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return {"user_id": int(user_id), "role": role, "email": email}
    except Exception:
        return None


def _extract_dev_code(body: str) -> str | None:
    match = re.search(r"(?:verification|login verification)\s+code\s*:?\s*(\d{6})", body, re.IGNORECASE)
    return match.group(1) if match else None


def send_email(to_email: str, subject: str, body: str):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", username or "")

    # Safe local-demo path: never use this for production.
    if not all([host, username, password, sender]):
        if os.getenv("DEV_EMAIL_MODE", "false").lower() == "true":
            code = _extract_dev_code(body)
            if not code:
                raise RuntimeError("DEV_EMAIL_MODE is enabled but no 6-digit OTP was found in the email body.")
            return {"sent": False, "dev_code": code}
        raise RuntimeError(
            "Email service is not configured. For local testing set DEV_EMAIL_MODE=true, "
            "or configure SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
    return {"sent": True}


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def otp_expiry() -> datetime:
    # email_otps.expires_at is TIMESTAMP WITHOUT TIME ZONE; store UTC as naive datetime.
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=OTP_TTL_MINUTES)
