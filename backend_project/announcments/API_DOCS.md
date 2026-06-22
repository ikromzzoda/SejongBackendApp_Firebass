# API Documentation — Announcements App

**Base URL:** `http://127.0.0.1:8000/api/announcements`

---

## Аутентификация

```
Authorization: Bearer <token>
```

| Уровень доступа | Эндпоинты |
|-----------------|-----------|
| Admin | Все `/admin/*` |
| Любой авторизованный | `GET /`, `GET /<id>/` |

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
| GET | `/` | Авторизованный | Список всех объявлений |
| GET | `/<id>/` | Авторизованный | Получить объявление |
| POST | `/admin/create/` | Admin | Создать объявление |
| PATCH | `/admin/<id>/edit/` | Admin | Редактировать объявление |
| DELETE | `/admin/<id>/delete/` | Admin | Удалить объявление |

---

## Объект объявления

```json
{
    "id": "announcements/AbCdEf123",
    "title_taj": "Эълон",
    "title_rus": "Объявление",
    "title_eng": "Announcement",
    "title_kor": "공지사항",
    "content_taj": "Матни эълон",
    "content_rus": "Текст объявления",
    "content_eng": "Announcement text",
    "content_kor": "공지사항 내용",
    "images": [
        { "file_id": "1A2B3C4D", "url": "https://drive.google.com/uc?id=1A2B3C4D" }
    ],
    "time_posted": "2026-06-15 10:30:00+00:00",
    "author": "admin_username"
}
```

> Поля `title_*` / `content_*` — мультиязычные: `taj`=таджикский, `rus`=русский, `eng`=английский, `kor`=корейский.  
> `images` — список изображений, загруженных на Google Drive.  
> `time_posted` — устанавливается автоматически при создании.  
> `author` — `username` администратора из JWT.

---

## GET `/`

Список всех объявлений (до 200 штук).

```json
// 200 — успех
{
    "total": 2,
    "announcements": [ { ... } ]
}
```

---

## GET `/<ann_id>/`

Получить одно объявление по ID.

```json
// 200 — успех
{ "announcement": { ... } }

// 404
{ "error": "Объявление не найдено" }
```

---

## POST `/admin/create/`

Создать новое объявление. После сохранения бэкенд автоматически:
1. Создаёт запись `Notification` с теми же данными
2. Отправляет FCM push-уведомление **всем** пользователям (Guest, Student, Teacher, Admin)

**Content-Type:** `multipart/form-data`

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `title_taj` | string | ❌ | Заголовок (таджикский) |
| `title_rus` | string | ✅* | Заголовок (русский) |
| `title_eng` | string | ❌ | Заголовок (английский) |
| `title_kor` | string | ❌ | Заголовок (корейский) |
| `content_taj` | string | ❌ | Текст (таджикский) |
| `content_rus` | string | ❌ | Текст (русский) |
| `content_eng` | string | ❌ | Текст (английский) |
| `content_kor` | string | ❌ | Текст (корейский) |
| `images` | File[] | ❌ | JPEG / PNG / WEBP, до 2 МБ каждый, максимум 10 файлов |

> \* Хотя бы одно из полей `title_rus` или `title_taj` обязательно.

```json
// 201 — успех
{
    "message": "Объявление успешно создано",
    "announcement": { ... }
}
```

**Ошибки:**

| Код | Описание | Ответ |
|-----|----------|-------|
| 400 | Не передан ни один заголовок | `{"error": "Хотя бы одно поле заголовка обязательно (title_rus или title_taj)"}` |
| 400 | Превышен лимит изображений | `{"error": "Максимум 10 изображений"}` |
| 400 | Недопустимый формат файла | `{"error": "Допустимые форматы изображений: JPEG, PNG, WEBP"}` |
| 400 | Изображение слишком большое | `{"error": "Изображение слишком большое. Максимум 2 МБ"}` |
| 502 | Ошибка загрузки на Google Drive | `{"error": "Ошибка загрузки изображения на Google Drive: ..."}` |

---

## PATCH `/admin/<ann_id>/edit/`

Редактировать объявление. Передаются только изменяемые поля.

> **Изображения:** при передаче поля `images` все старые изображения удаляются с Google Drive и заменяются новыми. Чтобы оставить текущие изображения без изменений — поле `images` не передавать.

**Content-Type:** `multipart/form-data`

```json
// 200 — успех
{
    "message": "Объявление обновлено",
    "updated_fields": ["title_rus", "content_rus", "images"],
    "announcement": { ... }
}
```

**Ошибки:**

| Код | Описание | Ответ |
|-----|----------|-------|
| 400 | Нет данных для обновления | `{"message": "Нет данных для обновления"}` |
| 400 | Превышен лимит изображений | `{"error": "Максимум 10 изображений"}` |
| 400 | Недопустимый формат / размер | см. ошибки создания |
| 404 | Объявление не найдено | `{"error": "Объявление не найдено"}` |
| 502 | Ошибка загрузки на Google Drive | `{"error": "Ошибка загрузки изображения на Google Drive: ..."}` |

---

## DELETE `/admin/<ann_id>/delete/`

Удалить объявление. Все прикреплённые изображения автоматически удаляются с Google Drive.

```json
// 200 — успех
{ "message": "Объявление удалено" }

// 404
{ "error": "Объявление не найдено" }
```

---

## Хранение изображений

Изображения загружаются на Google Drive по пути:
```
My Drive / Sejong Cloud / announcement / images /
```

Каждый элемент массива `images` содержит:
- `file_id` — ID файла на Google Drive (используется для удаления)
- `url` — публичный URL вида `https://drive.google.com/uc?id=<file_id>`

---

## FCM Push-уведомления

При создании объявления бэкенд автоматически отправляет FCM push **всем** пользователям независимо от их статуса.

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

**Шаг 3.** Токен сохраняется в Firestore. При создании объявления бэкенд находит `device_token` всех пользователей и отправляет push каждому.

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

### Список объявлений
```
GET http://127.0.0.1:8000/api/announcements/
Authorization: Bearer <token>
```

### Создать объявление (с изображениями)
```
POST http://127.0.0.1:8000/api/announcements/admin/create/
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data

title_rus=Новое объявление
title_taj=Эълони нав
content_rus=Текст нового объявления
content_eng=New announcement text
images=<file1.jpg>
images=<file2.png>
```

### Редактировать объявление
```
PATCH http://127.0.0.1:8000/api/announcements/admin/AbCdEf123/edit/
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data

title_rus=Обновлённый заголовок
content_rus=Обновлённый текст
```

### Удалить объявление
```
DELETE http://127.0.0.1:8000/api/announcements/admin/AbCdEf123/delete/
Authorization: Bearer <admin_token>
```
