import re
import secrets
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes

from .models import User, BlacklistedToken, DEFAULT_AVATAR
from groups.models import Group
from utils.jwt_utils import (
    generate_token,
    generate_refresh_token,
    generate_reset_token,
    decode_token,
    RESET_TOKEN_LIFETIME_MINUTES,
)
from utils.decorators import admin_required, jwt_required
from utils.drive import upload_avatar, delete_avatar
from utils.schema import (
    AUTH_HEADER_PARAM,
    ADMIN_RESPONSES,
    UNAUTHORIZED_RESPONSES,
    ErrorResponseSerializer,
    MessageResponseSerializer,
)
from audit_logs.utils import log_action
from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    ProfileSerializer,
    RegisterRequestSerializer,
    RegisterResponseSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    TokenRefreshRequestSerializer,
    TokenRefreshResponseSerializer,
    AdminListUsersResponseSerializer,
    AdminGetUserResponseSerializer,
    AdminEditUserRequestSerializer,
    AdminEditUserResponseSerializer,
    AdminVerifyUserRequestSerializer,
    AdminVerifyUserResponseSerializer,
    AdminSetStatusRequestSerializer,
    AdminSetStatusResponseSerializer,
    AdminCreateUserRequestSerializer,
    AdminCreateUserResponseSerializer,
    UpdateProfileRequestSerializer,
    UpdateProfileResponseSerializer,
    ChangeAvatarRequestSerializer,
    ChangeAvatarResponseSerializer,
    BulkImportRequestSerializer,
    VerifyEmailRequestSerializer,
    ResendEmailCodeRequestSerializer,
    ForgotPasswordRequestSerializer,
    VerifyResetCodeRequestSerializer,
    VerifyResetCodeResponseSerializer,
    ResetPasswordRequestSerializer,
)
from .validators import (
    ALLOWED_IMAGE_TYPES,
    MAX_AVATAR_SIZE,
    VALID_STATUSES,
    _require_fields,
    _validate_phone,
    _validate_email,
    _username_taken,
    _email_taken,
    _normalize_email,
)
from .services import (
    EMAIL_CODE_LIFETIME_MINUTES,
    EMAIL_CODE_MAX_ATTEMPTS,
    EMAIL_CODE_RESEND_SECONDS,
    RESEND_CODE_MESSAGE,
    RESET_CODE_LIFETIME_MINUTES,
    RESET_CODE_MAX_ATTEMPTS,
    RESET_CODE_RESEND_SECONDS,
    FORGOT_PASSWORD_MESSAGE,
    _clear_email_code,
    _send_email_verification_code,
    _clear_reset_code,
    _generate_username,
    _generate_password,
)
from .selectors import _user_dict
from .excel import (
    _detect_columns,
    _open_import_workbook,
    _build_import_results_xlsx,
    _build_import_template_xlsx,
    _xlsx_response,
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Users'],
    summary='Регистрация',
    description=(
        'Регистрация нового пользователя. На указанный email отправляется 6-значный код '
        f'подтверждения (действует {EMAIL_CODE_LIFETIME_MINUTES} минут). До подтверждения '
        'email вход в систему невозможен. Статус по умолчанию — "Guest", ожидает '
        'подтверждения администратора.'
    ),
    request={'multipart/form-data': RegisterRequestSerializer},
    responses={
        201: RegisterResponseSerializer,
        400: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def register(request):
    data = request.data

    err = _require_fields(data, 'username', 'password', 'email', 'phone_number')
    if err:
        return err

    err = _validate_phone(data['phone_number'])
    if err:
        return err

    if _username_taken(data['username']):
        return Response(
            {'error': 'Пользователь с таким username уже существует'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if _email_taken(data['email']):
        return Response(
            {'error': 'Пользователь с такой почтой уже существует. Укажите другой email.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    avatar_file = request.FILES.get('avatar')
    if avatar_file:
        if avatar_file.content_type not in ALLOWED_IMAGE_TYPES:
            return Response(
                {'error': 'Недопустимый формат аватара. Разрешены: JPEG, PNG, WEBP'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if avatar_file.size > MAX_AVATAR_SIZE:
            return Response(
                {'error': 'Файл аватара слишком большой. Максимум 3 МБ'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    user = User()
    user.username      = data['username']
    user.fullname      = data.get('fullname', '')
    user.email         = _normalize_email(data['email'])
    user.phone_number  = data['phone_number']
    user.password      = make_password(data['password'])
    user.date_of_birth = data.get('date_of_birth', '')
    user.status              = 'Guest'
    user.verification_status = 'Pending'
    user.email_verified       = False
    _send_email_verification_code(user, datetime.now(timezone.utc))
    user.save()

    if avatar_file:
        ext      = avatar_file.name.rsplit('.', 1)[-1] if '.' in avatar_file.name else 'jpg'
        filename = f"avatar_{user.id}.{ext}"
        try:
            new_file_id, new_url = upload_avatar(avatar_file, filename, avatar_file.content_type)
            user.avatar    = new_url
            user.avatar_id = new_file_id
            user.update()
        except Exception:
            pass

    return Response({
        'message': 'Регистрация успешна. Мы отправили 6-значный код на вашу почту — подтвердите email, чтобы войти.',
        'email': user.email,
        'status': user.status,
        'verification_status': user.verification_status,
        'avatar': user.avatar or '',
        'fcm_topic': f'status_{user.status}',
    }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Users'],
    summary='Регистрация — подтвердить email',
    description=(
        'Проверяет 6-значный код из письма, отправленного при регистрации или при смене '
        'почты в профиле. При верном коде email считается подтверждённым; если шла смена '
        'почты, новая почта (передайте её в поле "email") записывается в профиль. После '
        f'{EMAIL_CODE_MAX_ATTEMPTS} неверных попыток код аннулируется — нужно запросить новый '
        'через resend-code.'
    ),
    request=VerifyEmailRequestSerializer,
    responses={
        200: MessageResponseSerializer,
        400: ErrorResponseSerializer,
        429: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def verify_email(request):
    email = _normalize_email(request.data.get('email'))
    code  = (request.data.get('code') or '').strip()
    if not email or not code:
        return Response({'error': 'Поля "email" и "code" обязательны'}, status=status.HTTP_400_BAD_REQUEST)

    users = list(User.collection.filter('email', '==', email).fetch(1))
    user  = users[0] if users else None

    # Смена почты через профиль: новая почта до подтверждения лежит в pending_email
    is_pending_change = False
    if not user:
        users = list(User.collection.filter('pending_email', '==', email).fetch(1))
        user  = users[0] if users else None
        is_pending_change = user is not None

    if user and user.email_verified and not is_pending_change:
        return Response({'message': 'Email уже подтверждён. Можете войти.'})

    if not user or not user.email_code_hash:
        return Response(
            {'error': 'Код неверен или истёк. Запросите новый код.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = datetime.now(timezone.utc)
    if not user.email_code_expires or now > user.email_code_expires:
        _clear_email_code(user)
        user.update()
        return Response(
            {'error': 'Код истёк. Запросите новый код.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not check_password(code, user.email_code_hash):
        attempts = (user.email_code_attempts or 0) + 1
        if attempts >= EMAIL_CODE_MAX_ATTEMPTS:
            _clear_email_code(user)
            user.update()
            return Response(
                {'error': 'Слишком много неверных попыток. Запросите новый код.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        user.email_code_attempts = attempts
        user.update()
        return Response(
            {'error': f'Неверный код. Осталось попыток: {EMAIL_CODE_MAX_ATTEMPTS - attempts}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Код верный: подтверждаем email и аннулируем код
    if is_pending_change:
        # Пока пользователь подтверждал почту, её мог занять кто-то другой
        if _email_taken(email):
            user.pending_email = ''
            _clear_email_code(user)
            user.update()
            return Response(
                {'error': 'Эта почта уже занята другим пользователем. Укажите другой email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.email         = email
        user.pending_email = ''
    user.email_verified = True
    _clear_email_code(user)
    user.update()

    if is_pending_change:
        return Response({'message': 'Почта подтверждена и обновлена в профиле.'})
    return Response({'message': 'Email подтверждён. Теперь вы можете войти.'})


@extend_schema(
    tags=['Users'],
    summary='Регистрация — отправить код повторно',
    description=(
        'Повторно отправляет 6-значный код подтверждения email. Повторная отправка — не чаще '
        f'раза в {EMAIL_CODE_RESEND_SECONDS // 60} минут. Ответ одинаковый независимо от того, '
        'существует ли email (защита от перебора).'
    ),
    request=ResendEmailCodeRequestSerializer,
    responses={
        200: MessageResponseSerializer,
        400: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def resend_email_code(request):
    email = _normalize_email(request.data.get('email'))
    if not email:
        return Response({'error': 'Поле "email" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    users = list(User.collection.filter('email', '==', email).fetch(1))
    user  = users[0] if users else None

    # Смена почты через профиль: новая почта до подтверждения лежит в pending_email
    is_pending_change = False
    if not user:
        users = list(User.collection.filter('pending_email', '==', email).fetch(1))
        user  = users[0] if users else None
        is_pending_change = user is not None

    if not user or (user.email_verified and not is_pending_change):
        return Response({'message': RESEND_CODE_MESSAGE})

    now = datetime.now(timezone.utc)

    # Rate limit: не отправляем новый код, если предыдущий ушёл недавно
    if user.email_code_sent_at and (now - user.email_code_sent_at).total_seconds() < EMAIL_CODE_RESEND_SECONDS:
        return Response({'message': RESEND_CODE_MESSAGE})

    _send_email_verification_code(user, now)
    user.update()

    return Response({'message': RESEND_CODE_MESSAGE})


@extend_schema(
    tags=['Users'],
    summary='Вход',
    description='Вход по username и паролю. Возвращает access и refresh токены.',
    request=LoginRequestSerializer,
    responses={
        200: LoginResponseSerializer,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def login(request):
    data     = request.data
    username = data.get('username', '').strip()
    password = data.get('password', '')

    device_token = data.get('device_token', '').strip()

    if not username or not password or not device_token:
        return Response(
            {'error': 'Введите username, пароль и device_token'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    users = list(User.collection.filter('username', '==', username).fetch(1))
    if not users or not check_password(password, users[0].password):
        return Response(
            {'error': 'Неверный username или пароль'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user = users[0]

    # email_verified is False — только у новых пользователей, не подтвердивших код;
    # у старых записей поле отсутствует (None) — их не блокируем
    if user.email_verified is False:
        return Response(
            {'error': 'Email не подтверждён. Введите код из письма или запросите новый.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if device_token != (user.device_token or ''):
        user.device_token = device_token

    access_token = generate_token(
        user_id=user.id,
        username=user.username,
        status=user.status,
        verification_status=user.verification_status,
    )
    refresh_token, refresh_jti = generate_refresh_token(user.id)
    user.refresh_token_jti = refresh_jti
    user.update()

    return Response({
        'message':       'Вход выполнен',
        'token':         access_token,
        'refresh_token': refresh_token,
        'status':        user.status,
        'verification_status': user.verification_status,
    })


@extend_schema(
    tags=['Users'],
    summary='Выход',
    description='Отзывает текущий access-токен (добавляет его jti в чёрный список) и очищает refresh-токен пользователя.',
    parameters=[AUTH_HEADER_PARAM],
    request=None,
    responses={
        200: MessageResponseSerializer,
        401: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def logout(request):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response({'error': 'Токен не предоставлен'}, status=status.HTTP_401_UNAUTHORIZED)

    token = auth_header.split(' ', 1)[1]
    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        return Response({'error': 'Токен уже истёк'}, status=status.HTTP_401_UNAUTHORIZED)
    except pyjwt.InvalidTokenError:
        return Response({'error': 'Недействительный токен'}, status=status.HTTP_401_UNAUTHORIZED)

    bt = BlacklistedToken()
    bt.id = payload['jti']
    bt.save()

    try:
        user = User.collection.get(f"users/{payload['user_id']}")
        if user:
            user.refresh_token_jti = ''
            user.update()
    except Exception:
        pass

    return Response({'message': 'Выход выполнен'})


@extend_schema(
    tags=['Users'],
    summary='Обновить токен',
    description='Обновляет access-токен по действительному refresh-токену (одноразовый — старый refresh-токен становится недействителен).',
    request=TokenRefreshRequestSerializer,
    responses={
        200: TokenRefreshResponseSerializer,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def token_refresh(request):
    incoming = request.data.get('refresh_token', '')
    if not incoming:
        return Response({'error': 'refresh_token не передан'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payload = decode_token(incoming)
    except pyjwt.ExpiredSignatureError:
        return Response({'error': 'Refresh token истёк. Войдите заново.'}, status=status.HTTP_401_UNAUTHORIZED)
    except pyjwt.InvalidTokenError:
        return Response({'error': 'Недействительный refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

    if payload.get('type') != 'refresh':
        return Response({'error': 'Недействительный refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        user = User.collection.get(f"users/{payload['user_id']}")
    except Exception:
        user = None
    if not user or user.refresh_token_jti != payload['jti']:
        return Response({'error': 'Refresh token недействителен или уже использован'}, status=status.HTTP_401_UNAUTHORIZED)

    new_access = generate_token(
        user_id=user.id,
        username=user.username,
        status=user.status,
        verification_status=user.verification_status,
    )
    new_refresh, new_jti = generate_refresh_token(user.id)
    user.refresh_token_jti = new_jti
    user.update()

    return Response({
        'token':         new_access,
        'refresh_token': new_refresh,
    })


# ---------------------------------------------------------------------------
# Password reset (забыли пароль)
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Users'],
    summary='Забыли пароль — отправить код',
    description=(
        'Отправляет 6-значный код на email пользователя. Код действует '
        f'{RESET_CODE_LIFETIME_MINUTES} минут, повторная отправка — не чаще раза в '
        f'{RESET_CODE_RESEND_SECONDS // 60} минут. Ответ одинаковый независимо от того, '
        'существует ли email (защита от перебора).'
    ),
    request=ForgotPasswordRequestSerializer,
    responses={
        200: MessageResponseSerializer,
        400: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def forgot_password(request):
    email = _normalize_email(request.data.get('email'))
    if not email:
        return Response({'error': 'Поле "email" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    users = list(User.collection.filter('email', '==', email).fetch(1))
    if not users:
        return Response({'message': FORGOT_PASSWORD_MESSAGE})

    user = users[0]
    now  = datetime.now(timezone.utc)

    # Rate limit: не отправляем новый код, если предыдущий ушёл меньше минуты назад
    if user.reset_code_sent_at and (now - user.reset_code_sent_at).total_seconds() < RESET_CODE_RESEND_SECONDS:
        return Response({'message': FORGOT_PASSWORD_MESSAGE})

    code = f'{secrets.randbelow(1_000_000):06d}'
    user.reset_code_hash     = make_password(code)
    user.reset_code_expires  = now + timedelta(minutes=RESET_CODE_LIFETIME_MINUTES)
    user.reset_code_attempts = 0
    user.reset_code_sent_at  = now
    user.update()

    try:
        send_mail(
            subject='Sejong: код для сброса пароля',
            message=(
                f'Ваш код для сброса пароля: {code}\n\n'
                f'Код действует {RESET_CODE_LIFETIME_MINUTES} минут.\n'
                'Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        # Не раскрываем наружу проблемы SMTP; код остаётся валидным до истечения
        pass

    return Response({'message': FORGOT_PASSWORD_MESSAGE})


@extend_schema(
    tags=['Users'],
    summary='Забыли пароль — проверить код',
    description=(
        'Проверяет 6-значный код из письма. При верном коде возвращает короткоживущий '
        'reset_token для смены пароля. После '
        f'{RESET_CODE_MAX_ATTEMPTS} неверных попыток код аннулируется — нужно запросить новый.'
    ),
    request=VerifyResetCodeRequestSerializer,
    responses={
        200: VerifyResetCodeResponseSerializer,
        400: ErrorResponseSerializer,
        429: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def verify_reset_code(request):
    email = _normalize_email(request.data.get('email'))
    code  = (request.data.get('code') or '').strip()
    if not email or not code:
        return Response({'error': 'Поля "email" и "code" обязательны'}, status=status.HTTP_400_BAD_REQUEST)

    users = list(User.collection.filter('email', '==', email).fetch(1))
    user  = users[0] if users else None

    if not user or not user.reset_code_hash:
        return Response(
            {'error': 'Код неверен или истёк. Запросите новый код.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = datetime.now(timezone.utc)
    if not user.reset_code_expires or now > user.reset_code_expires:
        _clear_reset_code(user)
        user.update()
        return Response(
            {'error': 'Код истёк. Запросите новый код.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not check_password(code, user.reset_code_hash):
        attempts = (user.reset_code_attempts or 0) + 1
        if attempts >= RESET_CODE_MAX_ATTEMPTS:
            _clear_reset_code(user)
            user.update()
            return Response(
                {'error': 'Слишком много неверных попыток. Запросите новый код.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        user.reset_code_attempts = attempts
        user.update()
        return Response(
            {'error': f'Неверный код. Осталось попыток: {RESET_CODE_MAX_ATTEMPTS - attempts}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Код верный: аннулируем его и выдаём одноразовый reset-токен
    reset_token, reset_jti = generate_reset_token(user.id)
    _clear_reset_code(user)
    user.reset_token_jti = reset_jti
    user.update()

    return Response({
        'message': 'Код подтверждён. Установите новый пароль.',
        'reset_token': reset_token,
    })


@extend_schema(
    tags=['Users'],
    summary='Забыли пароль — установить новый',
    description=(
        'Устанавливает новый пароль по reset_token из verify-code. Токен одноразовый и '
        f'действует {RESET_TOKEN_LIFETIME_MINUTES} минут. После смены пароля все '
        'refresh-токены пользователя отзываются.'
    ),
    request=ResetPasswordRequestSerializer,
    responses={
        200: MessageResponseSerializer,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer,
    },
)
@api_view(['POST'])
def reset_password(request):
    reset_token  = request.data.get('reset_token', '')
    new_password = request.data.get('new_password', '')

    if not reset_token or not new_password:
        return Response(
            {'error': 'Поля "reset_token" и "new_password" обязательны'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(new_password) < 6:
        return Response(
            {'error': 'Пароль должен содержать минимум 6 символов'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = decode_token(reset_token)
    except pyjwt.ExpiredSignatureError:
        return Response(
            {'error': 'Срок действия reset_token истёк. Запросите код заново.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    except pyjwt.InvalidTokenError:
        return Response({'error': 'Недействительный reset_token'}, status=status.HTTP_401_UNAUTHORIZED)

    if payload.get('type') != 'reset':
        return Response({'error': 'Недействительный reset_token'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        user = User.collection.get(f"users/{payload['user_id']}")
    except Exception:
        user = None
    if not user or user.reset_token_jti != payload['jti']:
        return Response(
            {'error': 'Reset token недействителен или уже использован'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user.password        = make_password(new_password)
    user.reset_token_jti = ''
    # Отзываем refresh-токены: после сброса пароля старые сессии недействительны
    user.refresh_token_jti = ''
    user.update()

    return Response({'message': 'Пароль изменён. Войдите с новым паролем.'})


# ---------------------------------------------------------------------------
# Profile — get my data
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Users'],
    summary='Мои данные',
    description='Возвращает данные профиля текущего авторизованного пользователя.',
    parameters=[AUTH_HEADER_PARAM],
    responses={
        200: ProfileSerializer,
        404: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['GET'])
@jwt_required
def get_profile(request):
    user_id = request.user_payload.get('user_id', '')
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'id':                  user.id,
        'username':            user.username or '',
        'fullname':            user.fullname or '',
        'email':               user.email or '',
        'pending_email':       user.pending_email or '',
        'phone_number':        user.phone_number or '',
        'date_of_birth':       user.date_of_birth or '',
        'status':              user.status or '',
        'verification_status': user.verification_status or '',
        'group_id':            user.group or '',
        'avatar':              user.avatar or '',
        'date_joined':         str(user.date_joined) if user.date_joined else '',
    })


# ---------------------------------------------------------------------------
# Admin — users
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Users'],
    operation_id='users_admin_list_users',
    summary='Список пользователей (admin)',
    description='Список всех пользователей с опциональной фильтрацией по статусу, статусу верификации или группе.',
    parameters=[
        AUTH_HEADER_PARAM,
        OpenApiParameter('status', OpenApiTypes.STR, description='Фильтр по статусу (Student/Teacher/Admin/Guest)'),
        OpenApiParameter('verification_status', OpenApiTypes.STR, description='Фильтр по статусу верификации (Pending/Approved/Rejected)'),
        OpenApiParameter('group_id', OpenApiTypes.STR, description='Фильтр по ID группы'),
    ],
    responses={
        200: AdminListUsersResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['GET'])
@admin_required
def admin_list_users(request):
    """Список всех пользователей с фильтрацией.
    Query params: ?status=  ?verification_status=  ?group_id=
    """
    filter_status = request.query_params.get('status')
    filter_verify = request.query_params.get('verification_status')
    filter_group  = request.query_params.get('group_id')

    if filter_status and filter_status in VALID_STATUSES:
        users = list(User.collection.filter('status', '==', filter_status).fetch(500))
    elif filter_verify and filter_verify in ('Pending', 'Approved', 'Rejected'):
        users = list(User.collection.filter('verification_status', '==', filter_verify).fetch(500))
    elif filter_group:
        users = list(User.collection.filter('group', '==', filter_group).fetch(500))
    else:
        users = list(User.collection.fetch(500))

    groups_cache = {g.id: g.name for g in Group.collection.fetch(100)}

    return Response({
        'total': len(users),
        'users': [_user_dict(u, groups_cache) for u in users],
    })


@extend_schema(
    tags=['Users'],
    summary='Получить пользователя (admin)',
    description='Получить полную информацию об одном пользователе по ID.',
    parameters=[AUTH_HEADER_PARAM],
    responses={
        200: AdminGetUserResponseSerializer,
        404: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['GET'])
@admin_required
def admin_get_user(request, user_id):
    """Получить одного пользователя по ID."""
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'user': _user_dict(user, full=True)})


@extend_schema(
    tags=['Users'],
    summary='Редактировать пользователя (admin)',
    description=(
        'Частичное обновление данных пользователя. Передавайте только изменяемые поля. '
        'При смене email на новую почту отправляется 6-значный код подтверждения '
        f'(действует {EMAIL_CODE_LIFETIME_MINUTES} минут) — до подтверждения через '
        '/users/register/verify/ вход для пользователя будет недоступен.'
    ),
    parameters=[AUTH_HEADER_PARAM],
    request=AdminEditUserRequestSerializer,
    responses={
        200: AdminEditUserResponseSerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['PATCH'])
@admin_required
def admin_edit_user(request, user_id):
    """Редактировать данные пользователя."""
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    updated_fields = []

    if 'fullname' in data:
        user.fullname = data['fullname']
        updated_fields.append('fullname')

    if 'email' in data:
        new_email = _normalize_email(data['email'])
        err = _validate_email(new_email)
        if err:
            return err
        if new_email != user.email:
            if _email_taken(new_email):
                return Response(
                    {'error': 'Пользователь с такой почтой уже существует. Укажите другой email.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.email = new_email
            user.email_verified = False
            user.pending_email = ''  # админская смена перекрывает незавершённую смену из профиля
            _send_email_verification_code(user, datetime.now(timezone.utc))
            updated_fields.append('email')

    if 'phone_number' in data:
        phone = data['phone_number'].strip()
        err = _validate_phone(phone)
        if err:
            return err
        user.phone_number = phone
        updated_fields.append('phone_number')

    if 'date_of_birth' in data:
        user.date_of_birth = data['date_of_birth']
        updated_fields.append('date_of_birth')

    if 'status' in data:
        if data['status'] not in VALID_STATUSES:
            return Response(
                {'error': f'Допустимые статусы: {", ".join(VALID_STATUSES)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.status = data['status']
        updated_fields.append('status')

    if 'verification_status' in data:
        if data['verification_status'] not in ('Pending', 'Approved', 'Rejected'):
            return Response(
                {'error': 'Допустимые значения: Pending, Approved, Rejected'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.verification_status = data['verification_status']
        updated_fields.append('verification_status')

    if 'group_id' in data:
        group_id = data['group_id']
        if group_id:
            try:
                group = Group.collection.get(f'groups/{group_id}')
            except Exception:
                group = None
            if not group:
                return Response({'error': 'Группа не найдена'}, status=status.HTTP_404_NOT_FOUND)
        user.group = group_id
        updated_fields.append('group')

    if 'group' in data and 'group_id' not in data:
        group_name = data['group'].strip()
        if group_name:
            found = list(Group.collection.filter('name', '==', group_name).fetch(1))
            if not found:
                return Response({'error': f'Группа "{group_name}" не найдена'}, status=status.HTTP_404_NOT_FOUND)
            user.group = found[0].id
        else:
            user.group = ''
        updated_fields.append('group')

    if 'password' in data:
        new_pass = data['password']
        if not new_pass:
            return Response({'error': 'Пароль не может быть пустым'}, status=status.HTTP_400_BAD_REQUEST)
        user.password = make_password(new_pass)
        updated_fields.append('password')

    if not updated_fields:
        return Response({'message': 'Нет данных для обновления'}, status=status.HTTP_400_BAD_REQUEST)

    user.update()
    log_action(request, 'update', 'User', user_id, {'updated_fields': updated_fields})

    message = 'Данные пользователя обновлены'
    if 'email' in updated_fields:
        message += (
            '. На новую почту отправлен 6-значный код — пользователь должен '
            'подтвердить email, иначе вход будет недоступен.'
        )

    return Response({
        'message': message,
        'updated_fields': updated_fields,
        'user': _user_dict(user),
    })


@extend_schema(
    tags=['Users'],
    summary='Сменить аватар пользователя (admin)',
    description='Заменить аватар любого пользователя по ID (multipart/form-data, поле "avatar").',
    parameters=[AUTH_HEADER_PARAM],
    request={'multipart/form-data': ChangeAvatarRequestSerializer},
    responses={
        200: ChangeAvatarResponseSerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        502: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['POST'])
@admin_required
def admin_change_avatar(request, user_id):
    """Заменить аватар указанного пользователя (multipart/form-data, поле "avatar")."""
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    new_url, err = _replace_avatar(user, request.FILES.get('avatar'))
    if err:
        return err

    log_action(request, 'update', 'User', user_id, {'updated_fields': ['avatar']})

    return Response({
        'message': f'Аватар пользователя "{user.username}" успешно обновлён',
        'avatar': new_url,
    })


@extend_schema(
    tags=['Users'],
    summary='Подтвердить/отклонить верификацию (admin)',
    description='При подтверждении статус пользователя меняется на "Student".',
    parameters=[AUTH_HEADER_PARAM],
    request=AdminVerifyUserRequestSerializer,
    responses={
        200: AdminVerifyUserResponseSerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['POST'])
@admin_required
def admin_verify_user(request, user_id):
    """Подтвердить или отклонить верификацию.
    Body: { "action": "approve" | "reject" }
    """
    action = request.data.get('action')
    if action not in ('approve', 'reject'):
        return Response(
            {'error': 'Поле "action" должно быть "approve" или "reject"'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    if action == 'approve':
        user.verification_status = 'Approved'
        user.status = 'Student'
    else:
        user.verification_status = 'Rejected'

    user.update()
    log_action(request, 'update', 'User', user_id, {
        'verification_action': action,
        'verification_status': user.verification_status,
    })
    return Response({
        'message': f'Пользователь {"подтверждён" if action == "approve" else "отклонён"}.',
        'user': _user_dict(user),
    })


@extend_schema(
    tags=['Users'],
    summary='Назначить статус (admin)',
    parameters=[AUTH_HEADER_PARAM],
    request=AdminSetStatusRequestSerializer,
    responses={
        200: AdminSetStatusResponseSerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['POST'])
@admin_required
def admin_set_status(request, user_id):
    """Назначить статус пользователю.
    Body: { "status": "Student" | "Teacher" | "Admin" | "Guest" }
    """
    new_status = request.data.get('status')
    if new_status not in VALID_STATUSES:
        return Response(
            {'error': f'Допустимые статусы: {", ".join(VALID_STATUSES)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    user.status = new_status
    user.update()
    log_action(request, 'update', 'User', user_id, {'new_status': new_status})
    return Response({
        'message': f'Статус пользователя изменён на "{new_status}".',
        'user': _user_dict(user),
    })


@extend_schema(
    tags=['Users'],
    summary='Удалить пользователя (admin)',
    description=(
        'Удаляет любого пользователя, кроме администраторов (проверка по статусу). '
        'Вместе с аккаунтом удаляются аватар с Google Drive и указатель чтения чата; '
        'refresh-токен отзывается сразу, выданный access-токен доживает свой срок '
        '(максимум 1 день), но все эндпоинты, читающие пользователя, вернут 404. '
        'Сообщения пользователя в чате группы сохраняются (имя и аватар в них '
        'денормализованы).'
    ),
    parameters=[AUTH_HEADER_PARAM],
    responses={
        200: MessageResponseSerializer,
        404: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['DELETE'])
@admin_required
def admin_delete_user(request, user_id):
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    if user.status == 'Admin':
        return Response(
            {'error': 'Нельзя удалить администратора. Сначала смените ему статус.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Отзыв refresh-токена: сам документ пользователя исчезнет, но blacklist
    # закрывает и путь через уже выданный refresh
    if user.refresh_token_jti:
        try:
            bt = BlacklistedToken()
            bt.id = user.refresh_token_jti
            bt.save()
        except Exception:
            pass

    # Аватар с Google Drive (у дефолтного avatar_id пуст)
    if user.avatar_id:
        try:
            delete_avatar(user.avatar_id)
        except Exception:
            pass

    # Указатель чтения в чате группы
    if user.group:
        try:
            from chat_group.models import ChatReadStatus
            ChatReadStatus.collection.delete(f'groups/{user.group}/chat_read_status/{user_id}')
        except Exception:
            pass

    username_label = user.fullname or user.username
    deleted_info = {'username': user.username, 'fullname': user.fullname or '', 'status': user.status}
    User.collection.delete(f'users/{user_id}')
    log_action(request, 'delete', 'User', user_id, deleted_info)
    return Response({'message': f'Пользователь "{username_label}" удалён'})


@extend_schema(
    tags=['Users'],
    summary='Создать пользователя (admin)',
    description='Создать нового пользователя вручную. Верификация выставляется сразу как "Approved".',
    parameters=[AUTH_HEADER_PARAM],
    request=AdminCreateUserRequestSerializer,
    responses={
        201: AdminCreateUserResponseSerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['POST'])
@admin_required
def admin_create_user(request):
    """Создать нового пользователя вручную."""
    data = request.data

    err = _require_fields(data, 'username', 'password', 'email', 'phone_number')
    if err:
        return err

    err = _validate_phone(data['phone_number'])
    if err:
        return err

    if _username_taken(data['username']):
        return Response(
            {'error': 'Пользователь с таким username уже существует'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if _email_taken(data['email']):
        return Response(
            {'error': 'Пользователь с такой почтой уже существует. Укажите другой email.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_status = data.get('status', 'Student')
    if user_status not in VALID_STATUSES:
        return Response(
            {'error': f'Допустимые статусы: {", ".join(VALID_STATUSES)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    group_id   = data.get('group_id', '')
    group_name = data.get('group', '')
    if group_name and not group_id:
        found = list(Group.collection.filter('name', '==', group_name).fetch(1))
        if not found:
            return Response({'error': f'Группа "{group_name}" не найдена'}, status=status.HTTP_404_NOT_FOUND)
        group_id = found[0].id
    elif group_id:
        try:
            group = Group.collection.get(f'groups/{group_id}')
        except Exception:
            group = None
        if not group:
            return Response({'error': 'Группа не найдена'}, status=status.HTTP_404_NOT_FOUND)

    user = User()
    user.username      = data['username']
    user.password      = make_password(data['password'])
    user.fullname      = data.get('fullname', '')
    user.email         = _normalize_email(data['email'])
    user.phone_number  = data['phone_number']
    user.date_of_birth = data.get('date_of_birth', '')
    user.status        = user_status
    user.group         = group_id
    user.avatar        = data.get('avatar', DEFAULT_AVATAR)
    user.verification_status = 'Approved'
    user.email_verified       = True
    user.save()
    log_action(request, 'create', 'User', user.id, {
        'username': user.username,
        'status':   user.status,
    })

    return Response({
        'message': f'Пользователь "{user.username}" успешно создан.',
        'user': _user_dict(user),
    }, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Users'],
    summary='Обновить профиль',
    description=(
        'Частичное обновление своего профиля. Для смены пароля обязательно передать '
        'текущий пароль в поле "check_password". При смене email новая почта сохраняется '
        'как pending_email и на неё отправляется 6-значный код подтверждения (действует '
        f'{EMAIL_CODE_LIFETIME_MINUTES} минут). Почта в профиле меняется только после '
        'подтверждения кода через /users/register/verify/ (в поле "email" передать новую '
        'почту); до этого действует прежний email. Повторная отправка того же email — '
        'код заново не отправляется. Передача текущего email отменяет незавершённую смену.'
    ),
    parameters=[AUTH_HEADER_PARAM],
    request=UpdateProfileRequestSerializer,
    responses={
        200: UpdateProfileResponseSerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['PATCH'])
@jwt_required
def update_profile(request):
    """Обновить данные своего профиля."""
    data    = request.data
    payload = request.user_payload
    user_id = payload['user_id']

    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    updated_fields = []

    if 'username' in data:
        new_username = data['username'].strip()
        if not new_username:
            return Response({'error': 'Username не может быть пустым'}, status=status.HTTP_400_BAD_REQUEST)
        if new_username != user.username:
            if _username_taken(new_username):
                return Response({'error': 'Пользователь с таким username уже существует'}, status=status.HTTP_400_BAD_REQUEST)
            user.username = new_username
            updated_fields.append('username')

    email_change_cancelled = False
    if 'email' in data:
        new_email = _normalize_email(data['email'])
        err = _validate_email(new_email)
        if err:
            return err
        if new_email == user.email:
            # Почта не меняется; если была незавершённая смена — отменяем её
            if user.pending_email:
                user.pending_email = ''
                _clear_email_code(user)
                email_change_cancelled = True
                updated_fields.append('email')
        else:
            if _email_taken(new_email):
                return Response(
                    {'error': 'Пользователь с такой почтой уже существует. Укажите другой email.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            now = datetime.now(timezone.utc)
            # Та же почта уже ждёт подтверждения и код ушёл недавно — письмо повторно не шлём
            already_sent = (
                new_email == user.pending_email
                and user.email_code_sent_at
                and (now - user.email_code_sent_at).total_seconds() < EMAIL_CODE_RESEND_SECONDS
            )
            user.pending_email = new_email
            if not already_sent:
                _send_email_verification_code(user, now)
            updated_fields.append('email')

    if 'phone_number' in data:
        phone = data['phone_number'].strip()
        err = _validate_phone(phone)
        if err:
            return err
        user.phone_number = phone
        updated_fields.append('phone_number')

    if 'password' in data:
        current = data.get('check_password', '')
        if not current:
            return Response(
                {'error': "Для смены пароля укажите текущий пароль в поле 'check_password'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not check_password(current, user.password):
            return Response({'error': 'Неверный текущий пароль'}, status=status.HTTP_400_BAD_REQUEST)
        user.password = make_password(data['password'])
        updated_fields.append('password')

    if not updated_fields:
        return Response({'message': 'Нет данных для обновления'}, status=status.HTTP_400_BAD_REQUEST)

    user.update()

    new_token = generate_token(
        user_id=user.id,
        username=user.username,
        status=user.status,
        verification_status=user.verification_status,
    )

    message = 'Профиль обновлён'
    if 'email' in updated_fields:
        if email_change_cancelled:
            message += '. Незавершённая смена почты отменена.'
        else:
            message += (
                f'. Мы отправили 6-значный код на {user.pending_email} — подтвердите новую '
                'почту через /users/register/verify/. До подтверждения в профиле действует '
                'прежний email.'
            )

    return Response({
        'message': message,
        'updated_fields': updated_fields,
        'token': new_token,
    })


@extend_schema(
    tags=['Users'],
    summary='Профиль — отправить код подтверждения email повторно',
    description=(
        'Повторно отправляет 6-значный код подтверждения на email текущего пользователя. '
        'Если начата смена почты (есть pending_email), код уходит на новую почту. '
        'Повторная отправка — не чаще раза в '
        f'{EMAIL_CODE_RESEND_SECONDS // 60} минут. В отличие от /users/register/resend-code/ '
        'эндпоинт авторизованный, поэтому отвечает честно: код отправлен, email уже '
        'подтверждён или сработал лимит повторной отправки (429, поле retry_after_seconds).'
    ),
    parameters=[AUTH_HEADER_PARAM],
    request=None,
    responses={
        200: MessageResponseSerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        429: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['POST'])
@jwt_required
def profile_resend_email_code(request):
    """Повторная отправка кода подтверждения email для авторизованного пользователя."""
    user_id = request.user_payload.get('user_id', '')
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    # Незавершённая смена почты имеет приоритет: код шлём на новую почту
    target_email = user.pending_email or user.email
    if not target_email:
        return Response(
            {'error': 'У профиля не указан email. Сначала укажите почту через /users/profile/update/.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if user.email_verified and not user.pending_email:
        return Response(
            {'error': 'Email уже подтверждён, отправка кода не требуется.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = datetime.now(timezone.utc)
    if user.email_code_sent_at:
        elapsed = (now - user.email_code_sent_at).total_seconds()
        if elapsed < EMAIL_CODE_RESEND_SECONDS:
            retry_after = int(EMAIL_CODE_RESEND_SECONDS - elapsed)
            minutes_left = max(1, -(-retry_after // 60))  # округление вверх
            return Response(
                {
                    'error': f'Код уже отправлен. Повторная отправка возможна через {minutes_left} мин.',
                    'retry_after_seconds': retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

    _send_email_verification_code(user, now)
    user.update()

    return Response({
        'message': (
            f'Код отправлен на {target_email}. Код действует {EMAIL_CODE_LIFETIME_MINUTES} минут. '
            'Подтвердите email через /users/register/verify/.'
        ),
    })


def _replace_avatar(user, file):
    """Проверить файл, удалить старый аватар и загрузить новый на Google Drive.

    Возвращает (new_url, None) при успехе или (None, Response) с ошибкой.
    """
    if not file:
        return None, Response({'error': 'Файл не передан. Используйте поле "avatar"'}, status=status.HTTP_400_BAD_REQUEST)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return None, Response(
            {'error': 'Недопустимый формат. Разрешены: JPEG, PNG, WEBP'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if file.size > MAX_AVATAR_SIZE:
        return None, Response({'error': 'Файл слишком большой. Максимум 3 МБ'}, status=status.HTTP_400_BAD_REQUEST)

    if user.avatar_id:
        try:
            delete_avatar(user.avatar_id)
        except Exception:
            pass

    ext = file.name.rsplit('.', 1)[-1] if '.' in file.name else 'jpg'
    filename = f"avatar_{user.id}.{ext}"

    try:
        new_file_id, new_url = upload_avatar(file, filename, file.content_type)
    except Exception as e:
        return None, Response({'error': f'Ошибка загрузки на Google Drive: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

    user.avatar    = new_url
    user.avatar_id = new_file_id
    user.update()
    return new_url, None


@extend_schema(
    tags=['Users'],
    summary='Сменить аватар',
    parameters=[AUTH_HEADER_PARAM],
    request={'multipart/form-data': ChangeAvatarRequestSerializer},
    responses={
        200: ChangeAvatarResponseSerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        502: ErrorResponseSerializer,
        **UNAUTHORIZED_RESPONSES,
    },
)
@api_view(['POST'])
@jwt_required
def change_avatar(request):
    """Заменить аватар пользователя (multipart/form-data, поле "avatar")."""
    user_id = request.user_payload['user_id']
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    new_url, err = _replace_avatar(user, request.FILES.get('avatar'))
    if err:
        return err

    return Response({
        'message': 'Аватар успешно обновлён',
        'avatar': new_url,
    })


# ---------------------------------------------------------------------------
# Bulk import
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Users'],
    summary='Массовая загрузка студентов (admin)',
    description=(
        'Загружает студентов из Excel-файла (.xlsx) и возвращает файл .xlsx с результатами '
        'импорта (логины/пароли/ошибки). Колонка "Email" обязательна; строки с пустой или '
        'уже зарегистрированной почтой помечаются как ошибка и пропускаются.'
    ),
    parameters=[AUTH_HEADER_PARAM],
    request={'multipart/form-data': BulkImportRequestSerializer},
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.BINARY,
            description='Файл .xlsx с результатами импорта (students_credentials.xlsx).',
        ),
        400: ErrorResponseSerializer,
        **ADMIN_RESPONSES,
    },
)
@api_view(['POST'])
@admin_required
def admin_bulk_import(request):
    """Массовая загрузка студентов из Excel (.xlsx), поле "file"."""
    excel_file = request.FILES.get('file')
    if not excel_file:
        return Response({'error': 'Файл не передан. Используйте поле "file"'}, status=status.HTTP_400_BAD_REQUEST)

    if not excel_file.name.endswith('.xlsx'):
        return Response({'error': 'Разрешён только формат .xlsx'}, status=status.HTTP_400_BAD_REQUEST)

    rows, parse_error = _open_import_workbook(excel_file)
    if parse_error:
        return Response({'error': parse_error}, status=status.HTTP_400_BAD_REQUEST)

    col_map = _detect_columns(rows[0])
    if not col_map:
        return Response(
            {'error': 'Не найдены известные заголовки. Ожидаются: ФИО, Email, Телефон, Группа, Дата рождения'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if 'email' not in col_map:
        return Response(
            {'error': 'В файле отсутствует колонка "Email" — она обязательна'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    batch_usernames: set = set()
    batch_emails:    set = set()
    groups_by_name  = {g.name.lower(): g.id for g in Group.collection.fetch(100)}

    results = []
    for row in rows[1:]:
        values = [cell.value for cell in row]
        if all(v is None for v in values):
            continue

        def get(field):
            idx = col_map.get(field)
            return str(values[idx]).strip() if idx is not None and values[idx] is not None else ''

        fullname      = get('fullname')
        email         = _normalize_email(get('email'))
        phone_number  = re.sub(r'[^\d+]', '', get('phone_number'))
        date_of_birth = get('date_of_birth')
        group_name    = get('group')

        # Email обязателен: без него студент не создаётся
        if not email:
            results.append((
                fullname, email, phone_number, group_name, '', '',
                'Ошибка', 'Поле "Email" обязательно. Укажите почту студента.',
            ))
            continue

        # Проверка почты: не создаём студента, если email уже занят в базе
        # или повторяется в этом же файле
        if email in batch_emails or _email_taken(email):
            results.append((
                fullname, email, phone_number, group_name, '', '',
                'Ошибка', 'Пользователь с такой почтой уже существует. Укажите другую почту.',
            ))
            continue
        batch_emails.add(email)

        username = _generate_username(fullname or 'student', batch_usernames)
        password = _generate_password()
        batch_usernames.add(username)

        group_id = groups_by_name.get(group_name.lower(), '') if group_name else ''

        try:
            user = User()
            user.username      = username
            user.password      = make_password(password)
            user.fullname      = fullname
            user.email         = email
            user.phone_number  = phone_number
            user.date_of_birth = date_of_birth
            user.status        = 'Student'
            user.group         = group_id
            user.avatar        = DEFAULT_AVATAR
            user.verification_status = 'Approved'
            user.email_verified       = True
            user.save()
            results.append((fullname, email, phone_number, group_name, username, password, 'Успешно', ''))
        except Exception as e:
            results.append((fullname, email, phone_number, group_name, '', '', 'Ошибка', str(e)))

    success_count = sum(1 for r in results if r[6] == 'Успешно')
    error_count   = len(results) - success_count
    log_action(request, 'create', 'User', 'bulk_import', {
        'total':   len(results),
        'success': success_count,
        'errors':  error_count,
    })

    return _xlsx_response(_build_import_results_xlsx(results), 'students_credentials.xlsx')


@extend_schema(
    tags=['Users'],
    summary='Шаблон Excel для импорта (admin)',
    description='Скачать шаблон .xlsx для массовой загрузки студентов.',
    parameters=[AUTH_HEADER_PARAM],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.BINARY,
            description='Файл .xlsx-шаблона (students_import_template.xlsx).',
        ),
        **ADMIN_RESPONSES,
    },
)
@api_view(['GET'])
@admin_required
def admin_bulk_import_template(request):
    """Скачать шаблон Excel для массовой загрузки студентов."""
    return _xlsx_response(_build_import_template_xlsx(), 'students_import_template.xlsx')
