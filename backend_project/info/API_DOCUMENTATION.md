# API Documentation — Info App

**Base URL:** `http://127.0.0.1:8000/api/info`

---

## Общее

### Аутентификация
```
Authorization: Bearer <token>
```

### Права доступа
| Тип | Эндпоинты |
|-----|-----------|
| `Admin` | Все эндпоинты `/admin/*` |
| Любой авторизованный | `GET /schedules/*`, `GET /notifications/` |

```json
// 401 — токен не передан или недействителен
{ "error": "Токен не предоставлен" }

// 403 — недостаточно прав
{ "error": "Доступ запрещён. Требуются права администратора." }
```

---

## Расписание

### Объект расписания
```json
{
    "id": "schedules/AbCdEf123...",
    "day": 0,
    "day_name": "Monday",
    "start_time": "09:00",
    "end_time": "11:00",
    "classroom": 301,
    "group_name": "CS-101",
    "teacher_name": "John Smith",
    "book": 3,
    "created_at": "2025-01-15 10:30:00"
}
```

| Поле | Значения |
|------|----------|
| `day` | `0`=Monday, `1`=Tuesday, ..., `6`=Sunday |
| `classroom` | `301`, `303`, `306`, `307`, `308` |
| `book` | `1` – `8` |

---

### POST `/admin/schedules/create/`
Создать расписание для группы.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{
    "day": 1,
    "start_time": "09:00",
    "end_time": "11:00",
    "classroom": 301,
    "group_name": "CS-101",
    "teacher_name": "John Smith",
    "book": 3
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `day` | int | ✅ | 0–6 (Пн–Вс) |
| `start_time` | string | ✅ | Формат `HH:MM` |
| `end_time` | string | ✅ | Формат `HH:MM` |
| `classroom` | int | ✅ | 301, 303, 306, 307, 308 |
| `group_name` | string | ✅ | Имя группы |
| `teacher_name` | string | ✅ | ФИО преподавателя |
| `book` | int | ✅ | 1–8 |

**Успех — 201:**
```json
{
    "message": "Расписание создано",
    "schedule": { ... }
}
```

**Ошибки:**
```json
// 400 — обязательное поле не передано
{ "error": "Поле \"day\" обязательно" }

// 400 — день вне диапазона
{ "error": "Поле \"day\" должно быть от 0 (Monday) до 6 (Sunday)" }

// 400 — неверная аудитория
{ "error": "Неверная аудитория. Допустимые: [301, 303, 306, 307, 308]" }

// 400 — неверный формат времени
{ "error": "\"start_time\" должно быть в формате HH:MM" }

// 400 — end_time <= start_time
{ "error": "\"start_time\" должно быть раньше \"end_time\"" }

// 400 — у группы уже есть занятие в этот день
{ "error": "У группы уже есть занятие в Tuesday. Нельзя добавить два занятия в один день." }

// 400 — достигнут максимум дней
{ "error": "Группа уже имеет максимальное количество учебных дней (6)." }

// 404 — группа не найдена
{ "error": "Группа \"CS-999\" не найдена" }

// 404 — преподаватель не найден
{ "error": "Учитель \"Петров П.П.\" не найден" }
```

---

### GET `/admin/schedules/`
Список всех расписаний. Поддерживает фильтрацию.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Query параметры (необязательные, только один за раз):**
| Параметр | Пример |
|----------|--------|
| `group_name` | `?group_name=CS-101` |
| `teacher_name` | `?teacher_name=John Smith` |

**Успех — 200:**
```json
{
    "total": 15,
    "schedules": [ { ... } ]
}
```

---

### GET `/admin/schedules/<schedule_id>/`
Получить одно расписание.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{
    "schedule": { ... }
}
```

**Ошибки:**
```json
// 404
{ "error": "Расписание не найдено" }
```

---

### PATCH `/admin/schedules/<schedule_id>/edit/`
Изменить расписание. Все поля необязательные.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{
    "day": 2,
    "start_time": "10:00",
    "end_time": "12:00",
    "classroom": 303,
    "group_name": "CS-102",
    "teacher_name": "Jane Doe",
    "book": 5
}
```

**Успех — 200:**
```json
{
    "message": "Расписание обновлено",
    "updated_fields": ["day", "classroom"],
    "schedule": { ... }
}
```

**Ошибки:**
```json
// 400 — нет данных для обновления
{ "error": "Нет данных для обновления" }

// 400, 404 — те же что и при создании
```

---

### DELETE `/admin/schedules/<schedule_id>/delete/`
Удалить расписание.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{ "message": "Расписание удалено" }
```

**Ошибки:**
```json
// 404
{ "error": "Расписание не найдено" }
```

---

### GET `/schedules/all/`
Все расписания (для авторизованных пользователей). Отсортированы по дню и времени.

**Headers:**
```
Authorization: Bearer <token>
```

**Успех — 200:**
```json
{
    "total": 15,
    "schedules": [ { ... } ]
}
```

---

### GET `/schedules/group/<group_name>/`
Расписание конкретной группы. Отсортировано по дням недели.

**Headers:**
```
Authorization: Bearer <token>
```

**Пример:** `GET /api/info/schedules/group/CS-101/`

**Успех — 200:**
```json
{
    "group_name": "CS-101",
    "schedules": [ { ... } ]
}
```

**Ошибки:**
```json
// 404
{ "error": "Группа \"CS-999\" не найдена" }
```

---

## Уведомления

### Объект уведомления
```json
{
    "id": "notifications/XyZaBc...",
    "title_taj": "Огоҳнома",
    "title_rus": "Объявление",
    "title_eng": "Announcement",
    "title_kor": "공고",
    "content_taj": "Матн ...",
    "content_rus": "Текст ...",
    "content_eng": "Text ...",
    "content_kor": "내용 ...",
    "image_url": "https://drive.google.com/uc?id=...",
    "images": [
        { "file_id": "1AbCdEfG...", "url": "https://drive.google.com/uc?id=..." }
    ],
    "target_statuses": ["Student", "Teacher"],
    "created_at": "2025-01-15 10:30:00"
}
```

> Поля `title_*` и `content_*` — мультиязычные. `taj`=таджикский, `rus`=русский, `eng`=английский, `kor`=корейский.

---

### POST `/admin/notifications/create/`
Создать уведомление. После создания бэкенд автоматически:
1. Сохраняет уведомление в Firestore
2. Находит всех пользователей с указанными статусами
3. Отправляет FCM push-уведомление на их `device_token`

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Вариант A — JSON (без загрузки изображений):**
```
Content-Type: application/json
```
```json
{
    "title_rus": "Важное объявление",
    "title_eng": "Important announcement",
    "content_rus": "Занятия отменены",
    "content_eng": "Classes are cancelled",
    "target_statuses": ["Student", "Teacher"],
    "image_url": "https://example.com/banner.jpg"
}
```

**Вариант B — multipart/form-data (с загрузкой изображений):**

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `title_taj` | string | ❌ | Заголовок (таджикский) |
| `title_rus` | string | ❌ | Заголовок (русский) |
| `title_eng` | string | ❌ | Заголовок (английский) |
| `title_kor` | string | ❌ | Заголовок (корейский) |
| `content_taj` | string | ❌ | Текст (таджикский) |
| `content_rus` | string | ❌ | Текст (русский) |
| `content_eng` | string | ❌ | Текст (английский) |
| `content_kor` | string | ❌ | Текст (корейский) |
| `image_url` | string | ❌ | URL обложки |
| `images` | File[] | ❌ | JPEG/PNG/WEBP, до 2 МБ, максимум 10 |
| `target_statuses` | string[] | ✅ | Список статусов — `Student`, `Teacher`, `Admin`, `Guest` |

> Хотя бы одно поле `title_*` обязательно.

**Успех — 201:**
```json
{
    "message": "Уведомление создано",
    "notification": { ... }
}
```

**Ошибки:**
```json
// 400 — нет заголовка
{ "error": "Хотя бы одно поле заголовка обязательно (title_taj / title_rus / title_eng / title_kor)" }

// 400 — не указаны target_statuses
{ "error": "Поле \"target_statuses\" обязательно. Укажите хотя бы один статус." }

// 400 — недопустимый статус
{ "error": "Недопустимые статусы: [\"Unknown\"]. Допустимые: ['Admin', 'Guest', 'Student', 'Teacher']" }

// 400 — превышен лимит изображений
{ "error": "Максимум 10 изображений" }

// 400 — недопустимый формат изображения
{ "error": "Допустимые форматы изображений: JPEG, PNG, WEBP" }

// 400 — изображение слишком большое
{ "error": "Изображение слишком большое. Максимум 2 МБ" }

// 502 — ошибка загрузки
{ "error": "Ошибка загрузки изображения: ..." }
```

---

### GET `/admin/notifications/`
Список всех уведомлений. Отсортированы от новых к старым.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Query параметры (необязательные):**
| Параметр | Пример | Описание |
|----------|--------|----------|
| `status` | `?status=Student` | Фильтр по целевому статусу |

**Успех — 200:**
```json
{
    "total": 10,
    "notifications": [ { ... } ]
}
```

**Ошибки:**
```json
// 400 — недопустимый статус
{ "error": "Недопустимый статус: \"Unknown\". Допустимые: ['Admin', 'Guest', 'Student', 'Teacher']" }
```

---

### GET `/admin/notifications/<notif_id>/`
Получить одно уведомление.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{
    "notification": { ... }
}
```

**Ошибки:**
```json
// 404
{ "error": "Уведомление не найдено" }
```

---

### PATCH `/admin/notifications/<notif_id>/edit/`
Изменить уведомление. Все поля необязательные.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON или multipart/form-data):**
```json
{
    "title_rus": "Обновлённый заголовок",
    "content_rus": "Обновлённый текст",
    "target_statuses": ["Student"],
    "image_url": "https://example.com/new-banner.jpg"
}
```

> При передаче `images` (файлов) — старые изображения удаляются с Google Drive и заменяются новыми.

**Успех — 200:**
```json
{
    "message": "Уведомление обновлено",
    "updated_fields": ["title_rus", "content_rus"],
    "notification": { ... }
}
```

**Ошибки:**
```json
// 400 — нет данных
{ "error": "Нет данных для обновления" }

// 400 — недопустимый статус
{ "error": "Недопустимые статусы: [\"X\"]. Допустимые: ..." }

// 404
{ "error": "Уведомление не найдено" }
```

---

### DELETE `/admin/notifications/<notif_id>/delete/`
Удалить уведомление и все прикреплённые изображения с Google Drive.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{ "message": "Уведомление удалено" }
```

**Ошибки:**
```json
// 404
{ "error": "Уведомление не найдено" }
```

---

### GET `/notifications/`
Уведомления текущего пользователя. Фильтруются по его статусу. Отсортированы от новых к старым.

**Headers:**
```
Authorization: Bearer <token>
```

**Успех — 200:**
```json
{
    "total": 5,
    "notifications": [ { ... } ]
}
```

> Пользователь видит только уведомления, где его статус входит в `target_statuses`.

---

## FCM Push-уведомления

### Как подключить в мобильном приложении

**Шаг 1.** Получить FCM `device_token` через Firebase SDK.

**Шаг 2.** Передать токен при входе:
```json
POST /api/users/login/
{
    "username": "john_doe",
    "password": "MyPassword123",
    "device_token": "фкм_токен_устройства"
}
```

**Шаг 3.** Токен сохраняется в Firestore. При создании уведомления бэкенд автоматически находит все токены пользователей с нужными статусами и отправляет push каждому.

> Токен обновляется автоматически при каждом входе если он изменился.

---

## Коды ответов

| Код | Значение |
|-----|----------|
| 200 | Успех |
| 201 | Создан |
| 400 | Неверный запрос |
| 401 | Не авторизован |
| 403 | Доступ запрещён |
| 404 | Не найден |
| 502 | Ошибка внешнего сервиса (Google Drive / FCM) |

---

## Как проверить в Postman

### Расписание — создание
```
POST http://127.0.0.1:8000/api/info/admin/schedules/create/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
    "day": 0,
    "start_time": "09:00",
    "end_time": "11:00",
    "classroom": 301,
    "group_name": "CS-101",
    "teacher_name": "Иванов Иван",
    "book": 1
}
```

### Расписание группы
```
GET http://127.0.0.1:8000/api/info/schedules/group/CS-101/
Authorization: Bearer <token>
```

### Уведомление — создание с FCM
```
POST http://127.0.0.1:8000/api/info/admin/notifications/create/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
    "title_rus": "Тест",
    "content_rus": "Занятия отменены",
    "target_statuses": ["Student"]
}
```

### Мои уведомления
```
GET http://127.0.0.1:8000/api/info/notifications/
Authorization: Bearer <token>
```
