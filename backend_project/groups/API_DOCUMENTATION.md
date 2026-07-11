# API Documentation — Groups App

**Base URL:** `http://127.0.0.1:8000/api/groups`

> Документация по пользователям находится в `users/API_DOCUMENTATION.md`

---

## Общее

### Аутентификация
Все эндпоинты требуют JWT-токен администратора:
```
Authorization: Bearer <admin_token>
```

```json
// 403 — недостаточно прав
{ "error": "Доступ запрещён. Требуются права администратора." }

// 401 — токен не передан / истёк / отозван
{ "error": "Токен не предоставлен" }
```

---

### GET `/admin/`
Список всех учебных групп с пагинацией.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Query params:**

| Параметр | Тип | По умолчанию | Максимум | Описание |
|----------|-----|-------------|---------|----------|
| `limit`  | int | 20          | 100     | Количество групп в ответе |

**Успех — 200:**
```json
{
    "total": 2,
    "has_more": false,
    "groups": [
        { "id": "AbCdEf...", "name": "CS-101", "teacher_id": "TuVwXy...", "students_count": 12, "created_at": "2026-07-11 09:15:00+00:00" },
        { "id": "XyZwVu...", "name": "CS-102", "teacher_id": "", "students_count": 0, "created_at": "2026-07-11 10:20:00+00:00" }
    ]
}
```

- `teacher_id` — ID пользователя со статусом `Teacher`, состоящего в группе; пустая строка, если преподаватель не назначен.
- `students_count` — количество пользователей группы со статусом `Student`.
- `created_at` — дата создания группы (может быть пустой у групп, созданных до добавления поля).

> Если `has_more: true` — запросите следующую страницу с увеличенным `limit`.

---

### POST `/admin/create/`
Создать новую учебную группу. Имя должно быть уникальным.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{ "name": "CS-101" }
```

**Успех — 201:**
```json
{
    "message": "Группа \"CS-101\" создана.",
    "group": { "id": "AbCdEf...", "name": "CS-101" }
}
```

**Ошибки:**
```json
// 400 — name не передан
{ "error": "Поле \"name\" обязательно" }

// 400 — имя занято
{ "error": "Группа с именем \"CS-101\" уже существует" }
```

---

### DELETE `/admin/<group_id>/delete/`
Удалить группу по ID. У всех участников группы поле `group` автоматически очищается.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{ "message": "Группа \"CS-101\" удалена." }
```

**Ошибки:**
```json
// 404
{ "error": "Группа не найдена" }
```

---

### PATCH `/admin/<group_id>/rename/`
Переименовать группу. Новое имя должно быть уникальным.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{ "name": "CS-103" }
```

**Успех — 200:**
```json
{
    "message": "Группа переименована.",
    "group": { "id": "AbCdEf...", "name": "CS-103" }
}
```

**Ошибки:**
```json
// 400 — name не передан
{ "error": "Поле \"name\" обязательно" }

// 400 — имя занято
{ "error": "Группа с именем \"CS-103\" уже существует" }

// 404
{ "error": "Группа не найдена" }
```

---

### GET `/admin/<group_id>/members/`
Список всех участников группы.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{
    "group": { "id": "AbCdEf...", "name": "CS-101" },
    "total": 2,
    "members": [
        {
            "id": "users/mMplMaUG...",
            "username": "john_doe",
            "fullname": "John Doe",
            "email": "john@example.com",
            "phone_number": "+992991234567",
            "status": "Student",
            "verification_status": "Approved",
            "group": "CS-101"
        }
    ]
}
```

**Ошибки:**
```json
// 404
{ "error": "Группа не найдена" }
```

---

### POST `/admin/assign/<user_id>/`
Назначить пользователя в группу.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{ "group_id": "AbCdEf..." }
```

> `group_id` берётся из ответа `GET /admin/` — поле `"id"`.

**Успех — 200:**
```json
{
    "message": "Пользователь добавлен в группу \"CS-101\".",
    "user": {
        "id": "users/mMplMaUG...",
        "username": "john_doe",
        "fullname": "John Doe",
        "email": "john@example.com",
        "phone_number": "+992991234567",
        "status": "Student",
        "verification_status": "Approved",
        "group": "CS-101"
    }
}
```

**Ошибки:**
```json
// 400 — group_id не передан
{ "error": "Поле \"group_id\" обязательно" }

// 404 — пользователь не найден
{ "error": "Пользователь не найден" }

// 404 — группа не найдена
{ "error": "Группа не найдена" }
```

---

### DELETE `/admin/unassign/<user_id>/`
Убрать пользователя из группы.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{
    "message": "Пользователь удалён из группы.",
    "user": {
        "id": "users/mMplMaUG...",
        "username": "john_doe",
        "fullname": "John Doe",
        "email": "john@example.com",
        "phone_number": "+992991234567",
        "status": "Student",
        "verification_status": "Approved",
        "group": ""
    }
}
```

**Ошибки:**
```json
// 400 — пользователь не состоит в группе
{ "error": "Пользователь не состоит ни в одной группе" }

// 404 — пользователь не найден
{ "error": "Пользователь не найден" }
```

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
