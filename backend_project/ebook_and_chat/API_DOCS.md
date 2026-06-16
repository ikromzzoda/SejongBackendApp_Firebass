# E-Library API Documentation

Base URL: `/api/books/`

Все эндпоинты требуют заголовок:
```
Authorization: Bearer <JWT-токен>
```

---

## Публичные эндпоинты (доступны всем авторизованным пользователям)

---

### GET `/api/books/` — Список книг

Возвращает все книги. Поддерживает фильтрацию по жанру.

**Query параметры (необязательные):**

| Параметр | Тип    | Описание                                      |
|----------|--------|-----------------------------------------------|
| `genres` | string | Фильтр по жанру (одно из допустимых значений) |

**Допустимые значения `genres`:**
- `Книги Sejong`
- `Книги Topik`
- `Художественная литература`

**Пример запроса:**
```
GET /api/books/?genres=Книги Sejong
Authorization: Bearer <token>
```

**Ответ `200 OK`:**
```json
{
    "total": 2,
    "books": [
        {
            "id": "abc123",
            "title_taj": "Забони кореӣ",
            "title_rus": "Корейский язык",
            "title_eng": "Korean Language",
            "title_kor": "한국어",
            "description_taj": "...",
            "description_rus": "...",
            "description_eng": "...",
            "description_kor": "...",
            "author": "Иванов И.И.",
            "genres": "Книги Sejong",
            "published_date": "2024-01-01",
            "created_at": "2025-06-16 10:00:00",
            "cover": "https://drive.google.com/uc?id=COVER_ID",
            "cover_id": "COVER_ID",
            "file": "https://drive.google.com/uc?id=FILE_ID",
            "file_id": "FILE_ID"
        }
    ]
}
```

---

### GET `/api/books/<book_id>/` — Получить книгу

Возвращает одну книгу по ID.

**Пример запроса:**
```
GET /api/books/abc123/
Authorization: Bearer <token>
```

**Ответ `200 OK`:**
```json
{
    "book": {
        "id": "abc123",
        "title_taj": "Забони кореӣ",
        "title_rus": "Корейский язык",
        "title_eng": "Korean Language",
        "title_kor": "한국어",
        "description_taj": "...",
        "description_rus": "...",
        "description_eng": "...",
        "description_kor": "...",
        "author": "Иванов И.И.",
        "genres": "Книги Sejong",
        "published_date": "2024-01-01",
        "created_at": "2025-06-16 10:00:00",
        "cover": "https://drive.google.com/uc?id=COVER_ID",
        "cover_id": "COVER_ID",
        "file": "https://drive.google.com/uc?id=FILE_ID",
        "file_id": "FILE_ID"
    }
}
```

**Ответ `404 Not Found`:**
```json
{
    "error": "Книга не найдена"
}
```

---

## Административные эндпоинты (только для Admin)

---

### POST `/api/books/admin/create/` — Создать книгу

Загружает файл книги и обложку на Google Drive, сохраняет метаданные в Firestore.

**Метод:** `POST`  
**Тип тела:** `multipart/form-data`

**Поля запроса:**

| Поле              | Тип    | Обяз. | Описание                                     |
|-------------------|--------|-------|----------------------------------------------|
| `title_rus`       | text   | ✅    | Название на русском                          |
| `title_taj`       | text   | ❌    | Название на таджикском                       |
| `title_eng`       | text   | ❌    | Название на английском                       |
| `title_kor`       | text   | ❌    | Название на корейском                        |
| `description_rus` | text   | ❌    | Описание на русском                          |
| `description_taj` | text   | ❌    | Описание на таджикском                       |
| `description_eng` | text   | ❌    | Описание на английском                       |
| `description_kor` | text   | ❌    | Описание на корейском                        |
| `author`          | text   | ❌    | Автор книги                                  |
| `genres`          | text   | ❌    | Жанр (одно из допустимых значений)           |
| `published_date`  | text   | ❌    | Дата публикации (формат: `YYYY-MM-DD`)       |
| `file`            | file   | ✅    | Файл книги (PDF или EPUB, макс. 100 МБ)     |
| `cover`           | file   | ❌    | Обложка (JPEG / PNG / WEBP, макс. 2 МБ)    |

**Допустимые значения `genres`:**
- `Книги Sejong`
- `Книги Topik`
- `Художественная литература`

**Пример запроса (Postman):**
```
POST /api/books/admin/create/
Authorization: Bearer <admin-token>
Content-Type: multipart/form-data

title_rus     = Корейский язык для начинающих
title_eng     = Korean for Beginners
author        = Ким Чжи Су
genres        = Книги Sejong
published_date = 2024-03-15
file          = [PDF файл]
cover         = [JPEG файл]
```

**Ответ `201 Created`:**
```json
{
    "message": "Книга успешно добавлена",
    "book": {
        "id": "abc123",
        "title_rus": "Корейский язык для начинающих",
        "title_eng": "Korean for Beginners",
        "title_taj": "",
        "title_kor": "",
        "description_rus": "",
        "description_taj": "",
        "description_eng": "",
        "description_kor": "",
        "author": "Ким Чжи Су",
        "genres": "Книги Sejong",
        "published_date": "2024-03-15",
        "created_at": "2025-06-16 10:00:00",
        "cover": "https://drive.google.com/uc?id=COVER_ID",
        "cover_id": "COVER_ID",
        "file": "https://drive.google.com/uc?id=FILE_ID",
        "file_id": "FILE_ID"
    }
}
```

**Ошибки:**

| Код | Описание                                      |
|-----|-----------------------------------------------|
| 400 | Отсутствует `title_rus` или `file`            |
| 400 | Неверный формат файла или размер превышен     |
| 400 | Недопустимое значение жанра                   |
| 401 | Токен не предоставлен или истёк               |
| 403 | Нет прав администратора                       |
| 502 | Ошибка загрузки файла на Google Drive         |

---

### PATCH `/api/books/admin/<book_id>/edit/` — Редактировать книгу

Обновляет метаданные и/или заменяет файлы. Старые файлы на Drive удаляются автоматически.

**Метод:** `PATCH`  
**Тип тела:** `multipart/form-data`

Все поля необязательные. Передавай только те, что нужно изменить.

**Поля запроса:** те же что и при создании, кроме — `file` и `cover` здесь заменяют существующие файлы.

**Пример запроса:**
```
PATCH /api/books/admin/abc123/edit/
Authorization: Bearer <admin-token>
Content-Type: multipart/form-data

title_rus = Обновлённое название
cover     = [новое изображение]
```

**Ответ `200 OK`:**
```json
{
    "message": "Книга обновлена",
    "updated_fields": ["title_rus", "cover", "cover_id"],
    "book": { ... }
}
```

**Ошибки:**

| Код | Описание                                  |
|-----|-------------------------------------------|
| 400 | Нет данных для обновления                 |
| 400 | Неверный формат файла или размер превышен |
| 401 | Токен не предоставлен или истёк           |
| 403 | Нет прав администратора                   |
| 404 | Книга не найдена                          |
| 502 | Ошибка загрузки файла на Google Drive     |

---

### DELETE `/api/books/admin/<book_id>/delete/` — Удалить книгу

Удаляет книгу из Firestore и оба файла (обложку и PDF) с Google Drive.

**Пример запроса:**
```
DELETE /api/books/admin/abc123/delete/
Authorization: Bearer <admin-token>
```

**Ответ `200 OK`:**
```json
{
    "message": "Книга удалена"
}
```

**Ошибки:**

| Код | Описание                        |
|-----|---------------------------------|
| 401 | Токен не предоставлен или истёк |
| 403 | Нет прав администратора         |
| 404 | Книга не найдена                |

---

## Структура объекта Book

| Поле              | Тип    | Описание                                     |
|-------------------|--------|----------------------------------------------|
| `id`              | string | Уникальный ID документа в Firestore          |
| `title_taj`       | string | Название на таджикском                       |
| `title_rus`       | string | Название на русском                          |
| `title_eng`       | string | Название на английском                       |
| `title_kor`       | string | Название на корейском                        |
| `description_taj` | string | Описание на таджикском                       |
| `description_rus` | string | Описание на русском                          |
| `description_eng` | string | Описание на английском                       |
| `description_kor` | string | Описание на корейском                        |
| `author`          | string | Автор                                        |
| `genres`          | string | Жанр                                         |
| `published_date`  | string | Дата публикации (`YYYY-MM-DD`)               |
| `created_at`      | string | Дата добавления в систему                    |
| `cover`           | string | Публичный URL обложки на Google Drive        |
| `cover_id`        | string | Google Drive file ID обложки                 |
| `file`            | string | Публичный URL файла книги на Google Drive    |
| `file_id`         | string | Google Drive file ID файла книги             |
