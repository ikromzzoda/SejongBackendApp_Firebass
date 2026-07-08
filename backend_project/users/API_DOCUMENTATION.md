# API Documentation — Users App

**Base URL:** `http://127.0.0.1:8000/api/users`

---

## Аутентификация

```
Authorization: Bearer <token>
```

| Уровень доступа | Описание |
|-----------------|----------|
| Открытый | `POST /register/`, `POST /login/` |
| Авторизованный | `POST /logout/`, `/profile/*` |
| Admin | Все `/admin/*` |

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
| POST | `/register/` | Открытый | Регистрация |
| POST | `/login/` | Открытый | Вход |
| POST | `/logout/` | Авторизованный | Выход |
| POST | `/token/refresh/` | Открытый | Обновить токен |
| POST | `/forgot-password/` | Открытый | Отправить код сброса пароля на email |
| POST | `/forgot-password/verify/` | Открытый | Проверить код, получить reset_token |
| POST | `/forgot-password/reset/` | Открытый | Установить новый пароль |
| GET | `/profile/` | Авторизованный | Мои данные |
| PATCH | `/profile/update/` | Авторизованный | Изменить профиль |
| POST | `/profile/avatar/` | Авторизованный | Сменить аватар |
| POST | `/profile/email/resend-code/` | Авторизованный | Повторно отправить код подтверждения email |
| GET | `/admin/users/` | Admin | Список всех пользователей |
| POST | `/admin/users/create/` | Admin | Создать пользователя |
| GET | `/admin/users/<user_id>/` | Admin | Получить пользователя |
| PATCH | `/admin/users/<user_id>/edit/` | Admin | Редактировать пользователя |
| POST | `/admin/users/<user_id>/avatar/` | Admin | Сменить аватар пользователя |
| POST | `/admin/verify/<user_id>/` | Admin | Подтвердить / отклонить |
| POST | `/admin/set-status/<user_id>/` | Admin | Назначить статус |
| GET | `/admin/students/import/template/` | Admin | Скачать шаблон Excel |
| POST | `/admin/students/import/` | Admin | Загрузить студентов из Excel |

---

## Справочник

### Статусы пользователя

| Значение | Описание |
|----------|----------|
| `Guest` | Только зарегистрировался, не подтверждён |
| `Student` | Подтверждён администратором |
| `Teacher` | Преподаватель |
| `Admin` | Администратор |

### Статусы верификации

| Значение | Описание |
|----------|----------|
| `Pending` | Ожидает подтверждения |
| `Approved` | Подтверждён |
| `Rejected` | Отклонён |

### Стандартный объект пользователя

Возвращается функцией `_user_dict` — используется во всех admin-эндпоинтах.

```json
{
    "id": "users/mMplMaUG...",
    "username": "john_doe",
    "fullname": "John Doe",
    "email": "john@example.com",
    "phone_number": "+992991234567",
    "status": "Student",
    "verification_status": "Approved",
    "group_id": "AbCdEf123",
    "group": "CS-101",
    "avatar": "https://drive.google.com/uc?id=...",
    "date_joined": "2025-01-10 08:00:00"
}
```

> `group_id` — Firestore-ID группы. Пустая строка `""` если не назначена.  
> `group` — имя группы. Пустая строка `""` если не назначена.  
> `avatar` — URL аватара на Google Drive. Стандартный аватар если не загружен.

### Расширенный объект пользователя

Возвращается только эндпоинтом `GET /admin/users/<user_id>/`. Включает все стандартные поля плюс:

```json
{
    "...",
    "date_of_birth": "2000-01-15",
    "device_token": "fcm_token_устройства"
}
```

---

## Регистрация и вход

### POST `/register/`

Регистрация нового пользователя. После регистрации: `status = Guest`, `verification_status = Pending`.

> Если передаётся аватар — использовать `multipart/form-data`. Без аватара можно `application/json`.

**Body (multipart/form-data или JSON):**

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `username` | string | ✅ | Уникальный логин |
| `password` | string | ✅ | Пароль |
| `email` | string | ✅ | Email |
| `phone_number` | string | ✅ | Формат `+992XXXXXXXXX` (9 цифр после +992) |
| `fullname` | string | ❌ | ФИО |
| `date_of_birth` | string | ❌ | Дата рождения, например `2000-01-15` |
| `avatar` | file | ❌ | Фото профиля (JPEG, PNG, WEBP, макс. 3 МБ) |

```json
// 201 — успех
{
    "message": "Регистрация успешна. Ожидайте подтверждения администратора.",
    "token": "eyJhbGci...",
    "status": "Guest",
    "verification_status": "Pending",
    "avatar": "https://drive.google.com/uc?id=...",
    "fcm_topic": "status_Guest"
}
```

> `token` — сохраните для следующих запросов.  
> `avatar` — URL загруженного аватара, или URL стандартного аватара если не передавался.  
> `fcm_topic` — зарезервировано для FCM.

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Поле \"email\" обязательно"}` |
| 400 | `{"error": "Номер должен начинаться с '+992' и содержать 9 цифр после него."}` |
| 400 | `{"error": "Пользователь с таким username уже существует"}` |
| 400 | `{"error": "Недопустимый формат аватара. Разрешены: JPEG, PNG, WEBP"}` |
| 400 | `{"error": "Файл аватара слишком большой. Максимум 3 МБ"}` |

---

### POST `/login/`

Вход в систему. `device_token` сохраняется в Firestore для FCM push-уведомлений.

**Body (JSON):**

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `username` | string | ✅ | Логин |
| `password` | string | ✅ | Пароль |
| `device_token` | string | ✅ | FCM токен устройства |

```json
// Запрос
{
    "username": "john_doe",
    "password": "MyPassword123",
    "device_token": "fcm_registration_token_from_firebase_sdk"
}

// 200 — успех
{
    "message": "Вход выполнен",
    "token": "eyJhbGci...",
    "refresh_token": "eyJhbGci...",
    "status": "Student",
    "verification_status": "Approved"
}
```

> `token` — access token, действителен **1 день**.  
> `refresh_token` — действителен **30 дней**. Используйте для получения нового `token` без повторного логина.

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Введите username и пароль"}` |
| 401 | `{"error": "Неверный username или пароль"}` |

---

### POST `/token/refresh/`

Получить новый `token` без повторного логина. При каждом вызове оба токена обновляются (rotation) — старый `refresh_token` сразу становится недействительным.

**Body (JSON):**

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `refresh_token` | string | ✅ | Refresh token, полученный при логине |

```json
// Запрос
{ "refresh_token": "eyJhbGci..." }

// 200 — успех
{
    "token": "eyJhbGci...",
    "refresh_token": "eyJhbGci..."
}
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "refresh_token не передан"}` |
| 401 | `{"error": "Refresh token истёк. Войдите заново."}` |
| 401 | `{"error": "Недействительный refresh token"}` |
| 401 | `{"error": "Refresh token недействителен или уже использован"}` |

---

### POST `/logout/`

Выход. Access token добавляется в чёрный список, refresh token аннулируется.

**Headers:** `Authorization: Bearer <token>`

**Body:** не требуется

```json
// 200 — успех
{ "message": "Выход выполнен" }
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 401 | `{"error": "Токен не предоставлен"}` |
| 401 | `{"error": "Токен уже истёк"}` |
| 401 | `{"error": "Недействительный токен"}` |

---

## Сброс пароля (забыли пароль)

Флоу из трёх шагов: пользователь вводит email → получает 6-значный код на почту → вводит код → приложение получает `reset_token` и показывает экран нового пароля.

### POST `/forgot-password/`

Отправляет 6-значный код на email. Код действует **15 минут**, повторная отправка — не чаще **раза в 10 минут**. Ответ всегда одинаковый (200), даже если email не зарегистрирован — защита от перебора адресов.

**Body (JSON):**

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `email` | string | ✅ | Email, указанный при регистрации |

```json
// Запрос
{ "email": "student@example.com" }

// 200 — всегда
{ "message": "Если такой email зарегистрирован, код отправлен на почту." }
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Поле \"email\" обязательно"}` |

---

### POST `/forgot-password/verify/`

Проверяет код из письма. При верном коде возвращает `reset_token` (действует 10 минут, одноразовый). После **5 неверных попыток** код аннулируется — нужно запросить новый через `/forgot-password/`.

**Body (JSON):**

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `email` | string | ✅ | Тот же email |
| `code` | string | ✅ | 6-значный код из письма |

```json
// Запрос
{ "email": "student@example.com", "code": "483920" }

// 200 — успех
{
    "message": "Код подтверждён. Установите новый пароль.",
    "reset_token": "eyJhbGci..."
}
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Поля \"email\" и \"code\" обязательны"}` |
| 400 | `{"error": "Код неверен или истёк. Запросите новый код."}` |
| 400 | `{"error": "Код истёк. Запросите новый код."}` |
| 400 | `{"error": "Неверный код. Осталось попыток: N"}` |
| 429 | `{"error": "Слишком много неверных попыток. Запросите новый код."}` |

---

### POST `/forgot-password/reset/`

Устанавливает новый пароль. После смены все refresh-токены пользователя отзываются — нужно войти заново.

**Body (JSON):**

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `reset_token` | string | ✅ | Токен из ответа `/forgot-password/verify/` |
| `new_password` | string | ✅ | Новый пароль (минимум 6 символов) |

```json
// Запрос
{ "reset_token": "eyJhbGci...", "new_password": "newSecret123" }

// 200 — успех
{ "message": "Пароль изменён. Войдите с новым паролем." }
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Поля \"reset_token\" и \"new_password\" обязательны"}` |
| 400 | `{"error": "Пароль должен содержать минимум 6 символов"}` |
| 401 | `{"error": "Срок действия reset_token истёк. Запросите код заново."}` |
| 401 | `{"error": "Недействительный reset_token"}` |
| 401 | `{"error": "Reset token недействителен или уже использован"}` |

---

## Профиль

### GET `/profile/`

Получить полные данные своего профиля.

**Headers:** `Authorization: Bearer <token>`

```json
// 200 — успех
{
    "id": "users/mMplMaUG...",
    "username": "john_doe",
    "fullname": "John Doe",
    "email": "john@example.com",
    "phone_number": "+992991234567",
    "date_of_birth": "2000-01-15",
    "status": "Student",
    "verification_status": "Approved",
    "group_id": "AbCdEf123",
    "avatar": "https://drive.google.com/uc?id=...",
    "date_joined": "2025-01-10 08:00:00"
}
```

> `group_id` — Firestore-ID группы. Имя группы здесь не возвращается.

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 401 | `{"error": "Токен не предоставлен"}` |
| 404 | `{"error": "Пользователь не найден"}` |

---

### PATCH `/profile/update/`

Обновление данных профиля. Передавайте только изменяемые поля.

**Headers:** `Authorization: Bearer <token>`

**Body (JSON):**

| Поле | Тип | Описание |
|------|-----|----------|
| `username` | string | Новый логин (должен быть уникальным) |
| `email` | string | Новый email |
| `phone_number` | string | Новый телефон, формат `+992XXXXXXXXX` |
| `check_password` | string | Текущий пароль — **обязательно при смене пароля** |
| `password` | string | Новый пароль |

```json
// Запрос (пример — смена пароля)
{
    "check_password": "текущий_пароль",
    "password": "новый_пароль"
}

// 200 — успех
{
    "message": "Профиль обновлён",
    "updated_fields": ["username", "email"],
    "token": "eyJhbGci..."
}
```

> Возвращается **новый токен** — сохраните его вместо старого (особенно важно при смене `username`).

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Нет данных для обновления"}` |
| 400 | `{"error": "Username не может быть пустым"}` |
| 400 | `{"error": "Пользователь с таким username уже существует"}` |
| 400 | `{"error": "Номер должен начинаться с '+992' и содержать 9 цифр после него."}` |
| 400 | `{"error": "Для смены пароля укажите текущий пароль в поле 'check_password'"}` |
| 400 | `{"error": "Неверный текущий пароль"}` |
| 401 | `{"error": "Токен не предоставлен"}` |
| 404 | `{"error": "Пользователь не найден"}` |

---

### POST `/profile/email/resend-code/`

Повторно отправляет 6-значный код подтверждения на email текущего пользователя (например, после смены почты через `/profile/update/`). Эндпоинт авторизованный, поэтому, в отличие от `/register/resend-code/`, отвечает честно: код отправлен, email уже подтверждён или сработал лимит повторной отправки.

**Headers:** `Authorization: Bearer <token>`

**Body:** не требуется.

```json
// 200 — код отправлен
{
    "message": "Код отправлен на user@example.com. Код действует 15 минут. Подтвердите email через /users/register/verify/."
}
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Email уже подтверждён, отправка кода не требуется."}` |
| 400 | `{"error": "У профиля не указан email. Сначала укажите почту через /users/profile/update/."}` |
| 401 | `{"error": "Токен не предоставлен"}` |
| 404 | `{"error": "Пользователь не найден"}` |
| 429 | `{"error": "Код уже отправлен. Повторная отправка возможна через 10 мин.", "retry_after_seconds": 600}` |

> Повторная отправка — не чаще раза в 10 минут. При 429 используйте `retry_after_seconds` для таймера на фронтенде.

---

### POST `/profile/avatar/`

Загрузить новый аватар. Старый файл удаляется с Google Drive автоматически.

**Headers:** `Authorization: Bearer <token>`

**Body (multipart/form-data):**

| Поле | Тип | Ограничения |
|------|-----|-------------|
| `avatar` | File | JPEG / PNG / WEBP, максимум **3 МБ** |

```json
// 200 — успех
{
    "message": "Аватар успешно обновлён",
    "avatar": "https://drive.google.com/uc?id=..."
}
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Файл не передан. Используйте поле \"avatar\""}` |
| 400 | `{"error": "Недопустимый формат. Разрешены: JPEG, PNG, WEBP"}` |
| 400 | `{"error": "Файл слишком большой. Максимум 3 МБ"}` |
| 401 | `{"error": "Токен не предоставлен"}` |
| 404 | `{"error": "Пользователь не найден"}` |
| 502 | `{"error": "Ошибка загрузки на Google Drive: ..."}` |

---

## Администратор

> Все эндпоинты этого раздела требуют `status = Admin`.

### GET `/admin/users/`

Список всех пользователей. Поддерживается фильтрация — только **один** параметр за раз.

> Для получения ожидающих верификации используйте `?verification_status=Pending`.

**Headers:** `Authorization: Bearer <admin_token>`

**Query параметры (необязательные):**

| Параметр | Допустимые значения | Пример |
|----------|---------------------|--------|
| `status` | `Student` `Teacher` `Admin` `Guest` | `?status=Student` |
| `verification_status` | `Pending` `Approved` `Rejected` | `?verification_status=Pending` |
| `group_id` | Firestore ID группы | `?group_id=AbCdEf123` |

> Без параметров — возвращаются все пользователи (до 500).

```json
// 200 — успех
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
            "group_id": "AbCdEf123",
            "group": "CS-101",
            "avatar": "https://drive.google.com/uc?id=...",
            "date_joined": "2025-01-10 08:00:00"
        }
    ]
}
```

---

### POST `/admin/users/create/`

Создать нового пользователя вручную. Создаётся с `verification_status = Approved`.

**Headers:** `Authorization: Bearer <admin_token>`

**Body (JSON):**

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
| `group_id` | string | ❌ | Firestore ID группы (альтернатива `group`) |
| `avatar` | string | ❌ | URL аватара (по умолчанию — стандартный аватар) |

> Если переданы оба поля `group` и `group_id` — приоритет у `group_id`.

```json
// Запрос
{
    "username": "john_doe",
    "password": "MyPassword123",
    "email": "john@example.com",
    "phone_number": "+992991234567",
    "fullname": "John Doe",
    "status": "Student",
    "group": "CS-101"
}

// 201 — успех
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
        "group_id": "AbCdEf123",
        "group": "CS-101",
        "avatar": "https://drive.google.com/uc?id=...",
        "date_joined": "2026-06-22 10:00:00"
    }
}
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Поле \"email\" обязательно"}` |
| 400 | `{"error": "Номер должен начинаться с '+992' и содержать 9 цифр после него."}` |
| 400 | `{"error": "Пользователь с таким username уже существует"}` |
| 400 | `{"error": "Допустимые статусы: Student, Teacher, Admin, Guest"}` |
| 404 | `{"error": "Группа не найдена"}` |
| 404 | `{"error": "Группа \"CS-999\" не найдена"}` |

---

### GET `/admin/users/<user_id>/`

Получить подробные данные одного пользователя по ID. Возвращает расширенный объект: дополнительно включает `date_of_birth` и `device_token`.

**Headers:** `Authorization: Bearer <admin_token>`

**URL параметр:** `user_id` — Firestore ID без префикса `users/`

```json
// 200 — успех
{
    "user": {
        "id": "users/mMplMaUG...",
        "username": "john_doe",
        "fullname": "John Doe",
        "email": "john@example.com",
        "phone_number": "+992991234567",
        "status": "Student",
        "verification_status": "Approved",
        "group_id": "AbCdEf123",
        "group": "CS-101",
        "avatar": "https://drive.google.com/uc?id=...",
        "date_joined": "2025-01-10 08:00:00",
        "date_of_birth": "2000-01-15",
        "device_token": "fcm_token_устройства"
    }
}

// 404
{ "error": "Пользователь не найден" }
```

---

### PATCH `/admin/users/<user_id>/edit/`

Редактировать данные любого пользователя. Все поля необязательные.

**Headers:** `Authorization: Bearer <admin_token>`

**Body (JSON):**

| Поле | Тип | Описание |
|------|-----|----------|
| `fullname` | string | ФИО |
| `email` | string | Email |
| `phone_number` | string | Телефон, формат `+992XXXXXXXXX` |
| `date_of_birth` | string | Дата рождения |
| `status` | string | `Student` / `Teacher` / `Admin` / `Guest` |
| `verification_status` | string | `Pending` / `Approved` / `Rejected` |
| `group` | string | Имя группы, например `"CS-101"` |
| `group_id` | string | Firestore ID группы (альтернатива `group`) |
| `password` | string | Новый пароль (без подтверждения — только для Admin) |

> Если переданы оба поля `group` и `group_id` — приоритет у `group_id`.  
> Передайте `"group": ""` или `"group_id": ""` чтобы убрать пользователя из группы.

```json
// Запрос
{
    "fullname": "Новое Имя",
    "status": "Teacher",
    "group": "CS-102"
}

// 200 — успех
{
    "message": "Данные пользователя обновлены",
    "updated_fields": ["fullname", "status", "group"],
    "user": {
        "id": "users/mMplMaUG...",
        "username": "john_doe",
        "fullname": "Новое Имя",
        "email": "john@example.com",
        "phone_number": "+992991234567",
        "status": "Teacher",
        "verification_status": "Approved",
        "group_id": "BbCcDdEe...",
        "group": "CS-102",
        "avatar": "https://drive.google.com/uc?id=...",
        "date_joined": "2025-01-10 08:00:00"
    }
}
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Нет данных для обновления"}` |
| 400 | `{"error": "Номер должен начинаться с '+992' и содержать 9 цифр после него."}` |
| 400 | `{"error": "Допустимые статусы: Student, Teacher, Admin, Guest"}` |
| 400 | `{"error": "Допустимые значения: Pending, Approved, Rejected"}` |
| 400 | `{"error": "Пароль не может быть пустым"}` |
| 404 | `{"error": "Пользователь не найден"}` |
| 404 | `{"error": "Группа не найдена"}` |
| 404 | `{"error": "Группа \"CS-999\" не найдена"}` |

---

### POST `/admin/users/<user_id>/avatar/`

Заменить аватар любого пользователя. Старый файл удаляется с Google Drive автоматически.

**Headers:** `Authorization: Bearer <admin_token>`

**Body (multipart/form-data):**

| Поле | Тип | Ограничения |
|------|-----|-------------|
| `avatar` | File | JPEG / PNG / WEBP, максимум **3 МБ** |

```json
// 200 — успех
{
    "message": "Аватар пользователя \"john_doe\" успешно обновлён",
    "avatar": "https://drive.google.com/uc?id=..."
}
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Файл не передан. Используйте поле \"avatar\""}` |
| 400 | `{"error": "Недопустимый формат. Разрешены: JPEG, PNG, WEBP"}` |
| 400 | `{"error": "Файл слишком большой. Максимум 3 МБ"}` |
| 403 | `{"error": "Доступ запрещён. Требуются права администратора."}` |
| 404 | `{"error": "Пользователь не найден"}` |
| 502 | `{"error": "Ошибка загрузки на Google Drive: ..."}` |

---

### POST `/admin/verify/<user_id>/`

Подтвердить или отклонить верификацию пользователя.

- `approve` → `verification_status = Approved`, `status = Student`
- `reject` → `verification_status = Rejected` (status не меняется)

**Headers:** `Authorization: Bearer <admin_token>`

**Body (JSON):**

```json
{ "action": "approve" }
```

```json
{ "action": "reject" }
```

```json
// 200 — approve
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
        "group_id": "",
        "group": "",
        "avatar": "https://drive.google.com/uc?id=...",
        "date_joined": "2026-06-20 12:00:00"
    }
}

// 200 — reject
{
    "message": "Пользователь отклонён.",
    "user": { "..." }
}
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Поле \"action\" должно быть \"approve\" или \"reject\""}` |
| 404 | `{"error": "Пользователь не найден"}` |

---

### POST `/admin/set-status/<user_id>/`

Напрямую назначить статус пользователю. `verification_status` не изменяется.

**Headers:** `Authorization: Bearer <admin_token>`

**Body (JSON):**

```json
{ "status": "Teacher" }
```

Допустимые значения: `Student`, `Teacher`, `Admin`, `Guest`

```json
// 200 — успех
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
        "group_id": "AbCdEf123",
        "group": "CS-101",
        "avatar": "https://drive.google.com/uc?id=...",
        "date_joined": "2025-01-10 08:00:00"
    }
}
```

**Ошибки:**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Допустимые статусы: Student, Teacher, Admin, Guest"}` |
| 404 | `{"error": "Пользователь не найден"}` |

---

## Массовая загрузка студентов

### GET `/admin/students/import/template/`

Скачать готовый шаблон Excel для заполнения.

**Headers:** `Authorization: Bearer <admin_token>`

**Ответ:** файл `students_import_template.xlsx` (не JSON)

| Колонка | Пример значения |
|---------|-----------------|
| ФИО | Иванов Иван Иванович |
| Email | ivan@example.com |
| Телефон | +992991234567 |
| Дата рождения | 2003-05-20 |
| Группа | CS-101 |

> **Как сохранить в Postman:** Send → **Save Response** → **Save to file**

---

### POST `/admin/students/import/`

Загрузить Excel-файл со списком студентов. Для каждой строки автоматически создаётся аккаунт с уникальными `username` и `password`.

**Headers:** `Authorization: Bearer <admin_token>`

**Body (multipart/form-data):**

| Поле | Тип | Описание |
|------|-----|----------|
| `file` | File | Файл `.xlsx` со списком студентов |

**Поддерживаемые заголовки колонок (регистр не важен):**

| Поле | Принимаемые названия колонок |
|------|------------------------------|
| ФИО | `ФИО`, `Имя`, `Полное имя`, `Full Name`, `Name`, `Имя Фамилия` |
| Email | `Email`, `Почта`, `E-mail`, `Эл. почта`, `Электронная почта` |
| Телефон | `Телефон`, `Номер`, `Phone Number`, `Тел`, `Моб` |
| Дата рождения | `Дата рождения`, `Дата`, `Birth`, `Д.р.`, `Date of Birth/생년월일` |
| Группа | `Группа`, `Group`, `Учебная группа`, `Класс` |

> Телефон нормализуется автоматически: `(+992) 900 00 0000` → `+992900000000`

**Ответ:** файл `students_credentials.xlsx` (не JSON)

Колонки результата:

| № | ФИО | Email | Телефон | Группа | Username | Password | Статус | Примечание |
|---|-----|-------|---------|--------|----------|----------|--------|------------|
| 1 | Иванов Иван | ivan@... | +992991234567 | CS-101 | **ivan_4821** | **Kd7mNpQ2xR** | Успешно | |
| 2 | Петров Пётр | ... | ... | CS-999 | | | Ошибка | Группа не найдена |

В конце файла: `Итого: 50 строк | Успешно: 48 | Ошибок: 2`

> Созданные студенты получают: `status = Student`, `verification_status = Approved`  
> `username` генерируется из первого слова ФИО + транслитерация + случайные цифры: `ivan_4821`  
> `password` генерируется криптографически стойко: минимум 1 заглавная, 1 строчная, 1 цифра

> **Как сохранить в Postman:** Send → **Save Response** → **Save to file**

**Ошибки (JSON):**

| Код | Ответ |
|-----|-------|
| 400 | `{"error": "Файл не передан. Используйте поле \"file\""}` |
| 400 | `{"error": "Разрешён только формат .xlsx"}` |
| 400 | `{"error": "Не удалось открыть файл. Убедитесь что это корректный .xlsx"}` |
| 400 | `{"error": "Файл пустой или содержит только заголовок"}` |
| 400 | `{"error": "Не найдены известные заголовки. Ожидаются: ФИО, Email, Телефон, Группа, Дата рождения"}` |

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

## Примеры запросов (Postman)

### Регистрация
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

### Вход с device_token
```
POST http://127.0.0.1:8000/api/users/login/
Content-Type: application/json

{
    "username": "test_user",
    "password": "Test1234",
    "device_token": "fcm_token_с_устройства"
}
```

### Мой профиль
```
GET http://127.0.0.1:8000/api/users/profile/
Authorization: Bearer <token>
```

### Изменить пароль
```
PATCH http://127.0.0.1:8000/api/users/profile/update/
Authorization: Bearer <token>
Content-Type: application/json

{
    "check_password": "Test1234",
    "password": "NewPass5678"
}
```

### Сменить аватар
```
POST http://127.0.0.1:8000/api/users/profile/avatar/
Authorization: Bearer <token>
Content-Type: multipart/form-data

avatar: [выбрать файл]
```

### Список студентов
```
GET http://127.0.0.1:8000/api/users/admin/users/?status=Student
Authorization: Bearer <admin_token>
```

### Список ожидающих верификации
```
GET http://127.0.0.1:8000/api/users/admin/users/?verification_status=Pending
Authorization: Bearer <admin_token>
```

### Подтвердить пользователя
```
POST http://127.0.0.1:8000/api/users/admin/verify/mMplMaUG.../
Authorization: Bearer <admin_token>
Content-Type: application/json

{ "action": "approve" }
```

### Назначить преподавателя
```
POST http://127.0.0.1:8000/api/users/admin/set-status/mMplMaUG.../
Authorization: Bearer <admin_token>
Content-Type: application/json

{ "status": "Teacher" }
```

### Создать студента вручную
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

### Скачать шаблон для импорта
```
GET http://127.0.0.1:8000/api/users/admin/students/import/template/
Authorization: Bearer <admin_token>
```

### Массовый импорт студентов
```
POST http://127.0.0.1:8000/api/users/admin/students/import/
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data

file: [students.xlsx]
```
