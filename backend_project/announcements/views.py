from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from utils.decorators import admin_required, jwt_required
from utils.drive import upload_announcement_image, delete_file
from utils.fcm import send_notification_to_statuses
from utils.schema import AUTH_HEADER_PARAM, ADMIN_RESPONSES, UNAUTHORIZED_RESPONSES, ErrorResponseSerializer, MessageResponseSerializer
from audit_logs.utils import log_action
from info.models import Notification
from users.validators import _normalize_email, _validate_email
from .models import Announcement, ContactMessage
from .serializers import (
    AdminCreateAnnouncementRequestSerializer,
    AdminCreateAnnouncementResponseSerializer,
    AdminEditAnnouncementRequestSerializer,
    AdminEditAnnouncementResponseSerializer,
    ListAnnouncementsResponseSerializer,
    GetAnnouncementResponseSerializer,
    ContactAdminRequestSerializer,
    ListContactMessagesResponseSerializer,
    ContactMessageSerializer,
)

_ALL_STATUSES = ['Guest', 'Student', 'Teacher', 'Admin']

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_SIZE = 2 * 1024 * 1024   # 2 МБ
MAX_IMAGES = 10
_CACHE_TTL = 60  # seconds

MAX_CONTACT_MESSAGE_LEN = 2000
UNREAD_COUNT_FETCH_LIMIT = 500     # лимит выборки при подсчёте непрочитанных обращений
CONTACT_RATE_LIMIT_SECONDS = 60    # не чаще одного обращения в минуту с одного IP


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


def _get_announcement_or_404(ann_id):
    """Returns (ann, None) or (None, error_response)."""
    try:
        ann = Announcement.collection.get(f'announcements/{ann_id}')
    except Exception:
        ann = None
    if not ann:
        return None, Response({'error': 'Объявление не найдено'}, status=status.HTTP_404_NOT_FOUND)
    return ann, None


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


def _create_notification(ann, images: list) -> None:
    notif = Notification()
    for field in ('title_taj', 'title_rus', 'title_eng', 'title_kor',
                  'content_taj', 'content_rus', 'content_eng', 'content_kor'):
        setattr(notif, field, getattr(ann, field) or '')
    notif.image_url = images[0]['url'] if images else ''
    notif.images = images
    notif.target_statuses = _ALL_STATUSES
    notif.save()


def _invalidate_cache() -> None:
    version = cache.get('announcements_v', 0)
    cache.set('announcements_v', version + 1, None)


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Announcements'],
    summary='Создать объявление (admin)',
    description='Создаёт объявление, дублирует его как уведомление и отправляет push-уведомление всем пользователям.',
    parameters=[AUTH_HEADER_PARAM],
    request={'multipart/form-data': AdminCreateAnnouncementRequestSerializer},
    responses={
        201: AdminCreateAnnouncementResponseSerializer,
        400: ErrorResponseSerializer,
        502: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
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

    try:
        ann.save()
    except Exception as e:
        for item in images:
            delete_file(item['file_id'])
        return Response(
            {'error': f'Ошибка сохранения объявления: {e}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    log_action(request, 'create', 'Announcement', ann.id, {
        'title_rus': ann.title_rus or '',
        'title_taj': ann.title_taj or '',
    })
    _create_notification(ann, images)

    title = ann.title_rus or ann.title_eng or ann.title_taj or ann.title_kor or 'Объявление'
    body  = ann.content_rus or ann.content_eng or ann.content_taj or ann.content_kor or ''
    send_notification_to_statuses(_ALL_STATUSES, title, body)
    _invalidate_cache()

    return Response(
        {'message': 'Объявление успешно создано', 'announcement': _ann_dict(ann)},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=['Announcements'],
    summary='Редактировать объявление (admin)',
    description='Передача "images" заменяет все текущие изображения (старые удаляются после успешной загрузки новых).',
    parameters=[AUTH_HEADER_PARAM],
    request={'multipart/form-data': AdminEditAnnouncementRequestSerializer},
    responses={
        200: AdminEditAnnouncementResponseSerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        502: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['PATCH'])
@admin_required
def admin_edit_announcement(request, ann_id):
    ann, err = _get_announcement_or_404(ann_id)
    if err:
        return err

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
        new_images, err = _upload_images(image_files)
        if err:
            return err

        # Delete old images only after new ones are successfully uploaded
        for item in (ann.images or []):
            delete_file(item.get('file_id', ''))

        ann.images = new_images
        updated_fields.append('images')

    if not updated_fields:
        return Response({'message': 'Нет данных для обновления'}, status=status.HTTP_400_BAD_REQUEST)

    ann.update()
    log_action(request, 'update', 'Announcement', ann_id, {'updated_fields': updated_fields})
    _invalidate_cache()
    return Response({'message': 'Объявление обновлено', 'updated_fields': updated_fields, 'announcement': _ann_dict(ann)})


@extend_schema(
    tags=['Announcements'],
    summary='Удалить объявление (admin)',
    parameters=[AUTH_HEADER_PARAM],
    responses={200: MessageResponseSerializer, 404: ErrorResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['DELETE'])
@admin_required
def admin_delete_announcement(request, ann_id):
    ann, err = _get_announcement_or_404(ann_id)
    if err:
        return err

    for item in (ann.images or []):
        delete_file(item.get('file_id', ''))

    Announcement.collection.delete(f'announcements/{ann_id}')
    log_action(request, 'delete', 'Announcement', ann_id)
    _invalidate_cache()
    return Response({'message': 'Объявление удалено'})


# ---------------------------------------------------------------------------
# Public (authenticated) endpoints
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Announcements'],
    operation_id='announcements_list',
    summary='Список объявлений',
    description='Список объявлений с пагинацией. Результат кэшируется на 60 секунд.',
    parameters=[
        AUTH_HEADER_PARAM,
        OpenApiParameter('limit', OpenApiTypes.INT, description='Максимум записей (по умолчанию 20, максимум 100)'),
    ],
    responses={200: ListAnnouncementsResponseSerializer, **UNAUTHORIZED_RESPONSES},
)
@api_view(['GET'])
@jwt_required
def list_announcements(request):
    try:
        limit = min(int(request.query_params.get('limit', 20)), 100)
    except (ValueError, TypeError):
        limit = 20

    version = cache.get('announcements_v', 0)
    cache_key = f'announcements_{version}_{limit}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    raw = list(Announcement.collection.fetch(limit + 1))
    has_more = len(raw) > limit
    items = [_ann_dict(a) for a in raw[:limit]]

    result = {'total': len(items), 'has_more': has_more, 'announcements': items}
    cache.set(cache_key, result, _CACHE_TTL)
    return Response(result)


@extend_schema(
    tags=['Announcements'],
    summary='Получить объявление',
    parameters=[AUTH_HEADER_PARAM],
    responses={200: GetAnnouncementResponseSerializer, 404: ErrorResponseSerializer, **UNAUTHORIZED_RESPONSES},
)
@api_view(['GET'])
@jwt_required
def get_announcement(request, ann_id):
    ann, err = _get_announcement_or_404(ann_id)
    if err:
        return err
    return Response({'announcement': _ann_dict(ann)})


# ---------------------------------------------------------------------------
# Связаться с админом
# ---------------------------------------------------------------------------

def _contact_dict(msg) -> dict:
    return {
        'id':           msg.id,
        'name':         msg.name or '',
        'email':        msg.email or '',
        'phone_number': msg.phone_number or '',
        'message':      msg.message or '',
        'is_read':      bool(msg.is_read),
        'created_at':   str(msg.created_at) if msg.created_at else '',
    }


def count_unread_contact_messages() -> int:
    """Количество непрочитанных обращений к админу (используется и при логине админа)."""
    try:
        return len(list(
            ContactMessage.collection.filter('is_read', '==', False).fetch(UNREAD_COUNT_FETCH_LIMIT)
        ))
    except Exception:
        return 0


def _get_contact_message_or_404(msg_id):
    try:
        msg = ContactMessage.collection.get(f'contact_messages/{msg_id}')
    except Exception:
        msg = None
    if not msg:
        return None, Response({'error': 'Обращение не найдено'}, status=status.HTTP_404_NOT_FOUND)
    return msg, None


@extend_schema(
    tags=['Announcements'],
    summary='Связаться с админом (без авторизации)',
    description=(
        'Отправляет сообщение администратору. Доступно без авторизации — в том числе '
        'пользователям, которые не могут зарегистрироваться, войти или получить код на почту. '
        'Админы получают push-уведомление о новом обращении. '
        f'Не чаще одного обращения в {CONTACT_RATE_LIMIT_SECONDS} секунд с одного IP.'
    ),
    request=ContactAdminRequestSerializer,
    responses={
        201: MessageResponseSerializer,
        400: ErrorResponseSerializer,
        429: ErrorResponseSerializer,
        502: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def contact_admin(request):
    data    = request.data
    email   = _normalize_email(data.get('email'))
    message = (data.get('message') or '').strip()
    name    = (data.get('name') or '').strip()
    phone   = (data.get('phone_number') or '').strip()

    if not email or not message:
        return Response(
            {'error': 'Поля "email" и "message" обязательны'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    err = _validate_email(email)
    if err:
        return err

    if len(message) > MAX_CONTACT_MESSAGE_LEN:
        return Response(
            {'error': f'Сообщение слишком длинное. Максимум {MAX_CONTACT_MESSAGE_LEN} символов'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Rate limit по IP: эндпоинт открытый, защищаемся от спама
    ip = (request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
          or request.META.get('REMOTE_ADDR', ''))
    rate_key = f'contact_admin_{ip}'
    if cache.get(rate_key):
        return Response(
            {'error': 'Слишком часто. Подождите минуту и попробуйте снова.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    msg = ContactMessage()
    msg.name         = name
    msg.email        = email
    msg.phone_number = phone
    msg.message      = message
    msg.is_read      = False
    try:
        msg.save()
    except Exception as e:
        return Response(
            {'error': f'Ошибка сохранения обращения: {e}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    cache.set(rate_key, 1, CONTACT_RATE_LIMIT_SECONDS)

    sender  = name or email
    preview = message if len(message) <= 100 else message[:100] + '…'
    send_notification_to_statuses(['Admin'], 'Новое обращение к администратору', f'{sender}: {preview}')

    return Response(
        {'message': 'Сообщение отправлено администратору. Мы свяжемся с вами по указанной почте.'},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=['Announcements'],
    summary='Обращения пользователей (admin)',
    description='Список обращений «связаться с админом», новые сверху. Также возвращает число непрочитанных.',
    parameters=[
        AUTH_HEADER_PARAM,
        OpenApiParameter('limit', OpenApiTypes.INT, description='Максимум записей (по умолчанию 20, максимум 100)'),
    ],
    responses={200: ListContactMessagesResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['GET'])
@admin_required
def admin_list_contact_messages(request):
    try:
        limit = min(int(request.query_params.get('limit', 20)), 100)
    except (ValueError, TypeError):
        limit = 20

    raw = list(ContactMessage.collection.order('-created_at').fetch(limit + 1))
    has_more = len(raw) > limit
    items = [_contact_dict(m) for m in raw[:limit]]

    return Response({
        'total':        len(items),
        'unread_count': count_unread_contact_messages(),
        'has_more':     has_more,
        'messages':     items,
    })


@extend_schema(
    tags=['Announcements'],
    summary='Отметить обращение прочитанным (admin)',
    parameters=[AUTH_HEADER_PARAM],
    responses={200: MessageResponseSerializer, 404: ErrorResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['PATCH'])
@admin_required
def admin_mark_contact_message_read(request, msg_id):
    msg, err = _get_contact_message_or_404(msg_id)
    if err:
        return err

    if not msg.is_read:
        msg.is_read = True
        msg.update()

    return Response({'message': 'Обращение отмечено прочитанным'})


@extend_schema(
    tags=['Announcements'],
    summary='Удалить обращение (admin)',
    parameters=[AUTH_HEADER_PARAM],
    responses={200: MessageResponseSerializer, 404: ErrorResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['DELETE'])
@admin_required
def admin_delete_contact_message(request, msg_id):
    msg, err = _get_contact_message_or_404(msg_id)
    if err:
        return err

    ContactMessage.collection.delete(f'contact_messages/{msg_id}')
    log_action(request, 'delete', 'ContactMessage', msg_id)
    return Response({'message': 'Обращение удалено'})
