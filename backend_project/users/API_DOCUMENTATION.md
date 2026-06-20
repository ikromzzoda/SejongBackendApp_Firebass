# API Documentation — Users App

**Base URL:** `http://127.0.0.1:8000/api/users`

---

## Быстрый справочник

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| POST | `/register/` | Открытый | Регистрация |
| POST | `/login/` | Открытый | Вход |
| POST | `/logout/` | Авторизованный | Выход |
| GET | `/profile/` | Авторизованный | Мои данные |
| POST | `/profile/update/` | Авторизованный | Изменить профиль |
| POST | `/profile/avatar/` | Авторизованный | Сменить аватар |
| GET | `/admin/users/` | Admin | Список всех пользователей |
| GET | `/admin/users/<user_id>/` | Admin | Получить пользователя |
| PATCH | `/admin/users/<user_id>/edit/` | Admin | Редактировать пользователя |
| POST | `/admin/users/create/` | Admin | Создать пользователя |
| GET | `/admin/pending/` | Admin | Ожидающие верификации |
| POST | `/admin/verify/<user_id>/` | Admin | Подтвердить/отклонить |
| POST | `/admin/set-status/<user_id>/` | Admin | Назначить статус |
| GET | `/admin/students/import/template/` | Admin | Скачать шаблон Excel |
| POST | `/admin/students/import/` | Admin | Загрузить студентов из Excel |

---

## Общее

### Аутентификация
Все защищённые эндпоинты требуют JWT-токен в заголовке:
```
Authorization: Bearer <token>
```

### Форматы ответов
- Успех: данные + HTTP 200 / 201
- Ошибка: `{ "error": "описание" }` + соответствующий HTTP-код

### Объект пользователя (краткий — в списках)
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

### Объект пользователя (полный — GET /profile/)
```json
{
    "id": "users/mMplMaUG...",
    "username": "john_doe",
    "fullname": "John Doe",
    "email": "john@example.com",
    "phone_number": "+992991234567",
    "date_of_birth": "2000-01-15",
    "status": "Student",
    "verification_status": "Approved",
    "group_id": "ijidfjgijfjiodjf",
    "group": "CS-101",
    "avatar": "https://drive.google.com/uc?id=...",
    "date_joined": "2025-01-10 08:00:00"
}
```

> `group_id` — сырой ID группы в Firestore. Если не назначена — пустая строка `""`.
> `group` — **имя** группы. Если не назначена — пустая строка `""`.

### Статусы пользователя
| Значение | Описание |
|----------|----------|
| `Guest` | Только зарегистрировался, ещё не подтверждён |
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
Регистрация нового пользователя. После регистрации: `status=Guest`, `verification_status=Pending`.

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

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `username` | string | ✅ | Уникальный логин |
| `password` | string | ✅ | Пароль |
| `email` | string | ✅ | Email |
| `phone_number` | string | ✅ | Формат `+992XXXXXXXXX` (9 цифр после +992) |
| `fullname` | string | ❌ | ФИО |
| `date_of_birth` | string | ❌ | Дата рождения, например `2000-01-15` |

**Успех — 201:**
```json
{
    "message": "Регистрация успешна. Ожидайте подтверждения администратора.",
    "token": "eyJhbGci...",
    "status": "Guest",
    "verification_status": "Pending",
    "fcm_topic": "status_Guest"
}
```

> `fcm_topic` — тема FCM, зарезервировано для будущего использования.
> `token` — сохраните для следующих запросов.

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
Вход в систему. Если передать `device_token` — сохранит его в Firestore для FCM push-уведомлений.

**Headers:** не требуются

**Body (JSON):**
```json
{
    "username": "john_doe",
    "password": "MyPassword123",
    "device_token": "fcm_registration_token_from_firebase_sdk"
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `username` | string | ✅ | Логин пользователя |
| `password` | string | ✅ | Пароль |
| `device_token` | string | ❌ | FCM токен устройства для push-уведомлений |

**Успех — 200:**
```json
{
    "message": "Вход выполнен",
    "token": "eyJhbGci...",
    "status": "Student",
    "verification_status": "Approved"
}
```

> `token` — JWT токен действителен 30 дней. Используйте во всех последующих запросах.

**Ошибки:**
```json
// 400 — не переданы username или пароль
{ "error": "Введите username и пароль" }

// 401 — неверные учётные данные
{ "error": "Неверный username или пароль" }
```

---

### POST `/logout/`
Выход из системы. Токен немедленно добавляется в чёрный список и становится недействительным.

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

// 401 — токен уже истёк
{ "error": "Токен уже истёк" }

// 401 — токен недействителен (или уже в чёрном списке)
{ "error": "Недействительный токен" }
```

---

## Профиль

### GET `/profile/`
Получить полные данные своего профиля.

**Headers:**
```
Authorization: Bearer <token>
```

**Body:** не требуется

**Успех — 200:**
```json
{
    "id": "users/mMplMaUG...",
    "username": "john_doe",
    "fullname": "John Doe",
    "email": "john@example.com",
    "phone_number": "+992991234567",
    "date_of_birth": "2000-01-15",
    "status": "Student",
    "verification_status": "Approved",
    "group_id": "ijidfjgijfjiodjf",
    "avatar": "https://drive.google.com/uc?id=...",
    "date_joined": "2025-01-10 08:00:00"
}
```

**Ошибки:**
```json
// 401 — токен не передан или недействителен
{ "error": "Токен не предоставлен" }

// 404 — пользователь удалён из базы
{ "error": "Пользователь не найден" }
```

---

### POST `/profile/update/`
Обновление данных своего профиля. Все поля необязательные — передавайте только те, которые нужно изменить.

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

| Поле | Тип | Описание |
|------|-----|----------|
| `username` | string | Новый логин (должен быть уникальным) |
| `email` | string | Новый email |
| `phone_number` | string | Новый телефон, формат `+992XXXXXXXXX` |
| `check_password` | string | Текущий пароль — **обязательно при смене пароля** |
| `password` | string | Новый пароль |

**Успех — 200:**
```json
{
    "message": "Профиль обновлён",
    "updated_fields": ["username", "email"],
    "token": "eyJhbGci..."
}
```

> Возвращается **новый токен** — сохраните его и используйте вместо старого (важно если изменили `username`).

**Ошибки:**
```json
// 400 — нет данных для обновления
{ "error": "Нет данных для обновления" }

// 400 — пустой username
{ "error": "Username не может быть пустым" }

// 400 — username уже занят
{ "error": "Пользователь с таким username уже существует" }

// 400 — неверный формат телефона
{ "error": "Номер должен начинаться с '+992' и содержать 9 цифр после него." }

// 400 — не передан текущий пароль при смене
{ "error": "Для смены пароля укажите текущий пароль в поле 'check_password'" }

// 400 — неверный текущий пароль
{ "error": "Неверный текущий пароль" }

// 401 — токен не передан
{ "error": "Токен не предоставлен" }

// 404 — пользователь не найден
{ "error": "Пользователь не найден" }
```

---

### POST `/profile/avatar/`
Загрузка нового аватара. Старый аватар заменяется на Google Drive.

**Headers:**
```
Authorization: Bearer <token>
```

**Body (multipart/form-data):**
| Поле | Тип | Ограничения |
|------|-----|-------------|
| `avatar` | File | Форматы: JPEG, PNG, WEBP — максимум **3 МБ** |

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

// 400 — недопустимый формат файла
{ "error": "Недопустимый формат. Разрешены: JPEG, PNG, WEBP" }

// 400 — файл слишком большой
{ "error": "Файл слишком большой. Максимум 3 МБ" }

// 401 — токен не передан
{ "error": "Токен не предоставлен" }

// 404 — пользователь не найден
{ "error": "Пользователь не найден" }

// 502 — ошибка Google Drive
{ "error": "Ошибка загрузки на Google Drive: ..." }
```

---

## Администратор

> Все эндпоинты этого раздела доступны **только** пользователям со статусом `Admin`.

```json
// 401 — токен не передан
{ "error": "Токен не предоставлен" }

// 403 — недостаточно прав
{ "error": "Доступ запрещён. Требуются права администратора." }
```

---

### GET `/admin/users/`
Список всех пользователей с поддержкой фильтрации. Возвращает максимум 500 пользователей.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Query параметры (необязательные, только один за раз):**
| Параметр | Допустимые значения | Пример |
|----------|---------------------|--------|
| `status` | `Student` `Teacher` `Admin` `Guest` | `?status=Student` |
| `verification_status` | `Pending` `Approved` `Rejected` | `?verification_status=Pending` |
| `group_id` | ID группы (без префикса `groups/`) | `?group_id=AbCdEf123` |

> Если не передан ни один параметр — возвращаются все пользователи.

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

### GET `/admin/users/<user_id>/`
Получить данные одного пользователя по его ID.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**URL параметр:** `user_id` — ID без префикса `users/`, например `mMplMaUG...`

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

### PATCH `/admin/users/<user_id>/edit/`
Редактировать данные любого пользователя. Все поля необязательные.

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Body (JSON):**
```json
{
    "fullname": "Новое Имя Фамилия",
    "email": "new@example.com",
    "phone_number": "+992991234567",
    "date_of_birth": "2000-01-15",
    "status": "Teacher",
    "verification_status": "Approved",
    "group": "CS-101",
    "password": "NewPass123"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `fullname` | string | ФИО |
| `email` | string | Email |
| `phone_number` | string | Телефон, формат `+992XXXXXXXXX` |
| `date_of_birth` | string | Дата рождения |
| `status` | string | `Student` / `Teacher` / `Admin` / `Guest` |
| `verification_status` | string | `Pending` / `Approved` / `Rejected` |
| `group` | string | Имя группы, например `"CS-101"` |
| `group_id` | string | ID группы (альтернатива `group`) |
| `password` | string | Новый пароль без подтверждения (только для Admin) |

> Если передать и `group`, и `group_id` — приоритет у `group_id`.

**Успех — 200:**
```json
{
    "message": "Данные пользователя обновлены",
    "updated_fields": ["fullname", "status"],
    "user": {
        "id": "users/mMplMaUG...",
        "username": "john_doe",
        "fullname": "Новое Имя Фамилия",
        "email": "john@example.com",
        "phone_number": "+992991234567",
        "status": "Teacher",
        "verification_status": "Approved",
        "group": "CS-101"
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

// 404 — группа не найдена (при передаче group или group_id)
{ "error": "Группа не найдена" }
{ "error": "Группа \"CS-999\" не найдена" }
```

---

### POST `/admin/users/create/`
Создать нового пользователя вручную. Автоматически получает `verification_status: Approved`.

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
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
    "group": "CS-101"
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `username` | string | ✅ | Уникальный логин |
| `password` | string | ✅ | Пароль |
| `email` | string | ✅ | Email |
| `phone_number` | string | ✅ | Формат `+992XXXXXXXXX` |
| `fullname` | string | ❌ | ФИО |
| `date_of_birth` | string | ❌ | Дата рождения |
| `status` | string | ❌ | По умолчанию `Student` |
| `group` | string | ❌ | Имя группы, например `"CS-101"` |
| `group_id` | string | ❌ | ID группы (альтернатива `group`) |
| `avatar` | string | ❌ | URL аватара (по умолчанию — стандартный аватар) |

**Успех — 201:**
```json
{
    "message": "Пользователь \"john_doe\" успешно создан.",
    "user": {
        "id": "users/XyZaBcDe...",
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

// 400 — username уже занят
{ "error": "Пользователь с таким username уже существует" }

// 400 — недопустимый статус
{ "error": "Допустимые статусы: Student, Teacher, Admin, Guest" }

// 404 — группа не найдена
{ "error": "Группа не найдена" }
{ "error": "Группа \"CS-999\" не найдена" }
```

---

### GET `/admin/pending/`
Список всех пользователей с `verification_status = Pending` (ожидают подтверждения).

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
            "username": "new_user",
            "fullname": "Новый Пользователь",
            "email": "user@example.com",
            "phone_number": "+992991234567",
            "status": "Guest",
            "verification_status": "Pending",
            "group": ""
        }
    ]
}
```

---

### POST `/admin/verify/<user_id>/`
Подтвердить или отклонить верификацию пользователя.

- При `approve`: `verification_status → Approved`, `status → Student`
- При `reject`: `verification_status → Rejected` (status не меняется)

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Body (JSON):**
```json
{ "action": "approve" }
```
или
```json
{ "action": "reject" }
```

**Успех — 200 (approve):**
```json
{
    "message": "Пользователь подтверждён.",
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

**Успех — 200 (reject):**
```json
{
    "message": "Пользователь отклонён.",
    "user": {
        "status": "Guest",
        "verification_status": "Rejected",
        ...
    }
}
```

**Ошибки:**
```json
// 400 — неверное значение action
{ "error": "Поле \"action\" должно быть \"approve\" или \"reject\"" }

// 404
{ "error": "Пользователь не найден" }
```

---

### POST `/admin/set-status/<user_id>/`
Напрямую назначить статус пользователю (не меняет `verification_status`).

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
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
    "user": {
        "id": "users/mMplMaUG...",
        "username": "john_doe",
        "fullname": "John Doe",
        "email": "john@example.com",
        "phone_number": "+992991234567",
        "status": "Teacher",
        "verification_status": "Approved",
        "group": "CS-101"
    }
}
```

**Ошибки:**
```json
// 400 — недопустимый статус
{ "error": "Допустимые статусы: Student, Teacher, Admin, Guest" }

// 404
{ "error": "Пользователь не найден" }
```

---

## Массовая загрузка студентов

### GET `/admin/students/import/template/`
Скачать готовый шаблон Excel для заполнения.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Ответ:** файл `students_import_template.xlsx`

Колонки шаблона:
| Колонка | Пример |
|---------|--------|
| ФИО | Иванов Иван Иванович |
| Email | ivan@example.com |
| Телефон | +992991234567 |
| Дата рождения | 2003-05-20 |
| Группа | CS-101 |

> Телефон принимается в любом формате — скобки и пробелы удаляются автоматически:
> `(+992) 900 00 0000` → `+992900000000`

> **Как скачать в Postman:** Send → кнопка **Save Response** → **Save to file**

---

### POST `/admin/students/import/`
Загрузить Excel-файл со списком студентов. Для каждой строки автоматически генерируются `username` и `password`.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Body (multipart/form-data):**
| Поле | Тип | Описание |
|------|-----|----------|
| `file` | File | Файл `.xlsx` с данными студентов |

**Поддерживаемые заголовки колонок (регистр не важен):**
| Поле | Принимаемые названия колонок |
|------|------------------------------|
| ФИО | `ФИО`, `Имя`, `Полное имя`, `Full Name`, `Name` |
| Email | `Email`, `Почта`, `E-mail`, `Эл. почта` |
| Телефон | `Телефон`, `Номер`, `Phone Number`, `Тел` |
| Дата рождения | `Дата рождения`, `Дата`, `Birth`, `Д.р.` |
| Группа | `Группа`, `Group`, `Учебная группа`, `Класс` |

**Ответ:** файл `students_credentials.xlsx`

Колонки результата:
| № | ФИО | Email | Телефон | Группа | **Username** | **Password** | Статус | Примечание |
|---|-----|-------|---------|--------|------------|------------|--------|------------|
| 1 | Иванов Иван | ... | +992991234567 | CS-101 | **ivan_4821** | **Kd7mNpQ2xR** | Успешно | |
| 2 | ... | ... | ... | CS-999 | | | Ошибка | Группа не найдена |

В конце файла — строка итогов: `Итого: 50 строк | Успешно: 48 | Ошибок: 2`

> Созданные студенты получают: `status=Student`, `verification_status=Approved`

> **Username** генерируется из первого слова ФИО + транслитерация + случайные цифры, например: `ivan_4821`

> **Как сохранить в Postman:** Send → **Save Response** → **Save to file**

**Ошибки (JSON):**
```json
// 400 — файл не передан
{ "error": "Файл не передан. Используйте поле \"file\"" }

// 400 — неверный формат файла
{ "error": "Разрешён только формат .xlsx" }

// 400 — файл повреждён
{ "error": "Не удалось открыть файл. Убедитесь что это корректный .xlsx" }

// 400 — файл пустой (только заголовок)
{ "error": "Файл пустой или содержит только заголовок" }

// 400 — заголовки колонок не распознаны
{ "error": "Не найдены известные заголовки. Ожидаются: ФИО, Email, Телефон, Группа, Дата рождения" }
```

---

## Коды ответов

| Код | Значение |
|-----|----------|
| 200 | Успех |
| 201 | Ресурс создан |
| 400 | Неверный запрос (ошибка валидации) |
| 401 | Не авторизован (токен не передан или недействителен) |
| 403 | Доступ запрещён (недостаточно прав) |
| 404 | Ресурс не найден |
| 502 | Ошибка внешнего сервиса (Google Drive) |

---

## Примеры в Postman

### 1. Регистрация
```
POST http://127.0.0.1:8000/api/users/register/
Content-Type: application/json

{
    "username": "test_user",
    "password": "Test1234",
    "email": "test@example.com",
    "phone_number": "+992901234567",
    "fullname": "Тест Пользователь"
}
```

### 2. Вход с device_token
```
POST http://127.0.0.1:8000/api/users/login/
Content-Type: application/json

{
    "username": "test_user",
    "password": "Test1234",
    "device_token": "fcm_token_с_устройства"
}
```

### 3. Мой профиль
```
GET http://127.0.0.1:8000/api/users/profile/
Authorization: Bearer <token>
```

### 4. Изменить пароль
```
POST http://127.0.0.1:8000/api/users/profile/update/
Authorization: Bearer <token>
Content-Type: application/json

{
    "check_password": "Test1234",
    "password": "NewPass5678"
}
```

### 5. Сменить аватар
```
POST http://127.0.0.1:8000/api/users/profile/avatar/
Authorization: Bearer <token>
Content-Type: multipart/form-data

avatar: [выбрать файл]
```

### 6. Список студентов
```
GET http://127.0.0.1:8000/api/users/admin/users/?status=Student
Authorization: Bearer <admin_token>
```

### 7. Подтвердить пользователя
```
POST http://127.0.0.1:8000/api/users/admin/verify/mMplMaUG.../
Authorization: Bearer <admin_token>
Content-Type: application/json

{ "action": "approve" }
```

### 8. Назначить преподавателя
```
POST http://127.0.0.1:8000/api/users/admin/set-status/mMplMaUG.../
Authorization: Bearer <admin_token>
Content-Type: application/json

{ "status": "Teacher" }
```

### 9. Создать студента вручную
```
POST http://127.0.0.1:8000/api/users/admin/users/create/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
    "username": "ali_2025",
    "password": "SecurePass1",
    "email": "ali@example.com",
    "phone_number": "+992901234567",
    "fullname": "Али Иванов",
    "status": "Student",
    "group": "CS-101"
}
```

### 10. Массовый импорт
```
POST http://127.0.0.1:8000/api/users/admin/students/import/
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data

file: [students.xlsx]
```
> После отправки: **Save Response → Save to file** — получите credentials.xlsx
