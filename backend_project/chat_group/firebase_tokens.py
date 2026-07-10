"""
Выпуск Firebase custom tokens без firebase-admin.

Custom token — это обычный RS256-JWT, подписанный ключом сервисного
аккаунта (официальный способ «third-party JWT library»:
https://firebase.google.com/docs/auth/admin/create-custom-tokens).

firebase-admin намеренно не используется: свежие версии требуют
google-cloud-firestore>=2.21, а fireo требует ровно 2.11.1
(см. requirements.txt).
"""

import json
import time

import jwt
from django.conf import settings

_AUDIENCE = (
    'https://identitytoolkit.googleapis.com/'
    'google.identity.identitytoolkit.v1.IdentityToolkit'
)

# Максимальное время жизни custom token, разрешённое Firebase.
# Сессия Firebase на клиенте после signInWithCustomToken живёт дольше
# и продлевается SDK автоматически.
TOKEN_LIFETIME_SECONDS = 3600

_service_account: dict | None = None


def _get_service_account() -> dict:
    global _service_account
    if _service_account is None:
        with open(settings.FIREBASE_CREDENTIALS, encoding='utf-8') as f:
            _service_account = json.load(f)
    return _service_account


def create_custom_token(uid: str, claims: dict) -> str:
    """
    uid — ID пользователя из Firestore (users/{id}), станет request.auth.uid.
    claims — попадут в request.auth.token в security rules.
    """
    sa = _get_service_account()
    now = int(time.time())
    payload = {
        'iss': sa['client_email'],
        'sub': sa['client_email'],
        'aud': _AUDIENCE,
        'iat': now,
        'exp': now + TOKEN_LIFETIME_SECONDS,
        'uid': uid,
        'claims': claims,
    }
    return jwt.encode(payload, sa['private_key'], algorithm='RS256')
