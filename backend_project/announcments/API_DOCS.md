# Announcements API

Base URL: `/api/announcements/`

All endpoints require a JWT token in the `Authorization` header:
```
Authorization: Bearer <token>
```

---

## Endpoints Overview

| Method | URL | Access | Description |
|--------|-----|--------|-------------|
| GET | `/api/announcements/` | Any authenticated user | List all announcements |
| GET | `/api/announcements/{id}/` | Any authenticated user | Get single announcement |
| POST | `/api/announcements/admin/create/` | Admin only | Create announcement |
| PATCH | `/api/announcements/admin/{id}/edit/` | Admin only | Edit announcement |
| DELETE | `/api/announcements/admin/{id}/delete/` | Admin only | Delete announcement |

---

## 1. List Announcements

**GET** `/api/announcements/`

Returns all announcements (up to 200).

### Request

```
GET /api/announcements/
Authorization: Bearer <token>
```

### Response `200 OK`

```json
{
  "total": 2,
  "announcements": [
    {
      "id": "abc123",
      "title_taj": "Эълон",
      "title_rus": "Объявление",
      "title_eng": "Announcement",
      "title_kor": "공지사항",
      "content_taj": "Матни эълон",
      "content_rus": "Текст объявления",
      "content_eng": "Announcement text",
      "content_kor": "공지사항 내용",
      "images": [
        {
          "file_id": "1A2B3C4D",
          "url": "https://drive.google.com/uc?id=1A2B3C4D"
        }
      ],
      "time_posted": "2026-06-15 10:30:00+00:00",
      "author": "admin_username"
    }
  ]
}
```

---

## 2. Get Single Announcement

**GET** `/api/announcements/{id}/`

### Request

```
GET /api/announcements/abc123/
Authorization: Bearer <token>
```

### Response `200 OK`

```json
{
  "announcement": {
    "id": "abc123",
    "title_taj": "Эълон",
    "title_rus": "Объявление",
    "title_eng": "Announcement",
    "title_kor": "공지사항",
    "content_taj": "Матни эълон",
    "content_rus": "Текст объявления",
    "content_eng": "Announcement text",
    "content_kor": "공지사항 내용",
    "images": [
      {
        "file_id": "1A2B3C4D",
        "url": "https://drive.google.com/uc?id=1A2B3C4D"
      }
    ],
    "time_posted": "2026-06-15 10:30:00+00:00",
    "author": "admin_username"
  }
}
```

### Response `404 Not Found`

```json
{
  "error": "Объявление не найдено"
}
```

---

## 3. Create Announcement

**POST** `/api/announcements/admin/create/`

**Content-Type:** `multipart/form-data`

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title_taj` | string | — | Title in Tajik |
| `title_rus` | string | * | Title in Russian |
| `title_eng` | string | — | Title in English |
| `title_kor` | string | — | Title in Korean |
| `content_taj` | string | — | Content in Tajik |
| `content_rus` | string | — | Content in Russian |
| `content_eng` | string | — | Content in English |
| `content_kor` | string | — | Content in Korean |
| `images` | file[] | — | Images (JPEG/PNG/WEBP, max 2 MB each, max 10 files) |

> \* At least one of `title_rus` or `title_taj` is required.

### Request Example

```
POST /api/announcements/admin/create/
Authorization: Bearer <token>
Content-Type: multipart/form-data

title_rus=Новое объявление
title_taj=Эълони нав
content_rus=Текст нового объявления
content_eng=New announcement text
images=<file1.jpg>
images=<file2.png>
```

### Response `201 Created`

```json
{
  "message": "Объявление успешно создано",
  "announcement": {
    "id": "abc123",
    "title_taj": "Эълони нав",
    "title_rus": "Новое объявление",
    "title_eng": "",
    "title_kor": "",
    "content_taj": "",
    "content_rus": "Текст нового объявления",
    "content_eng": "New announcement text",
    "content_kor": "",
    "images": [
      {
        "file_id": "1A2B3C4D",
        "url": "https://drive.google.com/uc?id=1A2B3C4D"
      },
      {
        "file_id": "5E6F7G8H",
        "url": "https://drive.google.com/uc?id=5E6F7G8H"
      }
    ],
    "time_posted": "2026-06-15 10:30:00+00:00",
    "author": "admin_username"
  }
}
```

### Error Responses

| Status | Condition | Response |
|--------|-----------|----------|
| `400` | No title provided | `{"error": "Хотя бы одно поле заголовка обязательно (title_rus или title_taj)"}` |
| `400` | More than 10 images | `{"error": "Максимум 10 изображений"}` |
| `400` | Wrong image format | `{"error": "Допустимые форматы изображений: JPEG, PNG, WEBP"}` |
| `400` | Image too large | `{"error": "Изображение слишком большое. Максимум 2 МБ"}` |
| `401` | Missing / invalid token | `{"error": "Токен не предоставлен"}` |
| `403` | User is not Admin | `{"error": "Доступ запрещён. Требуются права администратора."}` |
| `502` | Google Drive error | `{"error": "Ошибка загрузки изображения на Google Drive: ..."}` |

---

## 4. Edit Announcement

**PATCH** `/api/announcements/admin/{id}/edit/`

**Content-Type:** `multipart/form-data`

Send only the fields you want to update.

> **Note on images:** If `images` field is provided, **all previous images are replaced** with the new ones. To keep existing images, do not send the `images` field.

### Request Example

```
PATCH /api/announcements/admin/abc123/edit/
Authorization: Bearer <token>
Content-Type: multipart/form-data

title_rus=Обновлённый заголовок
content_rus=Обновлённый текст
images=<new_photo.jpg>
```

### Response `200 OK`

```json
{
  "message": "Объявление обновлено",
  "updated_fields": ["title_rus", "content_rus", "images"],
  "announcement": {
    "id": "abc123",
    "title_rus": "Обновлённый заголовок",
    "content_rus": "Обновлённый текст",
    "images": [
      {
        "file_id": "9I0J1K2L",
        "url": "https://drive.google.com/uc?id=9I0J1K2L"
      }
    ],
    "time_posted": "2026-06-15 10:30:00+00:00",
    "author": "admin_username"
  }
}
```

### Error Responses

| Status | Condition | Response |
|--------|-----------|----------|
| `400` | Nothing to update | `{"message": "Нет данных для обновления"}` |
| `404` | Announcement not found | `{"error": "Объявление не найдено"}` |

---

## 5. Delete Announcement

**DELETE** `/api/announcements/admin/{id}/delete/`

Deletes the announcement and removes all associated images from Google Drive.

### Request

```
DELETE /api/announcements/admin/abc123/delete/
Authorization: Bearer <token>
```

### Response `200 OK`

```json
{
  "message": "Объявление удалено"
}
```

### Response `404 Not Found`

```json
{
  "error": "Объявление не найдено"
}
```

---

## Image Storage

Images are stored in Google Drive at:
```
My Drive / Sejong Cloud / announcement / images /
```

Each image entry in the response contains:
- `file_id` — Google Drive file ID (used internally for deletion)
- `url` — Public URL: `https://drive.google.com/uc?id=<file_id>`

---

## Announcement Object Reference

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
| `images` | array | List of `{file_id, url}` objects |
| `time_posted` | string | ISO datetime, set automatically on creation |
| `author` | string | Username of the admin who created it |
