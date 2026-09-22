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


