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


def send_email(to_email: str, subject: str, html: str):
    import os

    if os.getenv("DEV_EMAIL_MODE", "false").lower() == "true":
        return {
            "ok": True,
            "dev_code": _extract_dev_code(html),
        }

    try:
        import resend
    except ImportError as exc:
        raise RuntimeError("The resend package is not installed on the backend.") from exc

    api_key = os.getenv("RESEND_API_KEY")

    if not api_key:
        return {
            "ok": False,
            "error": "RESEND_API_KEY is not configured"
        }

    try:
        resend.api_key = api_key

        result = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [to_email],
            "subject": subject,
            "html": html,
        })

        return {
            "ok": True,
            "id": getattr(result, "id", None)
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc)
        }

def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def otp_expiry() -> datetime:
    # email_otps.expires_at is TIMESTAMP WITHOUT TIME ZONE; store UTC as naive datetime.
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=OTP_TTL_MINUTES)
