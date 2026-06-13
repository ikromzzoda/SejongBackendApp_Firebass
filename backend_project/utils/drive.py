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


def _get_or_create_folder(service, path: str) -> str:
    """Находит или создаёт цепочку папок по пути (например 'Sejong Cloud/book/files').
    Работает в Drive сервисного аккаунта. Возвращает ID финальной папки.
    """
    parts = [p for p in path.strip('/').split('/') if p]
    parent_id = 'root'

    for part in parts:
        query = (
            f"name='{part}' "
            f"and mimeType='application/vnd.google-apps.folder' "
            f"and '{parent_id}' in parents "
            f"and trashed=false"
        )
        results = service.files().list(q=query, fields='files(id)').execute()
        files = results.get('files', [])

        if files:
            parent_id = files[0]['id']
        else:
            folder = service.files().create(
                body={
                    'name': part,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id],
                },
                fields='id',
            ).execute()
            parent_id = folder['id']

    return parent_id


def _upload_to_path(file_obj, folder_path: str, filename: str, mime_type: str, resumable: bool = False) -> tuple[str, str]:
    """Загружает файл в папку по пути на Drive сервисного аккаунта.
    Возвращает (file_id, public_url).
    """
    service = _get_service()
    folder_id = _get_or_create_folder(service, folder_path)

    media = MediaIoBaseUpload(
        io.BytesIO(file_obj.read()),
        mimetype=mime_type,
        resumable=resumable,
    )

    uploaded = service.files().create(
        body={'name': filename, 'parents': [folder_id]},
        media_body=media,
        fields='id',
    ).execute()

    file_id = uploaded['id']

    service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'},
    ).execute()

    url = f'https://drive.google.com/uc?id={file_id}'
    return file_id, url


# ---------------------------------------------------------------------------
# Аватары
# ---------------------------------------------------------------------------

def upload_avatar(file_obj, filename: str, mime_type: str) -> tuple[str, str]:
    """Загрузить аватар на Google Drive. Возвращает (file_id, public_url)."""
    return _upload_to_path(file_obj, 'Sejong Cloud/users', filename, mime_type)


def delete_avatar(file_id: str) -> None:
    try:
        _get_service().files().delete(fileId=file_id).execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Книги
# ---------------------------------------------------------------------------

def upload_book_cover(file_obj, filename: str, mime_type: str) -> tuple[str, str]:
    """Загрузить обложку книги. Возвращает (file_id, public_url)."""
    return _upload_to_path(file_obj, 'Sejong Cloud/book/covers', filename, mime_type)


def upload_book_file(file_obj, filename: str, mime_type: str) -> tuple[str, str]:
    """Загрузить файл книги (PDF/EPUB). Возвращает (file_id, public_url)."""
    return _upload_to_path(file_obj, 'Sejong Cloud/book/files', filename, mime_type, resumable=True)


def delete_file(file_id: str) -> None:
    """Удалить любой файл с Google Drive по ID."""
    try:
        _get_service().files().delete(fileId=file_id).execute()
    except Exception:
        pass
