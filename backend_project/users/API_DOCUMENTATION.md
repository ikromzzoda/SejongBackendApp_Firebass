# API Documentation — Sejong Backend

**Base URL:** `http://127.0.0.1:8000/api/users`

---

## Общее

### Аутентификация
Все защищённые эндпоинты требуют JWT-токен в заголовке:
```
Authorization: Bearer <token>
```

### Форматы ответов
- Успех: данные + соответствующий HTTP-код (200 / 201)
- Ошибка: `{ "error": "описание ошибки" }` + соответствующий HTTP-код

### Объект пользователя (общий формат)
Возвращается во всех ответах, связанных с пользователем:
```json
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
```
> Поле `group` содержит **имя группы**, не ID. Если группа не назначена — пустая строка `""`.

### Статусы пользователя
| Значение | Описание |
|----------|----------|
| `Guest` | Только зарегистрировался, ожидает верификации |
| `Student` | Подтверждён администратором |
| `Teacher` | Преподаватель |
| `Admin` | Администратор |

### Статусы верификации
| Значение | Описание |
|----------|----------|
| `Pending` | Ожидает подтверждения |
| `Approved` | Подтверждён |
| `Rejected` | Отклонён |

---

## Аутентификация

### POST `/register/`
Регистрация нового пользователя. После регистрации статус `Guest`, верификация `Pending` — нужно подтверждение администратора.

**Headers:** не требуются

**Body (JSON):**
```json
{
    "username": "john_doe",
    "password": "MyPassword123",
    "email": "john@example.com",
    "phone_number": "+992991234567",
    "fullname": "John Doe",
    "date_of_birth": "2000-01-15"
}
```

| Поле | Тип | Обязательное |
|------|-----|:---:|
| `username` | string | ✅ |
| `password` | string | ✅ |
| `email` | string | ✅ |
| `phone_number` | string | ✅ |
| `fullname` | string | ❌ |
| `date_of_birth` | string | ❌ |

**Успех — 201:**
```json
{
    "message": "Регистрация успешна. Ожидайте подтверждения администратора.",
    "token": "eyJhbGci...",
    "status": "Guest",
    "verification_status": "Pending"
}
```

**Ошибки:**
```json
// 400 — обязательное поле не передано
{ "error": "Поле \"email\" обязательно" }

// 400 — неверный формат телефона
{ "error": "Номер должен начинаться с '+992' и содержать 9 цифр после него." }

// 400 — username уже занят
{ "error": "Пользователь с таким username уже существует" }
```

---

### POST `/login/`
Вход в систему.

**Headers:** не требуются

**Body (JSON):**
```json
{
    "username": "john_doe",
    "password": "MyPassword123"
}
```

**Успех — 200:**
```json
{
    "message": "Вход выполнен",
    "token": "eyJhbGci...",
    "status": "Student",
    "verification_status": "Approved"
}
```

**Ошибки:**
```json
// 400 — не переданы username или пароль
{ "error": "Введите username и пароль" }

// 401 — неверные данные
{ "error": "Неверный username или пароль" }
```

---

### POST `/logout/`
Выход из системы. Токен немедленно становится недействительным.

**Headers:**
```
Authorization: Bearer <token>
```

**Body:** не требуется

**Успех — 200:**
```json
{ "message": "Выход выполнен" }
```

**Ошибки:**
```json
// 401 — токен не передан
{ "error": "Токен не предоставлен" }

// 401 — токен истёк
{ "error": "Токен уже истёк" }

// 401 — токен недействителен
{ "error": "Недействительный токен" }
```

---

## Профиль

### POST `/profile/update/`
Обновление данных своего профиля. Все поля необязательные — передавайте только то, что нужно изменить.

**Headers:**
```
Authorization: Bearer <token>
```

**Body (JSON):**
```json
{
    "username": "new_login",
    "email": "new@example.com",
    "phone_number": "+992991234567",
    "check_password": "текущий_пароль",
    "password": "новый_пароль"
}
```

> При смене пароля поле `check_password` (текущий пароль) обязательно.

**Успех — 200:**
```json
{
    "message": "Профиль обновлён",
    "updated_fields": ["username", "email"],
    "token": "eyJhbGci..."
}
```

> После обновления возвращается **новый токен** — сохраните его вместо старого.

**Ошибки:**
```json
// 400 — нет данных для обновления
{ "error": "Нет данных для обновления" }

// 400 — username пустой
{ "error": "Username не может быть пустым" }

// 400 — username занят
{ "error": "Пользователь с таким username уже существует" }

// 400 — неверный формат телефона
{ "error": "Номер должен начинаться с '+992' и содержать 9 цифр после него." }

// 400 — не передан текущий пароль при смене
{ "error": "Для смены пароля укажите текущий пароль в поле 'check_password'" }

// 400 — неверный текущий пароль
{ "error": "Неверный текущий пароль" }

// 401 — проблема с токеном
{ "error": "Токен не предоставлен" }
```

---

### POST `/profile/avatar/`
Загрузка нового аватара. Файл сохраняется на Google Drive.

**Headers:**
```
Authorization: Bearer <token>
```

**Body (multipart/form-data):**
| Поле | Тип | Описание |
|------|-----|----------|
| `avatar` | File | Изображение JPEG, PNG или WEBP, максимум 3 МБ |

**Успех — 200:**
```json
{
    "message": "Аватар успешно обновлён",
    "avatar": "https://drive.google.com/uc?id=..."
}
```

**Ошибки:**
```json
// 400 — файл не передан
{ "error": "Файл не передан. Используйте поле \"avatar\"" }

// 400 — недопустимый формат
{ "error": "Недопустимый формат. Разрешены: JPEG, PNG, WEBP" }

// 400 — файл слишком большой
{ "error": "Файл слишком большой. Максимум 3 МБ" }

// 502 — ошибка загрузки на Drive
{ "error": "Ошибка загрузки на Google Drive: ..." }
```

---

## Администратор

> Все эндпоинты ниже доступны только пользователям со статусом `Admin`.

```json
// 403 — недостаточно прав
{ "error": "Доступ запрещён. Требуются права администратора." }

// 401 — токен не передан / истёк / отозван
{ "error": "Токен не предоставлен" }
```

---

### Пользователи

---

#### GET `/admin/users/`
Список всех пользователей. Поддерживает фильтрацию через query-параметры.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Query параметры (необязательные, только один за раз):**
| Параметр | Значения | Пример |
|----------|----------|--------|
| `status` | `Student`, `Teacher`, `Admin`, `Guest` | `?status=Student` |
| `verification_status` | `Pending`, `Approved`, `Rejected` | `?verification_status=Pending` |
| `group_id` | ID группы | `?group_id=groups/AbCdEf...` |

**Успех — 200:**
```json
{
    "total": 42,
    "users": [
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

---

#### GET `/admin/users/<user_id>/`
Получить одного пользователя по ID.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{
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
// 404
{ "error": "Пользователь не найден" }
```

---

#### PATCH `/admin/users/<user_id>/edit/`
Редактировать данные пользователя. Все поля необязательные — передавайте только то, что нужно изменить.

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Body (JSON):**
```json
{
    "fullname": "Новое Имя",
    "email": "new@example.com",
    "phone_number": "+992991234567",
    "date_of_birth": "2000-01-15",
    "status": "Teacher",
    "verification_status": "Approved",
    "group": "CS-101",
    "password": "NewPass123"
}
```

| Поле | Описание |
|------|----------|
| `fullname` | ФИО |
| `email` | Email |
| `phone_number` | Телефон в формате `+992XXXXXXXXX` |
| `date_of_birth` | Дата рождения |
| `status` | `Student` / `Teacher` / `Admin` / `Guest` |
| `verification_status` | `Pending` / `Approved` / `Rejected` |
| `group` | Имя группы (например `"CS-101"`) |
| `group_id` | ID группы (альтернатива полю `group`) |
| `password` | Новый пароль (без подтверждения — только для админа) |

**Успех — 200:**
```json
{
    "message": "Данные пользователя обновлены",
    "updated_fields": ["fullname", "status", "group"],
    "user": {
        "id": "users/mMplMaUG...",
        "username": "john_doe",
        "fullname": "Новое Имя",
        "status": "Teacher",
        "group": "CS-101",
        ...
    }
}
```

**Ошибки:**
```json
// 400 — нет данных для обновления
{ "error": "Нет данных для обновления" }

// 400 — неверный формат телефона
{ "error": "Номер должен начинаться с '+992' и содержать 9 цифр после него." }

// 400 — недопустимый статус
{ "error": "Допустимые статусы: Student, Teacher, Admin, Guest" }

// 400 — недопустимый verification_status
{ "error": "Допустимые значения: Pending, Approved, Rejected" }

// 400 — пустой пароль
{ "error": "Пароль не может быть пустым" }

// 404 — пользователь не найден
{ "error": "Пользователь не найден" }

// 404 — группа не найдена
{ "error": "Группа не найдена" }
```

---

#### POST `/admin/users/create/`
Создать нового пользователя вручную. Пользователь сразу получает `verification_status: Approved`.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{
    "username": "john_doe",
    "password": "MyPassword123",
    "email": "john@example.com",
    "phone_number": "+992991234567",
    "fullname": "John Doe",
    "date_of_birth": "2000-01-15",
    "status": "Student",
    "group": "CS-101",
    "avatar": "https://..."
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `username` | string | ✅ | |
| `password` | string | ✅ | |
| `email` | string | ✅ | |
| `phone_number` | string | ✅ | Формат: `+992XXXXXXXXX` |
| `fullname` | string | ❌ | |
| `date_of_birth` | string | ❌ | |
| `status` | string | ❌ | По умолчанию `Student` |
| `group` | string | ❌ | Имя группы, например `"CS-101"` |
| `group_id` | string | ❌ | ID группы (альтернатива `group`) |
| `avatar` | string | ❌ | URL аватара, по умолчанию — стандартный |

**Успех — 201:**
```json
{
    "message": "Пользователь \"john_doe\" успешно создан.",
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
// 400 — обязательное поле не передано
{ "error": "Поле \"email\" обязательно" }

// 400 — неверный формат телефона
{ "error": "Номер должен начинаться с '+992' и содержать 9 цифр после него." }

// 400 — username занят
{ "error": "Пользователь с таким username уже существует" }

// 400 — недопустимый статус
{ "error": "Допустимые статусы: Student, Teacher, Admin, Guest" }

// 404 — группа не найдена
{ "error": "Группа не найдена" }
```

---

#### GET `/admin/pending/`
Список пользователей, ожидающих верификации (`verification_status = Pending`).

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Успех — 200:**
```json
{
    "users": [
        {
            "id": "users/mMplMaUG...",
            "username": "john_doe",
            "fullname": "John Doe",
            "email": "john@example.com",
            "phone_number": "+992991234567",
            "status": "Guest",
            "verification_status": "Pending",
            "group": ""
        }
    ]
}
```

---

#### POST `/admin/verify/<user_id>/`
Подтвердить или отклонить верификацию пользователя.
При `approve` — статус автоматически меняется на `Student`.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{ "action": "approve" }
// или
{ "action": "reject" }
```

**Успех — 200:**
```json
{
    "message": "Пользователь подтверждён.",
    "user": { ... }
}
```

**Ошибки:**
```json
// 400 — неверный action
{ "error": "Поле \"action\" должно быть \"approve\" или \"reject\"" }

// 404
{ "error": "Пользователь не найден" }
```

---

#### POST `/admin/set-status/<user_id>/`
Назначить статус пользователю.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{ "status": "Teacher" }
```

Допустимые значения: `Student`, `Teacher`, `Admin`, `Guest`

**Успех — 200:**
```json
{
    "message": "Статус пользователя изменён на \"Teacher\".",
    "user": { ... }
}
```

**Ошибки:**
```json
// 400
{ "error": "Допустимые статусы: Student, Teacher, Admin, Guest" }

// 404
{ "error": "Пользователь не найден" }
```

---

#### POST `/admin/assign-group/<user_id>/`
Добавить пользователя в учебную группу.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (JSON):**
```json
{ "group_id": "groups/AbCdEf..." }
```

**Успех — 200:**
```json
{
    "message": "Пользователь добавлен в группу \"CS-101\".",
    "user": {
        "id": "users/mMplMaUG...",
        "username": "john_doe",
        "group": "CS-101",
        ...
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

### Группы

---

#### GET `/admin/groups/`
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

#### POST `/admin/groups/create/`
Создать новую учебную группу. Имя группы должно быть уникальным.

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

// 400 — имя уже занято
{ "error": "Группа с именем \"CS-101\" уже существует" }
```

---

#### DELETE `/admin/groups/<group_id>/delete/`
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

### Массовая загрузка студентов

---

#### GET `/admin/students/import/template/`
Скачать шаблон Excel для заполнения данных студентов.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Ответ:** файл `students_import_template.xlsx`

Колонки шаблона:
| Колонка | Обязательное |
|---------|:---:|
| ФИО | ❌ |
| Email | ❌ |
| Телефон | ❌ |
| Дата рождения | ❌ |
| Группа | ❌ |

> Заголовки колонок распознаются автоматически на русском и английском языках.

---

#### POST `/admin/students/import/`
Загрузить Excel-файл со студентами. Для каждой строки автоматически генерируется `username` и `password`.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (multipart/form-data):**
| Поле | Тип | Описание |
|------|-----|----------|
| `file` | File | Файл формата `.xlsx` |

**Ответ:** файл `students_credentials.xlsx`

Содержимое выходного файла:
| № | ФИО | Email | Телефон | Группа | **Username** | **Password** | Статус | Примечание |
|---|-----|-------|---------|--------|------------|------------|--------|------------|
| 1 | Иванов Иван | ... | ... | CS-101 | ivan_4821 | Kd7mNpQ2xR | Успешно | |
| 2 | ... | ... | ... | ... | ... | ... | Ошибка | описание |

- Строки зелёные — успешно, красные — ошибка
- Username и Password выделены жирным
- В конце файла итоговая строка

> В Postman: Send → **Save Response → Save to file**

**Ошибки (JSON):**
```json
// 400 — файл не передан
{ "error": "Файл не передан. Используйте поле \"file\"" }

// 400 — неверный формат файла
{ "error": "Разрешён только формат .xlsx" }

// 400 — файл повреждён или не является Excel
{ "error": "Не удалось открыть файл. Убедитесь что это корректный .xlsx" }

// 400 — файл пустой
{ "error": "Файл пустой или содержит только заголовок" }

// 400 — не найдены известные заголовки
{ "error": "Не найдены известные заголовки. Ожидаются: ФИО, Email, Телефон, Группа, Дата рождения" }
```

---

## Коды ответов

| Код | Значение |
|-----|----------|
| 200 | Успех |
| 201 | Создан |
| 400 | Неверный запрос (ошибка валидации) |
| 401 | Не авторизован (нет / истёк / отозван токен) |
| 403 | Доступ запрещён (недостаточно прав) |
| 404 | Ресурс не найден |
| 502 | Ошибка внешнего сервиса (Google Drive) |
