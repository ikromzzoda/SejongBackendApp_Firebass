import uuid
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings

ALGORITHM = 'HS256'
TOKEN_LIFETIME_DAYS = 1


def generate_token(user_id: str, username: str, status: str, verification_status: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'username': username,
        'status': status,
        'verification_status': verification_status,
        'iat': now,
        'exp': now + timedelta(days=TOKEN_LIFETIME_DAYS),
        'jti': str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
