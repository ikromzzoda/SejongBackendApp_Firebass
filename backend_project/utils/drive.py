import io
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ['https://www.googleapis.com/auth/drive']


def _get_service():
    credentials = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_DRIVE_CREDENTIALS,
        scopes=SCOPES,
    )
    return build('drive', 'v3', credentials=credentials)


def upload_avatar(file_obj, filename: str, mime_type: str) -> tuple[str, str]:
    """Загрузить файл в папку аватаров на Google Drive.
    Возвращает (file_id, public_url).
    """
    service = _get_service()

    metadata = {
        'name': filename,
        'parents': [settings.GOOGLE_DRIVE_AVATAR_FOLDER_ID],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_obj.read()),
        mimetype=mime_type,
        resumable=False,
    )

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields='id',
    ).execute()

    file_id = uploaded['id']

    # Открыть публичный доступ
    service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'},
    ).execute()

    url = f'https://drive.google.com/uc?id={file_id}'
    return file_id, url


def delete_avatar(file_id: str) -> None:
    """Удалить файл с Google Drive по ID. Ошибки при удалении не критичны."""
    try:
        service = _get_service()
        service.files().delete(fileId=file_id).execute()
    except Exception:
        pass
