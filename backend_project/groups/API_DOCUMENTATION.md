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
Список всех учебных групп.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{
    "groups": [
        { "id": "groups/AbCdEf...", "name": "CS-101" },
        { "id": "groups/XyZwVu...", "name": "CS-102" }
    ]
}
```

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
    "group": { "id": "groups/AbCdEf...", "name": "CS-101" }
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
Удалить группу по ID.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body:** не требуется

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

### POST `/admin/assign/<user_id>/`
Назначить пользователя в группу.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{ "group_id": "groups/AbCdEf..." }
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

// 404 — группа не найдена
{ "error": "Группа не найдена" }

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
