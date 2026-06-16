# Info App — API Documentation

Base URL: `http://127.0.0.1:8000/api/info`

---

## Authentication

All endpoints require a JWT token in the `Authorization` header:

```
Authorization: Bearer <token>
```

- **Admin** endpoints require `status = "Admin"` in the token.
- **JWT** endpoints require any valid token (Student, Teacher, Admin).

---

## Endpoints Overview

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/admin/schedules/create/` | Admin | Create schedule entry |
| GET | `/admin/schedules/` | Admin | List all schedules (with filters) |
| GET | `/admin/schedules/<id>/` | Admin | Get single schedule |
| PATCH | `/admin/schedules/<id>/edit/` | Admin | Edit schedule entry |
| DELETE | `/admin/schedules/<id>/delete/` | Admin | Delete schedule entry |
| GET | `/schedules/all/` | JWT | All schedules sorted by day & time |
| GET | `/schedules/group/<group_name>/` | JWT | Schedule for a specific group |
| POST | `/admin/notifications/create/` | Admin | Create notification + send FCM push |
| GET | `/admin/notifications/` | Admin | List all notifications (with filter) |
| GET | `/admin/notifications/<id>/` | Admin | Get single notification |
| PATCH | `/admin/notifications/<id>/edit/` | Admin | Edit notification |
| DELETE | `/admin/notifications/<id>/delete/` | Admin | Delete notification |
| GET | `/notifications/` | JWT | My notifications (filtered by user status) |

---

## Field Reference

| Field | Type | Values |
|-------|------|--------|
| `day` | int | `0`=Monday, `1`=Tuesday, `2`=Wednesday, `3`=Thursday, `4`=Friday, `5`=Saturday, `6`=Sunday |
| `start_time` | string | `"HH:MM"` e.g. `"09:00"` |
| `end_time` | string | `"HH:MM"` e.g. `"10:30"` |
| `classroom` | int | `301`, `303`, `306`, `307`, `308` |
| `group_name` | string | Exact group name from the database |
| `teacher_name` | string | Exact teacher fullname from the database |
| `book` | int | `1` – `8` |

---

---

# Admin Endpoints

---

## 1. Create Schedule

**POST** `/api/info/admin/schedules/create/`

**Auth:** Admin

### Request Body
```json
{
    "day": 1,
    "start_time": "09:00",
    "end_time": "10:30",
    "classroom": 301,
    "group_name": "Группа A",
    "teacher_name": "Иван Иванов",
    "book": 2
}
```

### Success Response — `201 Created`
```json
{
    "message": "Расписание создано",
    "schedule": {
        "id": "RdhA38z1B38KsLMhKyex",
        "day": 1,
        "day_name": "Tuesday",
        "start_time": "09:00",
        "end_time": "10:30",
        "classroom": 301,
        "group_name": "Группа A",
        "teacher_name": "Иван Иванов",
        "book": 2,
        "created_at": "2026-06-14 06:30:04.955000+00:00"
    }
}
```

### Error Responses

**400** — Missing required field:
```json
{ "error": "Поле \"group_name\" обязательно" }
```

**400** — Invalid day:
```json
{ "error": "Поле \"day\" должно быть от 0 (Monday) до 6 (Sunday)" }
```

**400** — Invalid classroom:
```json
{ "error": "Неверная аудитория. Допустимые: [301, 303, 306, 307, 308]" }
```

**400** — Invalid book:
```json
{ "error": "Поле \"book\" должно быть от 1 до 8" }
```

**400** — Invalid time format:
```json
{ "error": "\"start_time\" должно быть в формате HH:MM" }
```

**400** — start_time >= end_time:
```json
{ "error": "\"start_time\" должно быть раньше \"end_time\"" }
```

**400** — Group already has a lesson on this day:
```json
{ "error": "У группы уже есть занятие в Tuesday. Нельзя добавить два занятия в один день." }
```

**400** — Group already has 6 days:
```json
{ "error": "Группа уже имеет максимальное количество учебных дней (6)." }
```

**404** — Group not found:
```json
{ "error": "Группа \"Группа A\" не найдена" }
```

**404** — Teacher not found:
```json
{ "error": "Учитель \"Иван Иванов\" не найден" }
```

---

## 2. List All Schedules (Admin)

**GET** `/api/info/admin/schedules/`

**Auth:** Admin

### Query Parameters (all optional)

| Param | Type | Description |
|-------|------|-------------|
| `group_name` | string | Filter by group name |
| `teacher_name` | string | Filter by teacher fullname |

### Examples
```
GET /api/info/admin/schedules/
GET /api/info/admin/schedules/?group_name=Группа A
GET /api/info/admin/schedules/?teacher_name=Иван Иванов
```

### Success Response — `200 OK`
```json
{
    "total": 3,
    "schedules": [
        {
            "id": "RdhA38z1B38KsLMhKyex",
            "day": 0,
            "day_name": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "classroom": 301,
            "group_name": "Группа A",
            "teacher_name": "Иван Иванов",
            "book": 1,
            "created_at": "2026-06-14 06:30:04.955000+00:00"
        },
        {
            "id": "Xp9Kz2mN7qR4wTyVcLsa",
            "day": 2,
            "day_name": "Wednesday",
            "start_time": "11:00",
            "end_time": "12:30",
            "classroom": 303,
            "group_name": "Группа A",
            "teacher_name": "Иван Иванов",
            "book": 1,
            "created_at": "2026-06-14 07:10:22.100000+00:00"
        }
    ]
}
```

### Error Responses

**404** — Group not found (when filtering by group_name):
```json
{ "error": "Группа \"Группа X\" не найдена" }
```

**404** — Teacher not found (when filtering by teacher_name):
```json
{ "error": "Учитель \"Неизвестный\" не найден" }
```

---

## 3. Get Single Schedule

**GET** `/api/info/admin/schedules/<schedule_id>/`

**Auth:** Admin

### Example
```
GET /api/info/admin/schedules/RdhA38z1B38KsLMhKyex/
```

### Success Response — `200 OK`
```json
{
    "schedule": {
        "id": "RdhA38z1B38KsLMhKyex",
        "day": 1,
        "day_name": "Tuesday",
        "start_time": "09:00",
        "end_time": "10:30",
        "classroom": 301,
        "group_name": "Группа A",
        "teacher_name": "Иван Иванов",
        "book": 2,
        "created_at": "2026-06-14 06:30:04.955000+00:00"
    }
}
```

### Error Responses

**404** — Schedule not found:
```json
{ "error": "Расписание не найдено" }
```

---

## 4. Edit Schedule

**PATCH** `/api/info/admin/schedules/<schedule_id>/edit/`

**Auth:** Admin

All fields are **optional** — send only what you want to update.

### Request Body
```json
{
    "day": 3,
    "start_time": "10:00",
    "end_time": "11:30",
    "classroom": 306,
    "group_name": "Группа B",
    "teacher_name": "Анна Смирнова",
    "book": 4
}
```

### Success Response — `200 OK`
```json
{
    "message": "Расписание обновлено",
    "updated_fields": ["day", "start_time", "classroom"],
    "schedule": {
        "id": "RdhA38z1B38KsLMhKyex",
        "day": 3,
        "day_name": "Thursday",
        "start_time": "10:00",
        "end_time": "10:30",
        "classroom": 306,
        "group_name": "Группа A",
        "teacher_name": "Иван Иванов",
        "book": 2,
        "created_at": "2026-06-14 06:30:04.955000+00:00"
    }
}
```

### Error Responses

**400** — No fields sent:
```json
{ "message": "Нет данных для обновления" }
```

**400** — Duplicate day for the same group:
```json
{ "error": "У группы уже есть занятие в Thursday" }
```

**400** — Invalid values (same as create endpoint)

**404** — Schedule not found:
```json
{ "error": "Расписание не найдено" }
```

**404** — Group / Teacher not found (same as create endpoint)

---

## 5. Delete Schedule

**DELETE** `/api/info/admin/schedules/<schedule_id>/delete/`

**Auth:** Admin

### Example
```
DELETE /api/info/admin/schedules/RdhA38z1B38KsLMhKyex/delete/
```

### Success Response — `200 OK`
```json
{ "message": "Расписание удалено" }
```

### Error Responses

**404** — Schedule not found:
```json
{ "error": "Расписание не найдено" }
```

---

---

# Public / Authenticated Endpoints

---

## 6. All Schedules (Sorted)

**GET** `/api/info/schedules/all/`

**Auth:** JWT (any role)

Returns all schedules for all groups, sorted by day (Monday → Sunday) then by `start_time`.

### Success Response — `200 OK`
```json
{
    "total": 5,
    "schedules": [
        {
            "id": "abc123",
            "day": 0,
            "day_name": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "classroom": 301,
            "group_name": "Группа A",
            "teacher_name": "Иван Иванов",
            "book": 1,
            "created_at": "2026-06-14 06:30:04.955000+00:00"
        },
        {
            "id": "def456",
            "day": 0,
            "day_name": "Monday",
            "start_time": "11:00",
            "end_time": "12:30",
            "classroom": 303,
            "group_name": "Группа B",
            "teacher_name": "Анна Смирнова",
            "book": 3,
            "created_at": "2026-06-14 07:00:00.000000+00:00"
        },
        {
            "id": "ghi789",
            "day": 2,
            "day_name": "Wednesday",
            "start_time": "09:00",
            "end_time": "10:30",
            "classroom": 306,
            "group_name": "Группа A",
            "teacher_name": "Иван Иванов",
            "book": 1,
            "created_at": "2026-06-14 07:10:00.000000+00:00"
        }
    ]
}
```

---

## 7. Schedule by Group Name

**GET** `/api/info/schedules/group/<group_name>/`

**Auth:** JWT (any role)

Returns all schedule entries for the given group, sorted by day (Monday → Sunday).

### Example
```
GET /api/info/schedules/group/Группа A/
```

> If the group name contains spaces, they will be URL-encoded automatically (e.g. `Группа%20A`). This is handled automatically by Postman and most HTTP clients.

### Success Response — `200 OK`
```json
{
    "group_name": "Группа A",
    "schedules": [
        {
            "id": "abc123",
            "day": 0,
            "day_name": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "classroom": 301,
            "group_name": "Группа A",
            "teacher_name": "Иван Иванов",
            "book": 1,
            "created_at": "2026-06-14 06:30:04.955000+00:00"
        },
        {
            "id": "ghi789",
            "day": 2,
            "day_name": "Wednesday",
            "start_time": "09:00",
            "end_time": "10:30",
            "classroom": 306,
            "group_name": "Группа A",
            "teacher_name": "Иван Иванов",
            "book": 1,
            "created_at": "2026-06-14 07:10:00.000000+00:00"
        }
    ]
}
```

### Error Responses

**404** — Group not found:
```json
{ "error": "Группа \"Группа X\" не найдена" }
```

---

---

---

---

# Notifications

> **FCM Push:** When a notification is created, the server automatically sends a Firebase Cloud Messaging push to all devices subscribed to the relevant topics (`status_Student`, `status_Teacher`, etc.). The frontend must subscribe to its topic after login using the `fcm_topic` field returned by `/api/users/login/`.

---

## 8. Create Notification

**POST** `/api/info/admin/notifications/create/`

**Auth:** Admin
**Content-Type:** `multipart/form-data`

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title_taj` | string | * | Title in Tajik |
| `title_rus` | string | * | Title in Russian |
| `title_eng` | string | * | Title in English |
| `title_kor` | string | * | Title in Korean |
| `content_taj` | string | — | Content in Tajik |
| `content_rus` | string | — | Content in Russian |
| `content_eng` | string | — | Content in English |
| `content_kor` | string | — | Content in Korean |
| `image_url` | string | — | Single image URL (external link, optional) |
| `images` | file[] | — | Images (JPEG/PNG/WEBP, max 2 MB each, max 10 files) |
| `target_statuses` | string[] | **Yes** | Who receives it: `Guest`, `Student`, `Teacher`, `Admin` |

> \* At least one title field is required (`title_taj`, `title_rus`, `title_eng`, or `title_kor`).
> For multiple `target_statuses` in Postman — add multiple rows with the same key name.

### Request Example (Postman form-data)

```
title_rus       = Важное объявление
content_rus     = Занятия перенесены на пятницу
target_statuses = Student
target_statuses = Teacher
images          = <file: photo.jpg>
```

### Success Response — `201 Created`

```json
{
    "message": "Уведомление создано",
    "notification": {
        "id": "abc123",
        "title_taj": "",
        "title_rus": "Важное объявление",
        "title_eng": "",
        "title_kor": "",
        "content_taj": "",
        "content_rus": "Занятия перенесены на пятницу",
        "content_eng": "",
        "content_kor": "",
        "image_url": "",
        "images": [
            {
                "file_id": "1A2B3C4D",
                "url": "https://drive.google.com/uc?id=1A2B3C4D"
            }
        ],
        "target_statuses": ["Student", "Teacher"],
        "created_at": "2026-06-16 10:30:00+00:00"
    }
}
```

> After save, FCM push is sent to topics `status_Student` and `status_Teacher` automatically.

### Error Responses

| Status | Condition | Message |
|--------|-----------|---------|
| `400` | No title provided | `"Хотя бы одно поле заголовка обязательно ..."` |
| `400` | `target_statuses` missing | `"Поле \"target_statuses\" обязательно. Укажите хотя бы один статус."` |
| `400` | Invalid status value | `"Недопустимые статусы: [...]. Допустимые: ..."` |
| `400` | More than 10 images | `"Максимум 10 изображений"` |
| `400` | Wrong image format | `"Допустимые форматы изображений: JPEG, PNG, WEBP"` |
| `400` | Image too large | `"Изображение слишком большое. Максимум 2 МБ"` |
| `502` | Google Drive error | `"Ошибка загрузки изображения: ..."` |

---

## 9. List All Notifications (Admin)

**GET** `/api/info/admin/notifications/`

**Auth:** Admin

Returns all notifications sorted by `created_at` descending (newest first).

### Query Parameters (optional)

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by target status: `Guest`, `Student`, `Teacher`, `Admin` |

### Examples

```
GET /api/info/admin/notifications/
GET /api/info/admin/notifications/?status=Student
```

### Success Response — `200 OK`

```json
{
    "total": 2,
    "notifications": [
        {
            "id": "abc123",
            "title_taj": "",
            "title_rus": "Важное объявление",
            "title_eng": "",
            "title_kor": "",
            "content_taj": "",
            "content_rus": "Занятия перенесены на пятницу",
            "content_eng": "",
            "content_kor": "",
            "image_url": "",
            "images": [
                {
                    "file_id": "1A2B3C4D",
                    "url": "https://drive.google.com/uc?id=1A2B3C4D"
                }
            ],
            "target_statuses": ["Student", "Teacher"],
            "created_at": "2026-06-16 10:30:00+00:00"
        }
    ]
}
```

### Error Responses

| Status | Condition | Message |
|--------|-----------|---------|
| `400` | Invalid status filter | `"Недопустимый статус: \"X\". Допустимые: ..."` |

---

## 10. Get Single Notification (Admin)

**GET** `/api/info/admin/notifications/<notif_id>/`

**Auth:** Admin

### Success Response — `200 OK`

```json
{
    "notification": {
        "id": "abc123",
        "title_rus": "Важное объявление",
        "content_rus": "Занятия перенесены на пятницу",
        "image_url": "",
        "images": [],
        "target_statuses": ["Student"],
        "created_at": "2026-06-16 10:30:00+00:00"
    }
}
```

### Error Responses

**404** — Not found:
```json
{ "error": "Уведомление не найдено" }
```

---

## 11. Edit Notification

**PATCH** `/api/info/admin/notifications/<notif_id>/edit/`

**Auth:** Admin
**Content-Type:** `multipart/form-data`

Send only the fields you want to update.

> **Note on images:** If `images` is provided, **all previous images are deleted** from Google Drive and replaced with the new ones. To keep existing images, do not send the `images` field.

### Request Example

```
title_rus       = Обновлённый заголовок
target_statuses = Admin
images          = <file: new_photo.jpg>
```

### Success Response — `200 OK`

```json
{
    "message": "Уведомление обновлено",
    "updated_fields": ["title_rus", "target_statuses", "images"],
    "notification": {
        "id": "abc123",
        "title_rus": "Обновлённый заголовок",
        "target_statuses": ["Admin"],
        "images": [
            {
                "file_id": "9X8Y7Z",
                "url": "https://drive.google.com/uc?id=9X8Y7Z"
            }
        ],
        "created_at": "2026-06-16 10:30:00+00:00"
    }
}
```

### Error Responses

| Status | Condition | Message |
|--------|-----------|---------|
| `400` | Nothing to update | `"Нет данных для обновления"` |
| `400` | Invalid status value | `"Недопустимые статусы: [...]"` |
| `404` | Not found | `"Уведомление не найдено"` |

---

## 12. Delete Notification

**DELETE** `/api/info/admin/notifications/<notif_id>/delete/`

**Auth:** Admin

Deletes the notification and removes all associated images from Google Drive.

### Success Response — `200 OK`

```json
{ "message": "Уведомление удалено" }
```

### Error Responses

**404** — Not found:
```json
{ "error": "Уведомление не найдено" }
```

---

## 13. My Notifications (User)

**GET** `/api/info/notifications/`

**Auth:** JWT (any role)

Returns notifications targeted at the **current user's status** (taken from JWT token), sorted newest first.

A `Student` sees only notifications with `target_statuses` containing `"Student"`.

### Success Response — `200 OK`

```json
{
    "total": 1,
    "notifications": [
        {
            "id": "abc123",
            "title_taj": "",
            "title_rus": "Важное объявление",
            "title_eng": "",
            "title_kor": "",
            "content_taj": "",
            "content_rus": "Занятия перенесены на пятницу",
            "content_eng": "",
            "content_kor": "",
            "image_url": "",
            "images": [
                {
                    "file_id": "1A2B3C4D",
                    "url": "https://drive.google.com/uc?id=1A2B3C4D"
                }
            ],
            "target_statuses": ["Student", "Teacher"],
            "created_at": "2026-06-16 10:30:00+00:00"
        }
    ]
}
```

### Error Responses

**400** — Status missing in token:
```json
{ "error": "Статус пользователя не определён" }
```

---

## Notification Object Reference

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Firestore document ID |
| `title_taj` | string | Title in Tajik |
| `title_rus` | string | Title in Russian |
| `title_eng` | string | Title in English |
| `title_kor` | string | Title in Korean |
| `content_taj` | string | Content in Tajik |
| `content_rus` | string | Content in Russian |
| `content_eng` | string | Content in English |
| `content_kor` | string | Content in Korean |
| `image_url` | string | Optional single external image URL |
| `images` | array | List of `{file_id, url}` uploaded to Google Drive |
| `target_statuses` | array | List of statuses that receive this notification |
| `created_at` | string | ISO datetime, set automatically |

## Image Storage

Notification images are stored at:
```
My Drive / Sejong Cloud / notifications / images /
```

## FCM Topics

| User status | FCM topic subscribed |
|-------------|---------------------|
| `Guest` | `status_Guest` |
| `Student` | `status_Student` |
| `Teacher` | `status_Teacher` |
| `Admin` | `status_Admin` |

Frontend subscribes to the topic returned in `fcm_topic` field after login:
```dart
// Flutter example
await FirebaseMessaging.instance.subscribeToTopic(loginResponse['fcm_topic']);
```

---

---

# Common Error Responses

| Status | Meaning |
|--------|---------|
| `401` | Token missing, expired, or revoked |
| `403` | Valid token but not Admin (for admin endpoints) |
| `400` | Invalid input data |
| `404` | Resource not found |

**401 — Token missing:**
```json
{ "error": "Токен не предоставлен" }
```

**401 — Token expired:**
```json
{ "error": "Токен истёк" }
```

**401 — Token revoked (after logout):**
```json
{ "error": "Токен отозван" }
```

**403 — Not an admin:**
```json
{ "error": "Доступ запрещён. Требуются права администратора." }
```
