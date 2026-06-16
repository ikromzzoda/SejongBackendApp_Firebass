import re
import uuid
import random
import string
import io
import jwt as pyjwt
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from .models import User, BlacklistedToken, DEFAULT_AVATAR
from groups.models import Group
from utils.jwt_utils import generate_token, decode_token
from utils.decorators import admin_required, jwt_required
from utils.drive import upload_avatar, delete_avatar


PHONE_RE = re.compile(r'^\+992\d{9}$')


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

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
    user.username      = data['username']
    user.fullname      = data.get('fullname', '')
    user.email         = data['email']
    user.phone_number  = data['phone_number']
    user.password      = make_password(data['password'])
    user.date_of_birth = data.get('date_of_birth', '')
    user.status              = 'Guest'
    user.verification_status = 'Pending'
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
        'fcm_topic': f'status_{user.status}',
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
        'fcm_topic': f'status_{user.status}',
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

    bt = BlacklistedToken()
    bt.id = payload['jti']
    bt.save()

    return Response({'message': 'Выход выполнен'})


# ---------------------------------------------------------------------------
# Admin — helpers
# ---------------------------------------------------------------------------

VALID_STATUSES = {'Student', 'Teacher', 'Admin', 'Guest'}


def _resolve_group_name(group_id: str, cache: dict | None = None) -> str:
    if not group_id:
        return ''
    if cache is not None:
        return cache.get(group_id, group_id)
    try:
        g = Group.collection.get(f'groups/{group_id}')
        return g.name if g else group_id
    except Exception:
        return group_id


def _user_dict(user, groups_cache: dict | None = None):
    return {
        'id': user.id,
        'username': user.username,
        'fullname': user.fullname,
        'email': user.email,
        'phone_number': user.phone_number,
        'status': user.status,
        'verification_status': user.verification_status,
        'group': _resolve_group_name(user.group or '', groups_cache),
    }


# ---------------------------------------------------------------------------
# Admin — users
# ---------------------------------------------------------------------------

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
    return Response({'user': _user_dict(user)})


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
        user.email = data['email']
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
    return Response({
        'message': 'Данные пользователя обновлены',
        'updated_fields': updated_fields,
        'user': _user_dict(user),
    })


@api_view(['GET'])
@admin_required
def admin_pending_users(request):
    """Список пользователей, ожидающих верификации."""
    users = list(User.collection.filter('verification_status', '==', 'Pending').fetch(100))
    return Response({'users': [_user_dict(u) for u in users]})


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
def admin_create_user(request):
    """Создать нового пользователя вручную."""
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
    user.email         = data['email']
    user.phone_number  = data['phone_number']
    user.date_of_birth = data.get('date_of_birth', '')
    user.status        = user_status
    user.group         = group_id
    user.avatar        = data.get('avatar', DEFAULT_AVATAR)
    user.verification_status = 'Approved'
    user.save()

    return Response({
        'message': f'Пользователь "{user.username}" успешно создан.',
        'user': _user_dict(user),
    }, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@api_view(['POST'])
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
    """Заменить аватар пользователя (multipart/form-data, поле "avatar")."""
    file = request.FILES.get('avatar')
    if not file:
        return Response({'error': 'Файл не передан. Используйте поле "avatar"'}, status=status.HTTP_400_BAD_REQUEST)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return Response(
            {'error': 'Недопустимый формат. Разрешены: JPEG, PNG, WEBP'},
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

    user.avatar    = new_url
    user.avatar_id = new_file_id
    user.update()

    return Response({
        'message': 'Аватар успешно обновлён',
        'avatar': new_url,
    })


# ---------------------------------------------------------------------------
# Bulk import
# ---------------------------------------------------------------------------

_COL_ALIASES = {
    'fullname':      ['Full Name', 'фио', 'ф.и.о', 'ф.и.о.', 'имя', 'полное имя', 'full name', 'name', 'имя фамилия'],
    'email':         ['email', 'Email', 'почта', 'e-mail', 'эл. почта', 'электронная почта'],
    'phone_number':  ['Phone Number', 'phone_number', 'телефон', 'номер', 'номер телефона', 'моб', 'моб.', 'тел'],
    'date_of_birth': ['Date of Birth/생년월일', 'дата рождения', 'дата', 'birth', 'д.р.', 'день рождения'],
    'group':         ['Group', 'группа', 'учебная группа', 'класс'],
}

_TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}


def _transliterate(text: str) -> str:
    return ''.join(_TRANSLIT.get(c, c) for c in text.lower())


def _generate_username(fullname: str, existing: set) -> str:
    parts = fullname.strip().split()
    if parts:
        base = _transliterate(parts[0])
        base = re.sub(r'[^a-z0-9]', '', base)[:12] or 'student'
    else:
        base = 'student'
    for _ in range(20):
        candidate = f"{base}_{random.randint(1000, 9999)}"
        if candidate not in existing:
            return candidate
    return f"student_{uuid.uuid4().hex[:8]}"


def _generate_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    pwd = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
    ]
    pwd += [random.choice(chars) for _ in range(length - 3)]
    random.shuffle(pwd)
    return ''.join(pwd)


def _detect_columns(header_row) -> dict:
    mapping = {}
    for idx, cell in enumerate(header_row):
        if cell.value is None:
            continue
        normalized = str(cell.value).strip().lower()
        for field, aliases in _COL_ALIASES.items():
            if normalized in aliases and field not in mapping:
                mapping[field] = idx
    return mapping


def _style_header(ws, col_count: int):
    header_fill = PatternFill('solid', fgColor='1F4E79')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    for col in range(1, col_count + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')


def _auto_width(ws):
    for col in ws.columns:
        max_len = max((len(str(c.value or '')) for c in col), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)


@api_view(['POST'])
@admin_required
def admin_bulk_import(request):
    """Массовая загрузка студентов из Excel (.xlsx), поле "file"."""
    excel_file = request.FILES.get('file')
    if not excel_file:
        return Response({'error': 'Файл не передан. Используйте поле "file"'}, status=status.HTTP_400_BAD_REQUEST)

    if not excel_file.name.endswith('.xlsx'):
        return Response({'error': 'Разрешён только формат .xlsx'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        wb_in = load_workbook(excel_file, data_only=True)
    except Exception:
        return Response({'error': 'Не удалось открыть файл. Убедитесь что это корректный .xlsx'}, status=status.HTTP_400_BAD_REQUEST)

    ws_in = wb_in.active
    rows  = list(ws_in.iter_rows())
    if len(rows) < 2:
        return Response({'error': 'Файл пустой или содержит только заголовок'}, status=status.HTTP_400_BAD_REQUEST)

    col_map = _detect_columns(rows[0])
    if not col_map:
        return Response(
            {'error': 'Не найдены известные заголовки. Ожидаются: ФИО, Email, Телефон, Группа, Дата рождения'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing_usernames = {u.username for u in User.collection.fetch(10000)}
    groups_by_name     = {g.name.lower(): g.id for g in Group.collection.fetch(100)}

    results = []
    for row in rows[1:]:
        values = [cell.value for cell in row]
        if all(v is None for v in values):
            continue

        def get(field):
            idx = col_map.get(field)
            return str(values[idx]).strip() if idx is not None and values[idx] is not None else ''

        fullname      = get('fullname')
        email         = get('email')
        phone_number  = re.sub(r'[^\d+]', '', get('phone_number'))
        date_of_birth = get('date_of_birth')
        group_name    = get('group')

        username = _generate_username(fullname or 'student', existing_usernames)
        password = _generate_password()
        existing_usernames.add(username)

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
            user.save()
            results.append((fullname, email, phone_number, group_name, username, password, 'Успешно', ''))
        except Exception as e:
            results.append((fullname, email, phone_number, group_name, '', '', 'Ошибка', str(e)))

    wb_out  = Workbook()
    ws_out  = wb_out.active
    ws_out.title = 'Результаты импорта'
    ws_out.row_dimensions[1].height = 20

    headers = ['№', 'ФИО', 'Email', 'Телефон', 'Группа', 'Username', 'Password', 'Статус', 'Примечание']
    ws_out.append(headers)
    _style_header(ws_out, len(headers))

    green_fill = PatternFill('solid', fgColor='E2EFDA')
    red_fill   = PatternFill('solid', fgColor='FFDDC1')

    for i, (fullname, email, phone, group, username, password, status_text, note) in enumerate(results, start=1):
        ws_out.append([i, fullname, email, phone, group, username, password, status_text, note])
        row_fill = green_fill if status_text == 'Успешно' else red_fill
        for col in range(1, len(headers) + 1):
            ws_out.cell(row=i + 1, column=col).fill      = row_fill
            ws_out.cell(row=i + 1, column=col).alignment = Alignment(vertical='center')

    for row in ws_out.iter_rows(min_row=2, min_col=6, max_col=7):
        for cell in row:
            cell.font = Font(bold=True)

    _auto_width(ws_out)

    success_count = sum(1 for r in results if r[6] == 'Успешно')
    error_count   = len(results) - success_count

    ws_out.append([])
    ws_out.append(['', f'Итого: {len(results)} строк | Успешно: {success_count} | Ошибок: {error_count}'])
    ws_out.cell(row=ws_out.max_row, column=2).font = Font(bold=True, size=11)

    output = io.BytesIO()
    wb_out.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="students_credentials.xlsx"'
    return response


@api_view(['GET'])
@admin_required
def admin_bulk_import_template(request):
    """Скачать шаблон Excel для массовой загрузки студентов."""
    wb = Workbook()
    ws = wb.active
    ws.title = 'Студенты'

    headers = ['ФИО', 'Email', 'Телефон', 'Дата рождения', 'Группа']
    ws.append(headers)
    _style_header(ws, len(headers))

    example_fill = PatternFill('solid', fgColor='EBF3FB')
    ws.append(['Иванов Иван Иванович', 'ivan@example.com', '+992991234567', '2003-05-20', 'CS-101'])
    for col in range(1, len(headers) + 1):
        ws.cell(row=2, column=col).fill = example_fill
        ws.cell(row=2, column=col).font = Font(italic=True, color='555555')

    _auto_width(ws)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="students_import_template.xlsx"'
    return response
