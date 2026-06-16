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
    """Send FCM push to all devices subscribed to the given status topics.
    Uses Firebase HTTP v1 API — no firebase-admin SDK required.
    Errors are silenced so a FCM failure never blocks notification creation.
    """
    try:
        token = _get_access_token()
        project_id = _get_project_id()
    except Exception:
        return

    url = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    for user_status in target_statuses:
        topic = f'status_{user_status}'   # status_Student, status_Teacher, etc.
        payload = {
            'message': {
                'topic': topic,
                'notification': {
                    'title': title,
                    'body': body,
                },
            }
        }
        try:
            requests.post(url, json=payload, headers=headers, timeout=10)
        except Exception:
            pass
