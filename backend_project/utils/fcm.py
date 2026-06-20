import json
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from django.conf import settings

_FCM_SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']


def _get_access_token() -> str:
    credentials = service_account.Credentials.from_service_account_file(
        settings.FIREBASE_CREDENTIALS,
        scopes=_FCM_SCOPES,
    )
    credentials.refresh(Request())
    return credentials.token


def _get_project_id() -> str:
    with open(settings.FIREBASE_CREDENTIALS) as f:
        return json.load(f)['project_id']


def send_notification_to_statuses(target_statuses: list, title: str, body: str) -> None:
    """Отправить FCM push-уведомление всем пользователям с указанными статусами.
    Собирает device_token из Firestore и отправляет каждому индивидуально.
    Ошибки FCM не блокируют создание уведомления.
    """
    from users.models import User

    # Собираем device_token всех подходящих пользователей
    tokens: set[str] = set()
    for st in target_statuses:
        for u in User.collection.filter('status', '==', st).fetch(1000):
            if u.device_token:
                tokens.add(u.device_token)

    if not tokens:
        return

    try:
        access_token = _get_access_token()
        project_id   = _get_project_id()
    except Exception:
        return

    url     = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type':  'application/json',
    }

    for device_token in tokens:
        payload = {
            'message': {
                'token': device_token,
                'notification': {
                    'title': title,
                    'body':  body,
                },
                'android': {
                    'priority': 'high',
                },
                'apns': {
                    'payload': {
                        'aps': {'sound': 'default'},
                    },
                },
            }
        }
        try:
            requests.post(url, json=payload, headers=headers, timeout=10)
        except Exception:
            pass
