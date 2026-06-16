import re
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from utils.decorators import admin_required, jwt_required
from utils.drive import upload_notification_image, delete_file
from utils.fcm import send_notification_to_statuses
from users.models import User
from groups.models import Group
from .models import Schedule, Notification


VALID_DAYS         = {0, 1, 2, 3, 4, 5, 6}
VALID_CLASSROOMS   = {301, 303, 306, 307, 308}
VALID_BOOKS        = set(range(1, 9))
TIME_RE            = re.compile(r'^\d{2}:\d{2}$')
DAY_NAMES          = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MAX_DAYS_PER_GROUP = 6

VALID_STATUSES    = {'Guest', 'Student', 'Teacher', 'Admin'}
ALLOWED_IMG_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMG_SIZE      = 2 * 1024 * 1024   # 2 МБ
MAX_NOTIF_IMAGES  = 10
NOTIF_LANG_FIELDS = (
    'title_taj', 'title_rus', 'title_eng', 'title_kor',
    'content_taj', 'content_rus', 'content_eng', 'content_kor',
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _schedule_dict(s, group_name='', teacher_name='') -> dict:
    day = s.day
    return {
        'id':           s.id,
        'day':          day,
        'day_name':     DAY_NAMES[day] if day is not None and 0 <= day <= 6 else '',
        'start_time':   s.start_time or '',
        'end_time':     s.end_time or '',
        'classroom':    s.classroom,
        'group_name':   group_name,
        'teacher_name': teacher_name,
        'book':         s.book,
        'created_at':   str(s.created_at) if s.created_at else '',
    }


def _build_caches():
    groups   = {g.id: g.name or '' for g in Group.collection.fetch(200)}
    teachers = {u.id: u.fullname or '' for u in User.collection.filter('status', '==', 'Teacher').fetch(200)}
    return groups, teachers


def _fetch_names(group_id, teacher_id):
    group_name = teacher_name = ''
    try:
        g = Group.collection.get(f'groups/{group_id}')
        if g:
            group_name = g.name or ''
    except Exception:
        pass
    try:
        t = User.collection.get(f'users/{teacher_id}')
        if t:
            teacher_name = t.fullname or ''
    except Exception:
        pass
    return group_name, teacher_name


def _lookup_group(name):
    found = list(Group.collection.filter('name', '==', name).fetch(1))
    return found[0] if found else None


def _lookup_teacher(name):
    found = [u for u in User.collection.filter('fullname', '==', name).fetch(5) if u.status == 'Teacher']
    return found[0] if found else None


def _validate_day(val):
    try:
        day = int(val)
    except (ValueError, TypeError):
        return None, 'Поле "day" должно быть числом (0-6)'
    if day not in VALID_DAYS:
        return None, 'Поле "day" должно быть от 0 (Monday) до 6 (Sunday)'
    return day, None


def _validate_classroom(val):
    try:
        classroom = int(val)
    except (ValueError, TypeError):
        return None, 'Поле "classroom" должно быть числом'
    if classroom not in VALID_CLASSROOMS:
        return None, f'Неверная аудитория. Допустимые: {sorted(VALID_CLASSROOMS)}'
    return classroom, None


def _validate_book(val):
    try:
        book = int(val)
    except (ValueError, TypeError):
        return None, 'Поле "book" должно быть числом (1-8)'
    if book not in VALID_BOOKS:
        return None, 'Поле "book" должно быть от 1 до 8'
    return book, None


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@admin_required
def admin_create_schedule(request):
    data = request.data

    for field in ('day', 'start_time', 'end_time', 'classroom', 'group_name', 'teacher_name', 'book'):
        if data.get(field) is None or str(data.get(field, '')).strip() == '':
            return Response({'error': f'Поле "{field}" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    day, err = _validate_day(data['day'])
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

    classroom, err = _validate_classroom(data['classroom'])
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

    book, err = _validate_book(data['book'])
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

    start_time = str(data['start_time']).strip()
    end_time   = str(data['end_time']).strip()
    if not TIME_RE.match(start_time):
        return Response({'error': '"start_time" должно быть в формате HH:MM'}, status=status.HTTP_400_BAD_REQUEST)
    if not TIME_RE.match(end_time):
        return Response({'error': '"end_time" должно быть в формате HH:MM'}, status=status.HTTP_400_BAD_REQUEST)
    if start_time >= end_time:
        return Response({'error': '"start_time" должно быть раньше "end_time"'}, status=status.HTTP_400_BAD_REQUEST)

    group = _lookup_group(str(data['group_name']).strip())
    if not group:
        return Response({'error': f'Группа "{data["group_name"]}" не найдена'}, status=status.HTTP_404_NOT_FOUND)

    teacher = _lookup_teacher(str(data['teacher_name']).strip())
    if not teacher:
        return Response({'error': f'Учитель "{data["teacher_name"]}" не найден'}, status=status.HTTP_404_NOT_FOUND)

    existing_days = [s.day for s in Schedule.collection.filter('group_id', '==', group.id).fetch(7)]

    if day in existing_days:
        return Response(
            {'error': f'У группы уже есть занятие в {DAY_NAMES[day]}. Нельзя добавить два занятия в один день.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(existing_days) >= MAX_DAYS_PER_GROUP:
        return Response(
            {'error': f'Группа уже имеет максимальное количество учебных дней ({MAX_DAYS_PER_GROUP}).'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    sched            = Schedule()
    sched.day        = day
    sched.start_time = start_time
    sched.end_time   = end_time
    sched.classroom  = classroom
    sched.group_id   = group.id
    sched.teacher_id = teacher.id
    sched.book       = book
    sched.save()

    return Response(
        {'message': 'Расписание создано', 'schedule': _schedule_dict(sched, group.name, teacher.fullname)},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@admin_required
def admin_list_schedules(request):
    group_name   = request.GET.get('group_name', '').strip()
    teacher_name = request.GET.get('teacher_name', '').strip()

    if group_name:
        group = _lookup_group(group_name)
        if not group:
            return Response({'error': f'Группа "{group_name}" не найдена'}, status=status.HTTP_404_NOT_FOUND)
        schedules = list(Schedule.collection.filter('group_id', '==', group.id).fetch(100))
    elif teacher_name:
        teacher = _lookup_teacher(teacher_name)
        if not teacher:
            return Response({'error': f'Учитель "{teacher_name}" не найден'}, status=status.HTTP_404_NOT_FOUND)
        schedules = list(Schedule.collection.filter('teacher_id', '==', teacher.id).fetch(100))
    else:
        schedules = list(Schedule.collection.fetch(500))

    groups_cache, teachers_cache = _build_caches()
    return Response({
        'total':     len(schedules),
        'schedules': [
            _schedule_dict(s, groups_cache.get(s.group_id, ''), teachers_cache.get(s.teacher_id, ''))
            for s in schedules
        ],
    })


@api_view(['GET'])
@admin_required
def admin_get_schedule(request, schedule_id):
    try:
        sched = Schedule.collection.get(f'schedules/{schedule_id}')
    except Exception:
        sched = None
    if not sched:
        return Response({'error': 'Расписание не найдено'}, status=status.HTTP_404_NOT_FOUND)
    group_name, teacher_name = _fetch_names(sched.group_id, sched.teacher_id)
    return Response({'schedule': _schedule_dict(sched, group_name, teacher_name)})


@api_view(['PATCH'])
@admin_required
def admin_edit_schedule(request, schedule_id):
    try:
        sched = Schedule.collection.get(f'schedules/{schedule_id}')
    except Exception:
        sched = None
    if not sched:
        return Response({'error': 'Расписание не найдено'}, status=status.HTTP_404_NOT_FOUND)

    data           = request.data
    updated_fields = []

    if 'group_name' in data:
        group = _lookup_group(str(data['group_name']).strip())
        if not group:
            return Response({'error': f'Группа "{data["group_name"]}" не найдена'}, status=status.HTTP_404_NOT_FOUND)
        sched.group_id = group.id
        updated_fields.append('group_name')

    if 'day' in data:
        day, err = _validate_day(data['day'])
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
        for s in Schedule.collection.filter('group_id', '==', sched.group_id).fetch(7):
            if s.id != schedule_id and s.day == day:
                return Response(
                    {'error': f'У группы уже есть занятие в {DAY_NAMES[day]}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        sched.day = day
        updated_fields.append('day')

    if 'classroom' in data:
        classroom, err = _validate_classroom(data['classroom'])
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
        sched.classroom = classroom
        updated_fields.append('classroom')

    if 'book' in data:
        book, err = _validate_book(data['book'])
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
        sched.book = book
        updated_fields.append('book')

    if 'start_time' in data:
        start_time = str(data['start_time']).strip()
        if not TIME_RE.match(start_time):
            return Response({'error': '"start_time" должно быть в формате HH:MM'}, status=status.HTTP_400_BAD_REQUEST)
        sched.start_time = start_time
        updated_fields.append('start_time')

    if 'end_time' in data:
        end_time = str(data['end_time']).strip()
        if not TIME_RE.match(end_time):
            return Response({'error': '"end_time" должно быть в формате HH:MM'}, status=status.HTTP_400_BAD_REQUEST)
        sched.end_time = end_time
        updated_fields.append('end_time')

    if sched.start_time and sched.end_time and sched.start_time >= sched.end_time:
        return Response({'error': '"start_time" должно быть раньше "end_time"'}, status=status.HTTP_400_BAD_REQUEST)

    if 'teacher_name' in data:
        teacher = _lookup_teacher(str(data['teacher_name']).strip())
        if not teacher:
            return Response({'error': f'Учитель "{data["teacher_name"]}" не найден'}, status=status.HTTP_404_NOT_FOUND)
        sched.teacher_id = teacher.id
        updated_fields.append('teacher_name')

    if not updated_fields:
        return Response({'message': 'Нет данных для обновления'}, status=status.HTTP_400_BAD_REQUEST)

    sched.update()
    group_name, teacher_name = _fetch_names(sched.group_id, sched.teacher_id)
    return Response({
        'message':        'Расписание обновлено',
        'updated_fields': updated_fields,
        'schedule':       _schedule_dict(sched, group_name, teacher_name),
    })


@api_view(['DELETE'])
@admin_required
def admin_delete_schedule(request, schedule_id):
    try:
        sched = Schedule.collection.get(f'schedules/{schedule_id}')
    except Exception:
        sched = None
    if not sched:
        return Response({'error': 'Расписание не найдено'}, status=status.HTTP_404_NOT_FOUND)
    Schedule.collection.delete(f'schedules/{schedule_id}')
    return Response({'message': 'Расписание удалено'})


# ---------------------------------------------------------------------------
# Public / authenticated endpoints
# ---------------------------------------------------------------------------

@api_view(['GET'])
@jwt_required
def get_all_schedules(request):
    schedules = list(Schedule.collection.fetch(500))
    schedules.sort(key=lambda s: (s.day if s.day is not None else 7, s.start_time or ''))
    groups_cache, teachers_cache = _build_caches()
    return Response({
        'total':     len(schedules),
        'schedules': [
            _schedule_dict(s, groups_cache.get(s.group_id, ''), teachers_cache.get(s.teacher_id, ''))
            for s in schedules
        ],
    })


@api_view(['GET'])
@jwt_required
def get_group_schedule(request, group_name):
    group = _lookup_group(group_name)
    if not group:
        return Response({'error': f'Группа "{group_name}" не найдена'}, status=status.HTTP_404_NOT_FOUND)

    schedules = list(Schedule.collection.filter('group_id', '==', group.id).fetch(7))
    schedules.sort(key=lambda s: s.day if s.day is not None else 7)

    teachers_cache = {u.id: u.fullname or '' for u in User.collection.filter('status', '==', 'Teacher').fetch(200)}
    return Response({
        'group_name': group.name or '',
        'schedules':  [
            _schedule_dict(s, group.name or '', teachers_cache.get(s.teacher_id, ''))
            for s in schedules
        ],
    })


# ---------------------------------------------------------------------------
# Notifications — helpers
# ---------------------------------------------------------------------------

def _notif_dict(n) -> dict:
    return {
        'id':              n.id,
        'title_taj':       n.title_taj or '',
        'title_rus':       n.title_rus or '',
        'title_eng':       n.title_eng or '',
        'title_kor':       n.title_kor or '',
        'content_taj':     n.content_taj or '',
        'content_rus':     n.content_rus or '',
        'content_eng':     n.content_eng or '',
        'content_kor':     n.content_kor or '',
        'image_url':       n.image_url or '',
        'images':          n.images or [],
        'target_statuses': n.target_statuses or [],
        'created_at':      str(n.created_at) if n.created_at else '',
    }


def _parse_statuses(data) -> list:
    """Extracts target_statuses from both JSON (dict) and multipart (QueryDict) request data."""
    if hasattr(data, 'getlist'):
        return data.getlist('target_statuses')
    raw = data.get('target_statuses', [])
    return [raw] if isinstance(raw, str) else (list(raw) if isinstance(raw, list) else [])


def _upload_notif_images(files) -> tuple[list, 'Response | None']:
    uploaded = []
    for f in files:
        if f.content_type not in ALLOWED_IMG_TYPES:
            for item in uploaded:
                delete_file(item['file_id'])
            return [], Response(
                {'error': 'Допустимые форматы изображений: JPEG, PNG, WEBP'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if f.size > MAX_IMG_SIZE:
            for item in uploaded:
                delete_file(item['file_id'])
            return [], Response(
                {'error': 'Изображение слишком большое. Максимум 2 МБ'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ext = f.name.rsplit('.', 1)[-1] if '.' in f.name else 'jpg'
        try:
            file_id, url = upload_notification_image(
                f, f'notification_{len(uploaded)}.{ext}', f.content_type
            )
        except Exception as e:
            for item in uploaded:
                delete_file(item['file_id'])
            return [], Response(
                {'error': f'Ошибка загрузки изображения: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        uploaded.append({'file_id': file_id, 'url': url})
    return uploaded, None


# ---------------------------------------------------------------------------
# Notifications — Admin endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@admin_required
def admin_create_notification(request):
    data = request.data

    if not any(str(data.get(f'title_{lang}') or '').strip() for lang in ('taj', 'rus', 'eng', 'kor')):
        return Response(
            {'error': 'Хотя бы одно поле заголовка обязательно (title_taj / title_rus / title_eng / title_kor)'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    raw_statuses = _parse_statuses(data)
    if not raw_statuses:
        return Response(
            {'error': 'Поле "target_statuses" обязательно. Укажите хотя бы один статус.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    invalid = [s for s in raw_statuses if s not in VALID_STATUSES]
    if invalid:
        return Response(
            {'error': f'Недопустимые статусы: {invalid}. Допустимые: {sorted(VALID_STATUSES)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_files = request.FILES.getlist('images')
    if len(image_files) > MAX_NOTIF_IMAGES:
        return Response(
            {'error': f'Максимум {MAX_NOTIF_IMAGES} изображений'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    images, err = _upload_notif_images(image_files)
    if err:
        return err

    notif = Notification()
    for field in NOTIF_LANG_FIELDS:
        setattr(notif, field, str(data.get(field) or '').strip())
    notif.image_url       = str(data.get('image_url') or '').strip()
    notif.images          = images
    notif.target_statuses = list(dict.fromkeys(raw_statuses))  # deduplicate, preserve order
    notif.save()

    title = (notif.title_rus or notif.title_eng or notif.title_taj or notif.title_kor or 'Уведомление')
    body  = (notif.content_rus or notif.content_eng or notif.content_taj or notif.content_kor or '')
    send_notification_to_statuses(notif.target_statuses, title, body)

    return Response(
        {'message': 'Уведомление создано', 'notification': _notif_dict(notif)},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@admin_required
def admin_list_notifications(request):
    filter_status = request.GET.get('status', '').strip()
    if filter_status:
        if filter_status not in VALID_STATUSES:
            return Response(
                {'error': f'Недопустимый статус: "{filter_status}". Допустимые: {sorted(VALID_STATUSES)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notifications = list(
            Notification.collection.filter('target_statuses', 'array_contains', filter_status).fetch(500)
        )
    else:
        notifications = list(Notification.collection.fetch(500))

    notifications.sort(key=lambda n: str(n.created_at or ''), reverse=True)
    return Response({
        'total':         len(notifications),
        'notifications': [_notif_dict(n) for n in notifications],
    })


@api_view(['GET'])
@admin_required
def admin_get_notification(request, notif_id):
    try:
        notif = Notification.collection.get(f'notifications/{notif_id}')
    except Exception:
        notif = None
    if not notif:
        return Response({'error': 'Уведомление не найдено'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'notification': _notif_dict(notif)})


@api_view(['PATCH'])
@admin_required
def admin_edit_notification(request, notif_id):
    try:
        notif = Notification.collection.get(f'notifications/{notif_id}')
    except Exception:
        notif = None
    if not notif:
        return Response({'error': 'Уведомление не найдено'}, status=status.HTTP_404_NOT_FOUND)

    data           = request.data
    updated_fields = []

    for field in NOTIF_LANG_FIELDS:
        if field in data:
            setattr(notif, field, str(data[field] or '').strip())
            updated_fields.append(field)

    if 'image_url' in data:
        notif.image_url = str(data['image_url'] or '').strip()
        updated_fields.append('image_url')

    raw_statuses = _parse_statuses(data)
    if raw_statuses:
        invalid = [s for s in raw_statuses if s not in VALID_STATUSES]
        if invalid:
            return Response(
                {'error': f'Недопустимые статусы: {invalid}. Допустимые: {sorted(VALID_STATUSES)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notif.target_statuses = list(dict.fromkeys(raw_statuses))
        updated_fields.append('target_statuses')

    image_files = request.FILES.getlist('images')
    if image_files:
        if len(image_files) > MAX_NOTIF_IMAGES:
            return Response(
                {'error': f'Максимум {MAX_NOTIF_IMAGES} изображений'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for item in (notif.images or []):
            delete_file(item.get('file_id', ''))
        new_images, err = _upload_notif_images(image_files)
        if err:
            return err
        notif.images = new_images
        updated_fields.append('images')

    if not updated_fields:
        return Response({'message': 'Нет данных для обновления'}, status=status.HTTP_400_BAD_REQUEST)

    notif.update()
    return Response({
        'message':        'Уведомление обновлено',
        'updated_fields': updated_fields,
        'notification':   _notif_dict(notif),
    })


@api_view(['DELETE'])
@admin_required
def admin_delete_notification(request, notif_id):
    try:
        notif = Notification.collection.get(f'notifications/{notif_id}')
    except Exception:
        notif = None
    if not notif:
        return Response({'error': 'Уведомление не найдено'}, status=status.HTTP_404_NOT_FOUND)

    for item in (notif.images or []):
        delete_file(item.get('file_id', ''))
    Notification.collection.delete(f'notifications/{notif_id}')
    return Response({'message': 'Уведомление удалено'})


# ---------------------------------------------------------------------------
# Notifications — Authenticated user endpoint
# ---------------------------------------------------------------------------

@api_view(['GET'])
@jwt_required
def get_my_notifications(request):
    user_status = request.user_payload.get('status', '')
    if not user_status:
        return Response({'error': 'Статус пользователя не определён'}, status=status.HTTP_400_BAD_REQUEST)

    notifications = list(
        Notification.collection.filter('target_statuses', 'array_contains', user_status).fetch(200)
    )
    notifications.sort(key=lambda n: str(n.created_at or ''), reverse=True)
    return Response({
        'total':         len(notifications),
        'notifications': [_notif_dict(n) for n in notifications],
    })
