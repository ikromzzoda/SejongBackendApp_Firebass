import uuid
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings

ALGORITHM = 'HS256'
TOKEN_LIFETIME_DAYS         = 1
REFRESH_TOKEN_LIFETIME_DAYS = 30


def generate_token(user_id: str, username: str, status: str, verification_status: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'user_id':             user_id,
        'username':            username,
        'status':              status,
        'verification_status': verification_status,
        'type': 'access',
        'iat':  now,
        'exp':  now + timedelta(days=TOKEN_LIFETIME_DAYS),
        'jti':  str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def generate_refresh_token(user_id: str) -> tuple[str, str]:
    """Returns (token, jti)."""
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    payload = {
        'user_id': user_id,
        'type': 'refresh',
        'iat':  now,
        'exp':  now + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS),
        'jti':  jti,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM), jti


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
