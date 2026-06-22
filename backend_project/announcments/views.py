from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from utils.decorators import admin_required, jwt_required
from utils.drive import upload_announcement_image, delete_file
from utils.fcm import send_notification_to_statuses
from info.models import Notification
from .models import Announcement

_ALL_STATUSES = ['Guest', 'Student', 'Teacher', 'Admin']

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_SIZE = 2 * 1024 * 1024   # 2 МБ
MAX_IMAGES = 10


def _ann_dict(ann) -> dict:
    return {
        'id':          ann.id,
        'title_taj':   ann.title_taj or '',
        'title_rus':   ann.title_rus or '',
        'title_eng':   ann.title_eng or '',
        'title_kor':   ann.title_kor or '',
        'content_taj': ann.content_taj or '',
        'content_rus': ann.content_rus or '',
        'content_eng': ann.content_eng or '',
        'content_kor': ann.content_kor or '',
        'images':      ann.images or [],
        'time_posted': str(ann.time_posted) if ann.time_posted else '',
        'author':      ann.author or '',
    }


def _upload_images(files) -> tuple[list, Response | None]:
    """Загружает список файлов на Drive. Возвращает (images_list, error_response|None)."""
    uploaded = []
    for f in files:
        if f.content_type not in ALLOWED_IMAGE_TYPES:
            for item in uploaded:
                delete_file(item['file_id'])
            return [], Response(
                {'error': 'Допустимые форматы изображений: JPEG, PNG, WEBP'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if f.size > MAX_IMAGE_SIZE:
            for item in uploaded:
                delete_file(item['file_id'])
            return [], Response(
                {'error': 'Изображение слишком большое. Максимум 2 МБ'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ext = f.name.rsplit('.', 1)[-1] if '.' in f.name else 'jpg'
        try:
            file_id, url = upload_announcement_image(f, f'announcement_{len(uploaded)}.{ext}', f.content_type)
        except Exception as e:
            for item in uploaded:
                delete_file(item['file_id'])
            return [], Response(
                {'error': f'Ошибка загрузки изображения на Google Drive: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        uploaded.append({'file_id': file_id, 'url': url})
    return uploaded, None


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@admin_required
def admin_create_announcement(request):
    data = request.data

    if not data.get('title_rus', '').strip() and not data.get('title_taj', '').strip():
        return Response(
            {'error': 'Хотя бы одно поле заголовка обязательно (title_rus или title_taj)'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_files = request.FILES.getlist('images')
    if len(image_files) > MAX_IMAGES:
        return Response(
            {'error': f'Максимум {MAX_IMAGES} изображений'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    images, err = _upload_images(image_files)
    if err:
        return err

    ann = Announcement()
    for field in ('title_taj', 'title_rus', 'title_eng', 'title_kor',
                  'content_taj', 'content_rus', 'content_eng', 'content_kor'):
        setattr(ann, field, data.get(field, '').strip())
    ann.images = images
    ann.author = request.user_payload.get('username', '')
    ann.save()

    # Automatically create a Notification and push it to all users
    notif = Notification()
    for field in ('title_taj', 'title_rus', 'title_eng', 'title_kor',
                  'content_taj', 'content_rus', 'content_eng', 'content_kor'):
        setattr(notif, field, getattr(ann, field) or '')
    notif.image_url = images[0]['url'] if images else ''
    notif.images = images
    notif.target_statuses = _ALL_STATUSES
    notif.save()

    title = (ann.title_rus or ann.title_eng or ann.title_taj or ann.title_kor or 'Объявление')
    body  = (ann.content_rus or ann.content_eng or ann.content_taj or ann.content_kor or '')
    send_notification_to_statuses(_ALL_STATUSES, title, body)

    return Response(
        {'message': 'Объявление успешно создано', 'announcement': _ann_dict(ann)},
        status=status.HTTP_201_CREATED,
    )


@api_view(['PATCH'])
@admin_required
def admin_edit_announcement(request, ann_id):
    try:
        ann = Announcement.collection.get(f'announcements/{ann_id}')
    except Exception:
        ann = None
    if not ann:
        return Response({'error': 'Объявление не найдено'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    updated_fields = []

    for field in ('title_taj', 'title_rus', 'title_eng', 'title_kor',
                  'content_taj', 'content_rus', 'content_eng', 'content_kor'):
        if field in data:
            setattr(ann, field, data[field].strip())
            updated_fields.append(field)

    image_files = request.FILES.getlist('images')
    if image_files:
        if len(image_files) > MAX_IMAGES:
            return Response(
                {'error': f'Максимум {MAX_IMAGES} изображений'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Удаляем старые изображения
        for item in (ann.images or []):
            delete_file(item.get('file_id', ''))

        new_images, err = _upload_images(image_files)
        if err:
            return err
        ann.images = new_images
        updated_fields.append('images')

    if not updated_fields:
        return Response({'message': 'Нет данных для обновления'}, status=status.HTTP_400_BAD_REQUEST)

    ann.update()
    return Response({'message': 'Объявление обновлено', 'updated_fields': updated_fields, 'announcement': _ann_dict(ann)})


@api_view(['DELETE'])
@admin_required
def admin_delete_announcement(request, ann_id):
    try:
        ann = Announcement.collection.get(f'announcements/{ann_id}')
    except Exception:
        ann = None
    if not ann:
        return Response({'error': 'Объявление не найдено'}, status=status.HTTP_404_NOT_FOUND)

    for item in (ann.images or []):
        delete_file(item.get('file_id', ''))

    Announcement.collection.delete(f'announcements/{ann_id}')
    return Response({'message': 'Объявление удалено'})


# ---------------------------------------------------------------------------
# Public (authenticated) endpoints
# ---------------------------------------------------------------------------

@api_view(['GET'])
@jwt_required
def list_announcements(request):
    announcements = list(Announcement.collection.fetch(200))
    return Response({
        'total': len(announcements),
        'announcements': [_ann_dict(a) for a in announcements],
    })


@api_view(['GET'])
@jwt_required
def get_announcement(request, ann_id):
    try:
        ann = Announcement.collection.get(f'announcements/{ann_id}')
    except Exception:
        ann = None
    if not ann:
        return Response({'error': 'Объявление не найдено'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'announcement': _ann_dict(ann)})
