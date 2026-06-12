import re
import jwt as pyjwt
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import User, BlacklistedToken, Group
from utils.jwt_utils import generate_token, decode_token
from utils.decorators import admin_required, jwt_required
from utils.drive import upload_avatar, delete_avatar


PHONE_RE = re.compile(r'^\+992\d{9}$')


@api_view(['POST'])
def register(request):
    data = request.data

    for field in ('username', 'password', 'email', 'phone_number'):
        if not data.get(field):
            return Response(
                {'error': f'Поле "{field}" обязательно'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if not PHONE_RE.match(data['phone_number']):
        return Response(
            {'error': "Номер должен начинаться с '+992' и содержать 9 цифр после него."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing = list(User.collection.filter('username', '==', data['username']).fetch(1))
    if existing:
        return Response(
            {'error': 'Пользователь с таким username уже существует'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User()
    user.username     = data['username']
    user.fullname     = data.get('fullname', '')
    user.email        = data['email']
    user.phone_number = data['phone_number']
    user.password     = make_password(data['password'])
    user.date_of_birth = data.get('date_of_birth', '')
    user.status               = 'Guest'
    user.verification_status  = 'Pending'
    user.save()

    token = generate_token(
        user_id=user.id,
        username=user.username,
        status=user.status,
        verification_status=user.verification_status,
    )

    return Response({
        'message': 'Регистрация успешна. Ожидайте подтверждения администратора.',
        'token': token,
        'status': user.status,
        'verification_status': user.verification_status,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def login(request):
    data     = request.data
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return Response(
            {'error': 'Введите username и пароль'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    users = list(User.collection.filter('username', '==', username).fetch(1))
    if not users or not check_password(password, users[0].password):
        return Response(
            {'error': 'Неверный username или пароль'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user = users[0]

    token = generate_token(
        user_id=user.id,
        username=user.username,
        status=user.status,
        verification_status=user.verification_status,
    )

    return Response({
        'message': 'Вход выполнен',
        'token': token,
        'status': user.status,
        'verification_status': user.verification_status,
    })


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

    # Добавляем JTI в чёрный список (document ID = JTI → поиск O(1))
    bt = BlacklistedToken()
    bt.id = payload['jti']
    bt.save()

    return Response({'message': 'Выход выполнен'})


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

VALID_STATUSES = {'Student', 'Teacher', 'Admin', 'Guest'}


def _user_dict(user):
    return {
        'id': user.id,
        'username': user.username,
        'fullname': user.fullname,
        'email': user.email,
        'phone_number': user.phone_number,
        'status': user.status,
        'verification_status': user.verification_status,
        'group': user.group,
    }


@api_view(['GET'])
@admin_required
def admin_pending_users(request):
    """Список пользователей, ожидающих верификации."""
    users = list(User.collection.filter('verification_status', '==', 'Pending').fetch(100))
    return Response({'users': [_user_dict(u) for u in users]})


@api_view(['POST'])
@admin_required
def admin_verify_user(request, user_id):
    """Подтвердить или отклонить верификацию пользователя.
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
    return Response({
        'message': f'Пользователь {"подтверждён" if action == "approve" else "отклонён"}.',
        'user': _user_dict(user),
    })


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
    return Response({
        'message': f'Статус пользователя изменён на "{new_status}".',
        'user': _user_dict(user),
    })


@api_view(['POST'])
@admin_required
def admin_assign_group(request, user_id):
    """Назначить пользователя в группу.
    Body: { "group_id": "<id группы>" }
    """
    group_id = request.data.get('group_id')
    if not group_id:
        return Response({'error': 'Поле "group_id" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        group = Group.collection.get(f'groups/{group_id}')
    except Exception:
        group = None
    if not group:
        return Response({'error': 'Группа не найдена'}, status=status.HTTP_404_NOT_FOUND)

    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    user.group = group_id
    user.update()
    return Response({
        'message': f'Пользователь добавлен в группу "{group.name}".',
        'user': _user_dict(user),
    })


@api_view(['GET'])
@admin_required
def admin_list_groups(request):
    """Список всех групп."""
    groups = list(Group.collection.fetch(100))
    return Response({'groups': [{'id': g.id, 'name': g.name} for g in groups]})


@api_view(['POST'])
@admin_required
def admin_create_group(request):
    """Создать новую группу.
    Body: { "name": "название группы" }
    """
    name = request.data.get('name', '').strip()
    if not name:
        return Response({'error': 'Поле "name" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    existing = list(Group.collection.filter('name', '==', name).fetch(1))
    if existing:
        return Response({'error': f'Группа с именем "{name}" уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    group = Group()
    group.name = name
    group.save()
    return Response(
        {'message': f'Группа "{name}" создана.', 'group': {'id': group.id, 'name': group.name}},
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@admin_required
def admin_delete_group(request, group_id):
    """Удалить группу по ID."""
    try:
        group = Group.collection.get(f'groups/{group_id}')
    except Exception:
        group = None
    if not group:
        return Response({'error': 'Группа не найдена'}, status=status.HTTP_404_NOT_FOUND)

    Group.collection.delete(f'groups/{group_id}')
    return Response({'message': f'Группа "{group.name}" удалена.'})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@api_view(['POST'])
@jwt_required
def update_profile(request):
    """Обновить данные своего профиля. Все поля необязательные.
    Body: {
        "username":       "новый_логин",
        "email":          "new@email.com",
        "phone_number":   "+992XXXXXXXXX",
        "check_password": "текущий_пароль",
        "password":       "новый_пароль"
    }
    """
    data = request.data
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
            taken = list(User.collection.filter('username', '==', new_username).fetch(1))
            if taken:
                return Response({'error': 'Пользователь с таким username уже существует'}, status=status.HTTP_400_BAD_REQUEST)
            user.username = new_username
            updated_fields.append('username')

    if 'email' in data:
        user.email = data['email'].strip()
        updated_fields.append('email')

    if 'phone_number' in data:
        phone = data['phone_number'].strip()
        if not PHONE_RE.match(phone):
            return Response(
                {'error': "Номер должен начинаться с '+992' и содержать 9 цифр после него."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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

    return Response({
        'message': 'Профиль обновлён',
        'updated_fields': updated_fields,
        'token': new_token,
    })


ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_AVATAR_SIZE = 3 * 1024 * 1024  # 3 MB


@api_view(['POST'])
@jwt_required
def change_avatar(request):
    """Заменить аватар пользователя.
    Тело запроса: multipart/form-data, поле "avatar" — файл изображения.
    """
    file = request.FILES.get('avatar')
    if not file:
        return Response({'error': 'Файл не передан. Используйте поле "avatar"'}, status=status.HTTP_400_BAD_REQUEST)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return Response(
            {'error': f'Недопустимый формат. Разрешены: JPEG, PNG, WEBP'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if file.size > MAX_AVATAR_SIZE:
        return Response({'error': 'Файл слишком большой. Максимум 3 МБ'}, status=status.HTTP_400_BAD_REQUEST)

    user_id = request.user_payload['user_id']
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    ext = file.name.rsplit('.', 1)[-1] if '.' in file.name else 'jpg'
    filename = f"avatar_{user_id}.{ext}"

    try:
        new_file_id, new_url = upload_avatar(file, filename, file.content_type)
    except Exception as e:
        return Response({'error': f'Ошибка загрузки на Google Drive: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

    user.avatar = new_url
    user.avatar_id = new_file_id
    user.update()

    return Response({
        'message': 'Аватар успешно обновлён',
        'avatar': new_url,
    })
