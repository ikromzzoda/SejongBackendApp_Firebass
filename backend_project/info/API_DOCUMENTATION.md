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
