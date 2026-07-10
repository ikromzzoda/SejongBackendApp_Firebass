import re
import threading
from datetime import datetime, timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from utils.decorators import jwt_required
from utils.fcm import send_chat_message_push
from utils.schema import AUTH_HEADER_PARAM, UNAUTHORIZED_RESPONSES, ErrorResponseSerializer, MessageResponseSerializer
from audit_logs.utils import log_action
from users.models import User
from groups.models import Group
from .models import ChatMessage, ChatReadStatus
from .firebase_tokens import create_custom_token, TOKEN_LIFETIME_SECONDS
from .serializers import (
    SendMessageRequestSerializer,
    SendMessageResponseSerializer,
    ListMessagesResponseSerializer,
    FirebaseTokenResponseSerializer,
    MarkReadResponseSerializer,
    ReadStatusResponseSerializer,
    SeenByResponseSerializer,
)

MAX_TEXT_LENGTH = 2000

# Сколько ждать перед пушем: если за это время получатель отметил чат
# прочитанным (сидел в нём с открытым листенером), пуш ему не отправляется
READ_GRACE_SECONDS = 30


def _message_dict(msg) -> dict:
    return {
        'id':            msg.id,
        'sender_id':     msg.sender_id or '',
        'sender_name':   msg.sender_name or '',
        'sender_avatar': msg.sender_avatar or '',
        'text':          msg.text or '',
        'created_at':    str(msg.created_at) if msg.created_at else '',
    }


def _get_chat_user(request):
    """
    Возвращает (user, group_id, None) или (None, None, error_response).

    Группа берётся из документа пользователя, а не из JWT — членство
    проверяется актуальное, даже если админ только что перевёл студента.
    """
    user_id = request.user_payload.get('user_id', '')
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return None, None, Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
    if not user.group:
        return None, None, Response(
            {'error': 'Вы не состоите ни в одной группе'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return user, user.group, None


# ---------------------------------------------------------------------------
# Firebase custom token — «пропуск» для realtime-чтения чата из Firestore
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Chat'],
    summary='Firebase custom token для подписки на чат',
    description=(
        'Выдаёт custom token Firebase Auth с claim `group_id` текущей группы. '
        'Клиент вызывает `signInWithCustomToken(token)` и вешает snapshot-листенер '
        'на `groups/{group_id}/chat_messages` — новые сообщения приходят в реальном '
        'времени без запросов к бэкенду. Токен одноразовый для входа (живёт 1 час), '
        'сессию Firebase SDK продлевает сам; запрашивайте новый токен при каждом '
        'запуске приложения, чтобы подхватить смену группы.'
    ),
    parameters=[AUTH_HEADER_PARAM],
    responses={
        200: FirebaseTokenResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        502: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['GET'])
@jwt_required
def firebase_token(request):
    user, group_id, err = _get_chat_user(request)
    if err:
        return err

    try:
        token = create_custom_token(user.id, {'group_id': group_id})
    except Exception as e:
        return Response(
            {'error': f'Ошибка выпуска Firebase-токена: {e}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({
        'firebase_token': token,
        'uid':            user.id,
        'group_id':       group_id,
        'expires_in':     TOKEN_LIFETIME_SECONDS,
    })


# ---------------------------------------------------------------------------
# Сообщения
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['POST'],
    tags=['Chat'],
    summary='Отправить сообщение в чат своей группы',
    description='Сообщение сохраняется в Firestore, подписанные листенеры группы получают его мгновенно.',
    parameters=[AUTH_HEADER_PARAM],
    request=SendMessageRequestSerializer,
    responses={
        201: SendMessageResponseSerializer,
        400: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        502: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@extend_schema(
    methods=['GET'],
    tags=['Chat'],
    summary='История сообщений своей группы',
    description=(
        'Сообщения отсортированы от новых к старым. Для подгрузки истории '
        'передайте в `before` значение `created_at` самого старого из уже '
        'загруженных сообщений.'
    ),
    parameters=[
        AUTH_HEADER_PARAM,
        OpenApiParameter('limit', OpenApiTypes.INT, description='Максимум записей (по умолчанию 50, максимум 100)'),
        OpenApiParameter('before', OpenApiTypes.STR, description='ISO-дата: вернуть сообщения строго старше неё'),
    ],
    responses={
        200: ListMessagesResponseSerializer,
        400: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['GET', 'POST'])
@jwt_required
def messages(request):
    user, group_id, err = _get_chat_user(request)
    if err:
        return err

    if request.method == 'POST':
        return _send_message(request, user, group_id)
    return _list_messages(request, group_id)


def _send_message(request, user, group_id):
    text = (request.data.get('text') or '').strip()
    if not text:
        return Response({'error': 'Поле "text" обязательно'}, status=status.HTTP_400_BAD_REQUEST)
    if len(text) > MAX_TEXT_LENGTH:
        return Response(
            {'error': f'Сообщение слишком длинное. Максимум {MAX_TEXT_LENGTH} символов'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    msg = ChatMessage(parent=f'groups/{group_id}')
    msg.sender_id = user.id
    msg.sender_name = user.fullname or user.username
    msg.sender_avatar = user.avatar or ''
    msg.text = text
    msg.created_at = datetime.now(timezone.utc)
    try:
        msg.save()
    except Exception as e:
        return Response(
            {'error': f'Ошибка сохранения сообщения: {e}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    timer = threading.Timer(
        READ_GRACE_SECONDS,
        _push_unread_members,
        args=(group_id, msg.id, msg.created_at, user.id, msg.sender_name, text),
    )
    timer.daemon = True
    timer.start()

    return Response(
        {'message': 'Сообщение отправлено', 'chat_message': _message_dict(msg)},
        status=status.HTTP_201_CREATED,
    )


def _push_unread_members(group_id, message_id, created_at, sender_id, sender_name, text):
    """
    Вызывается через READ_GRACE_SECONDS после отправки: шлёт push только тем
    членам группы, кто к этому моменту так и не прочитал сообщение.
    Best-effort: отложенный пуш живёт в памяти воркера и теряется при рестарте.
    """
    try:
        # Сообщение могли удалить за время ожидания
        if not ChatMessage.collection.get(f'groups/{group_id}/chat_messages/{message_id}'):
            return

        read_at = {
            s.id: s.last_read_at
            for s in ChatReadStatus.collection.parent(f'groups/{group_id}').fetch(500)
        }
        tokens = []
        for member in User.collection.filter('group', '==', group_id).fetch(500):
            if member.id == sender_id or not member.device_token:
                continue
            last = read_at.get(member.id)
            if last and last >= created_at:
                continue
            tokens.append(member.device_token)
        if not tokens:
            return

        try:
            group = Group.collection.get(f'groups/{group_id}')
        except Exception:
            group = None
        title = group.name if group and group.name else 'Чат группы'
        body = f'{sender_name}: {text}'
        if len(body) > 150:
            body = body[:150] + '…'
        send_chat_message_push(tokens, title, body, group_id)
    except Exception:
        pass


def _parse_before(raw: str):
    """
    ISO 8601 → datetime. Если '+' смещения потерялся при URL-декодировании
    ('... 00:00' вместо '...+00:00'), восстанавливает его.
    """
    for candidate in (raw.replace('Z', '+00:00'), re.sub(r' (\d{2}:\d{2})$', r'+\1', raw)):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def _list_messages(request, group_id):
    try:
        limit = min(int(request.query_params.get('limit', 50)), 100)
    except (ValueError, TypeError):
        limit = 50

    query = ChatMessage.collection.parent(f'groups/{group_id}')

    before_raw = request.query_params.get('before', '')
    if before_raw:
        before_dt = _parse_before(before_raw)
        if before_dt is None:
            return Response(
                {'error': 'Параметр "before" должен быть датой в формате ISO 8601'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        query = query.filter('created_at', '<', before_dt)

    raw = list(query.order('-created_at').fetch(limit + 1))
    has_more = len(raw) > limit
    items = [_message_dict(m) for m in raw[:limit]]
    return Response({'total': len(items), 'has_more': has_more, 'messages': items})


# ---------------------------------------------------------------------------
# Прочитанность («кто посмотрел», как в Telegram)
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Chat'],
    summary='Отметить чат прочитанным',
    description=(
        'Ставит указатель чтения текущего пользователя на текущий момент. '
        'Клиент вызывает это, когда пользователь видит сообщения (чат открыт '
        'и новые сообщения показаны). Все сообщения с `created_at` не позже '
        'указателя считаются просмотренными этим пользователем. Пока указатель '
        'старше сообщения, через ~30 секунд после отправки пользователю уйдёт push.'
    ),
    parameters=[AUTH_HEADER_PARAM],
    responses={
        200: MarkReadResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        502: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['POST'])
@jwt_required
def mark_read(request):
    user, group_id, err = _get_chat_user(request)
    if err:
        return err

    now = datetime.now(timezone.utc)
    rs = ChatReadStatus(parent=f'groups/{group_id}')
    rs.id = user.id
    rs.user_name = user.fullname or user.username
    rs.user_avatar = user.avatar or ''
    rs.last_read_at = now
    try:
        rs.save()
    except Exception as e:
        return Response(
            {'error': f'Ошибка сохранения отметки чтения: {e}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({'message': 'Чат отмечен прочитанным', 'last_read_at': str(now)})


def _read_statuses(group_id) -> list:
    return list(ChatReadStatus.collection.parent(f'groups/{group_id}').fetch(500))


def _read_status_dict(rs) -> dict:
    return {
        'user_id':      rs.id,
        'user_name':    rs.user_name or '',
        'user_avatar':  rs.user_avatar or '',
        'last_read_at': str(rs.last_read_at) if rs.last_read_at else '',
    }


@extend_schema(
    tags=['Chat'],
    summary='Указатели чтения своей группы',
    description=(
        'Кто до какого момента дочитал чат. Сообщение просмотрено пользователем, '
        'если его `created_at` <= `last_read_at` пользователя. Для realtime-галочек '
        'клиенту удобнее слушать `groups/{group_id}/chat_read_status` напрямую '
        'из Firestore — этот эндпоинт REST-фолбэк.'
    ),
    parameters=[AUTH_HEADER_PARAM],
    responses={
        200: ReadStatusResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['GET'])
@jwt_required
def read_status(request):
    _, group_id, err = _get_chat_user(request)
    if err:
        return err

    statuses = _read_statuses(group_id)
    return Response({
        'total': len(statuses),
        'read_status': [_read_status_dict(s) for s in statuses],
    })


@extend_schema(
    tags=['Chat'],
    summary='Кто посмотрел сообщение',
    description='Список членов группы, чей указатель чтения не старше `created_at` сообщения (автор не включается).',
    parameters=[AUTH_HEADER_PARAM],
    responses={
        200: SeenByResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['GET'])
@jwt_required
def message_seen(request, message_id):
    _, group_id, err = _get_chat_user(request)
    if err:
        return err

    try:
        msg = ChatMessage.collection.get(f'groups/{group_id}/chat_messages/{message_id}')
    except Exception:
        msg = None
    if not msg:
        return Response({'error': 'Сообщение не найдено'}, status=status.HTTP_404_NOT_FOUND)

    viewers = [
        s for s in _read_statuses(group_id)
        if s.id != msg.sender_id and s.last_read_at and msg.created_at and s.last_read_at >= msg.created_at
    ]
    return Response({
        'total': len(viewers),
        'seen_by': [_read_status_dict(s) for s in viewers],
    })


@extend_schema(
    tags=['Chat'],
    summary='Удалить сообщение',
    description=(
        'Автор может удалить своё сообщение, админ — любое. '
        'Админ может указать `group_id` в query, чтобы модерировать чужую группу '
        '(по умолчанию используется его собственная группа).'
    ),
    parameters=[
        AUTH_HEADER_PARAM,
        OpenApiParameter('group_id', OpenApiTypes.STR, description='Только для админа: группа, в которой лежит сообщение'),
    ],
    responses={
        200: MessageResponseSerializer,
        400: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['DELETE'])
@jwt_required
def delete_message(request, message_id):
    is_admin = request.user_payload.get('status') == 'Admin'

    _, group_id, err = _get_chat_user(request)
    if err and not is_admin:
        return err
    if err:
        group_id = ''

    if is_admin and request.query_params.get('group_id'):
        group_id = request.query_params['group_id']
    if not group_id:
        return Response({'error': 'Укажите параметр "group_id"'}, status=status.HTTP_400_BAD_REQUEST)

    key = f'groups/{group_id}/chat_messages/{message_id}'
    try:
        msg = ChatMessage.collection.get(key)
    except Exception:
        msg = None
    if not msg:
        return Response({'error': 'Сообщение не найдено'}, status=status.HTTP_404_NOT_FOUND)

    if not is_admin and msg.sender_id != request.user_payload.get('user_id'):
        return Response({'error': 'Можно удалять только свои сообщения'}, status=status.HTTP_403_FORBIDDEN)

    ChatMessage.collection.delete(key)
    log_action(request, 'delete', 'ChatMessage', message_id, {'group_id': group_id})
    return Response({'message': 'Сообщение удалено'})
