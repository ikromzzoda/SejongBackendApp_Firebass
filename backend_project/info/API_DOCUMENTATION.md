# API Documentation — Info App

**Base URL:** `http://127.0.0.1:8000/api/info`

---

## Аутентификация

```
Authorization: Bearer <token>
```

| Уровень доступа | Эндпоинты |
|-----------------|-----------|
| Admin | Все `/admin/*` |
| Любой авторизованный | `GET /schedules/*`, `GET /notifications/` |

```json
// 401 — токен не передан или недействителен
{ "error": "Токен не предоставлен" }

// 403 — недостаточно прав
{ "error": "Доступ запрещён. Требуются права администратора." }
```

---

## Обзор эндпоинтов

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| POST | `/admin/schedules/create/` | Admin | Создать расписание |
| GET | `/admin/schedules/` | Admin | Список всех расписаний |
| GET | `/admin/schedules/<id>/` | Admin | Получить расписание |
| PATCH | `/admin/schedules/<id>/edit/` | Admin | Редактировать расписание |
| DELETE | `/admin/schedules/<id>/delete/` | Admin | Удалить расписание |
| GET | `/schedules/all/` | Авторизованный | Все расписания |
| GET | `/schedules/group/<group_name>/` | Авторизованный | Расписание группы |
| POST | `/admin/notifications/create/` | Admin | Создать уведомление + FCM push |
| GET | `/admin/notifications/` | Admin | Список уведомлений |
| GET | `/admin/notifications/<id>/` | Admin | Получить уведомление |
| PATCH | `/admin/notifications/<id>/edit/` | Admin | Редактировать уведомление |
| DELETE | `/admin/notifications/<id>/delete/` | Admin | Удалить уведомление |
| GET | `/notifications/` | Авторизованный | Мои уведомления |

---

## Расписание

### Объект расписания

```json
{
    "id": "schedules/AbCdEf123",
    "day": 0,
    "day_name": "Monday",
    "start_time": "09:00",
    "end_time": "11:00",
    "classroom": 301,
    "group_name": "CS-101",
    "teacher_name": "Иванов Иван",
    "book": 3,
    "created_at": "2026-01-15 10:30:00"
}
```

| Поле | Допустимые значения |
|------|---------------------|
| `day` | `0`=Monday, `1`=Tuesday, `2`=Wednesday, `3`=Thursday, `4`=Friday, `5`=Saturday, `6`=Sunday |
| `classroom` | `301`, `303`, `306`, `307`, `308` |
| `book` | `1` – `8` |

---

### POST `/admin/schedules/create/`

Создать расписание для группы. В одной группе не может быть двух занятий в один день; максимум 6 учебных дней на группу.

**Body (JSON):**

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `day` | int | ✅ | 0–6 (Пн–Вс) |
| `start_time` | string | ✅ | Формат `HH:MM` |
| `end_time` | string | ✅ | Формат `HH:MM`, должно быть позже `start_time` |
| `classroom` | int | ✅ | 301, 303, 306, 307, 308 |
| `group_name` | string | ✅ | Название группы |
| `teacher_name` | string | ✅ | ФИО преподавателя |
| `book` | int | ✅ | 1–8 |

```json
// Запрос
{
    "day": 1,
    "start_time": "09:00",
    "end_time": "11:00",
    "classroom": 301,
    "group_name": "CS-101",
    "teacher_name": "Иванов Иван",
    "book": 3
}

// 201 — успех
{
    "message": "Расписание создано",
    "schedule": { ... }
}
```

**Ошибки:**

| Код | Описание | Ответ |
|-----|----------|-------|
| 400 | Обязательное поле не передано | `{"error": "Поле \"day\" обязательно"}` |
| 400 | Неверный день | `{"error": "Поле \"day\" должно быть от 0 (Monday) до 6 (Sunday)"}` |
| 400 | Неверная аудитория | `{"error": "Неверная аудитория. Допустимые: [301, 303, 306, 307, 308]"}` |
| 400 | Неверный формат времени | `{"error": "\"start_time\" должно быть в формате HH:MM"}` |
| 400 | start_time ≥ end_time | `{"error": "\"start_time\" должно быть раньше \"end_time\""}` |
| 400 | Занятие в этот день уже есть | `{"error": "У группы уже есть занятие в Tuesday. Нельзя добавить два занятия в один день."}` |
| 400 | Достигнут максимум дней | `{"error": "Группа уже имеет максимальное количество учебных дней (6)."}` |
| 404 | Группа не найдена | `{"error": "Группа \"CS-999\" не найдена"}` |
| 404 | Преподаватель не найден | `{"error": "Учитель \"Петров П.П.\" не найден"}` |

---

### GET `/admin/schedules/`

Список всех расписаний. Можно фильтровать по группе или преподавателю (только один параметр за раз).

**Query параметры (необязательные):**

| Параметр | Пример |
|----------|--------|
| `group_name` | `?group_name=CS-101` |
| `teacher_name` | `?teacher_name=Иванов Иван` |

```json
// 200 — успех
{
    "total": 15,
    "schedules": [ { ... } ]
}
```

---

### GET `/admin/schedules/<schedule_id>/`

Получить одно расписание по ID.

```json
// 200 — успех
{ "schedule": { ... } }

// 404
{ "error": "Расписание не найдено" }
```

---

### PATCH `/admin/schedules/<schedule_id>/edit/`

Изменить расписание. Передаются только изменяемые поля.

**Body (JSON, все поля необязательные):**

```json
{
    "day": 2,
    "start_time": "10:00",
    "end_time": "12:00",
    "classroom": 303,
    "group_name": "CS-102",
    "teacher_name": "Петрова Мария",
    "book": 5
}

// 200 — успех
{
    "message": "Расписание обновлено",
    "updated_fields": ["day", "classroom"],
    "schedule": { ... }
}
```

**Ошибки:**

| Код | Описание |
|-----|----------|
| 400 | Нет данных для обновления / неверные значения полей |
| 404 | Расписание / группа / преподаватель не найдены |

---

### DELETE `/admin/schedules/<schedule_id>/delete/`

Удалить расписание.

```json
// 200 — успех
{ "message": "Расписание удалено" }

// 404
{ "error": "Расписание не найдено" }
```

---

### GET `/schedules/all/`

Все расписания для авторизованного пользователя. Отсортированы по дню недели и времени начала.

```json
// 200 — успех
{
    "total": 15,
    "schedules": [ { ... } ]
}
```

---

### GET `/schedules/group/<group_name>/`

Расписание конкретной группы, отсортированное по дням недели.

**Пример:** `GET /api/info/schedules/group/CS-101/`

```json
// 200 — успех
{
    "group_name": "CS-101",
    "schedules": [ { ... } ]
}

// 404
{ "error": "Группа \"CS-999\" не найдена" }
```

---

## Уведомления

### Объект уведомления

```json
{
    "id": "notifications/XyZaBc",
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
        { "file_id": "1AbCdEfG", "url": "https://drive.google.com/uc?id=1AbCdEfG" }
    ],
    "target_statuses": ["Student", "Teacher"],
    "created_at": "2026-01-15 10:30:00"
}
```

> Поля `title_*` / `content_*` — мультиязычные: `taj`=таджикский, `rus`=русский, `eng`=английский, `kor`=корейский.  
> `image_url` — URL обложки (одно изображение).  
> `images` — дополнительные изображения, загруженные на Google Drive.  
> `target_statuses` — допустимые значения: `Guest`, `Student`, `Teacher`, `Admin`.

---

### POST `/admin/notifications/create/`

Создать уведомление. После сохранения бэкенд автоматически:
1. Находит `device_token` всех пользователей с указанными статусами
2. Отправляет FCM push-уведомление на каждый токен

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
    "image_url": "https://example.com/banner.jpg",
    "target_statuses": ["Student", "Teacher"]
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
| `images` | File[] | ❌ | JPEG / PNG / WEBP, до 2 МБ каждый, максимум 10 файлов |
| `target_statuses` | string[] | ✅ | `Guest`, `Student`, `Teacher`, `Admin` |

> Хотя бы одно поле `title_*` обязательно.

```json
// 201 — успех
{
    "message": "Уведомление создано",
    "notification": { ... }
}
```

**Ошибки:**

| Код | Описание | Ответ |
|-----|----------|-------|
| 400 | Нет ни одного заголовка | `{"error": "Хотя бы одно поле заголовка обязательно (title_taj / title_rus / title_eng / title_kor)"}` |
| 400 | `target_statuses` не передан | `{"error": "Поле \"target_statuses\" обязательно. Укажите хотя бы один статус."}` |
| 400 | Недопустимый статус | `{"error": "Недопустимые статусы: [\"Unknown\"]. Допустимые: ['Admin', 'Guest', 'Student', 'Teacher']"}` |
| 400 | Превышен лимит изображений | `{"error": "Максимум 10 изображений"}` |
| 400 | Недопустимый формат | `{"error": "Допустимые форматы изображений: JPEG, PNG, WEBP"}` |
| 400 | Изображение слишком большое | `{"error": "Изображение слишком большое. Максимум 2 МБ"}` |
| 502 | Ошибка загрузки на Google Drive | `{"error": "Ошибка загрузки изображения: ..."}` |

---

### GET `/admin/notifications/`

Список всех уведомлений, отсортированных от новых к старым.

**Query параметры (необязательные):**

| Параметр | Пример | Описание |
|----------|--------|----------|
| `status` | `?status=Student` | Фильтр по целевому статусу |

```json
// 200 — успех
{
    "total": 10,
    "notifications": [ { ... } ]
}

// 400 — недопустимый статус
{ "error": "Недопустимый статус: \"Unknown\". Допустимые: ['Admin', 'Guest', 'Student', 'Teacher']" }
```

---

### GET `/admin/notifications/<notif_id>/`

Получить одно уведомление по ID.

```json
// 200 — успех
{ "notification": { ... } }

// 404
{ "error": "Уведомление не найдено" }
```

---

### PATCH `/admin/notifications/<notif_id>/edit/`

Изменить уведомление. Передаются только изменяемые поля.

> При передаче новых `images` — старые изображения удаляются с Google Drive и заменяются новыми.

**Body (JSON или multipart/form-data, все поля необязательные):**

```json
{
    "title_rus": "Обновлённый заголовок",
    "content_rus": "Обновлённый текст",
    "image_url": "https://example.com/new-banner.jpg",
    "target_statuses": ["Student"]
}
```

```json
// 200 — успех
{
    "message": "Уведомление обновлено",
    "updated_fields": ["title_rus", "content_rus"],
    "notification": { ... }
}
```

**Ошибки:**

| Код | Описание |
|-----|----------|
| 400 | Нет данных для обновления / недопустимый статус / превышен лимит изображений |
| 404 | Уведомление не найдено |

---

### DELETE `/admin/notifications/<notif_id>/delete/`

Удалить уведомление и все прикреплённые изображения с Google Drive.

```json
// 200 — успех
{ "message": "Уведомление удалено" }

// 404
{ "error": "Уведомление не найдено" }
```

---

### GET `/notifications/`

Уведомления текущего пользователя. Возвращает только те, где статус пользователя входит в `target_statuses`. Отсортированы от новых к старым.

```json
// 200 — успех
{
    "total": 5,
    "notifications": [ { ... } ]
}
```

---

## FCM Push-уведомления

Бэкенд отправляет FCM push автоматически при создании уведомления (`POST /admin/notifications/create/`).

**Как подключить в мобильном приложении:**

**Шаг 1.** Получить FCM `device_token` через Firebase SDK на устройстве.

**Шаг 2.** Передать токен при входе:
```json
POST /api/users/login/
{
    "username": "john_doe",
    "password": "MyPassword123",
    "device_token": "fcm_token_устройства"
}
```

**Шаг 3.** Токен сохраняется в Firestore. При создании уведомления бэкенд находит все `device_token` пользователей с нужными `target_statuses` и отправляет push каждому.

> Токен обновляется автоматически при каждом входе.

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

## Примеры запросов (Postman)

### Создать расписание
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

### Расписание конкретной группы
```
GET http://127.0.0.1:8000/api/info/schedules/group/CS-101/
Authorization: Bearer <token>
```

### Создать уведомление (с FCM push всем студентам)
```
POST http://127.0.0.1:8000/api/info/admin/notifications/create/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
    "title_rus": "Занятия отменены",
    "title_eng": "Classes cancelled",
    "content_rus": "Занятия 23 июня отменяются",
    "target_statuses": ["Student"]
}
```

### Мои уведомления
```
GET http://127.0.0.1:8000/api/info/notifications/
Authorization: Bearer <token>
```
