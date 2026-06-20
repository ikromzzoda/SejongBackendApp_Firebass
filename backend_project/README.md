# Sejong Backend

REST API backend for the **Sejong Korean Language Learning Platform**. Serves students, teachers, and administrators with course management, e-library, schedules, notifications, and announcements.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0.6 + Django REST Framework 3.17.1 |
| Business DB | Firebase Firestore (via FireO ORM) |
| Internal DB | SQLite (Django sessions/admin only) |
| File Storage | Google Drive API |
| Push Notifications | Firebase Cloud Messaging (FCM) |
| Deployment | Google Cloud Run (Docker) |
| Auth | JWT (HS256, 1-day lifetime) |

---

## Project Structure

```
backend_project/
├── config/                  # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── users/                   # User auth & profile management
├── groups/                  # Student group management
├── ebook_and_chat/          # E-library (books)
├── info/                    # Schedules & push notifications
├── announcments/            # Announcements
├── utils/
│   ├── jwt_utils.py         # JWT encode/decode
│   ├── decorators.py        # @jwt_required, @admin_required
│   ├── drive.py             # Google Drive upload/delete helpers
│   └── fcm.py               # Firebase Cloud Messaging sender
├── manage.py
├── requirements.txt
├── Dockerfile
├── .env                     # Local dev environment
└── .env.production.example  # Production template
```

---

## Setup

### Prerequisites

- Python 3.11+
- Firebase project with Firestore enabled
- Google Drive service account with Drive API enabled
- Two credential JSON files (Firebase + Google Drive)

### Local Development

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.production.example .env
# Fill in your values in .env

# 4. Apply Django migrations (SQLite only)
python manage.py migrate

# 5. Run development server
python manage.py runserver
```

### Environment Variables

| Variable | Description |
|---|---|
| `DEBUG` | `True` for dev, `False` for production |
| `SECRET_KEY` | Django secret key (used for JWT signing) |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `FIREBASE_CREDENTIALS` | Path to Firebase service account JSON |
| `GOOGLE_DRIVE_CREDENTIALS` | Path to Google Drive service account JSON |
| `GOOGLE_DRIVE_AVATAR_FOLDER_ID` | Drive folder ID for user avatars |
| `GOOGLE_DRIVE_BOOK_FILES_FOLDER_ID` | Drive folder ID for book files |
| `GOOGLE_DRIVE_BOOK_COVERS_FOLDER_ID` | Drive folder ID for book covers |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins (production) |

---

## Authentication

All protected endpoints require a JWT in the `Authorization` header:

```
Authorization: Bearer <token>
```

### User Roles

| Status | Description |
|---|---|
| `Guest` | Newly registered, awaiting approval |
| `Student` | Approved student |
| `Teacher` | Teacher account |
| `Admin` | Full administrative access |

### Verification States

| State | Description |
|---|---|
| `Pending` | Registration submitted, not reviewed |
| `Approved` | Access granted |
| `Rejected` | Access denied |

### Auth Decorators

| Decorator | Check |
|---|---|
| `@jwt_required` | Valid JWT + not blacklisted (Firestore lookup) |
| `@admin_required` | `@jwt_required` + `status == 'Admin'` |
| `@jwt_verify_only` | Signature-only check (no Firestore call, faster) |

Token revocation on logout stores the JTI in the `BlacklistedToken` Firestore collection (document ID = JTI for O(1) lookup).

---

## API Reference

Base URL: `/api/`

---

### Users — `/api/users/`

#### Public / Auth

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/register/` | — | Register new user (status=Guest, verification=Pending) |
| POST | `/login/` | — | Login, returns JWT token |
| POST | `/logout/` | JWT | Revoke token |

#### Profile

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/profile/` | JWT | Get own profile |
| POST | `/profile/update/` | JWT | Update own profile fields |
| POST | `/profile/avatar/` | JWT | Upload avatar (multipart) |

#### Admin — User Management

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/admin/users/` | Admin | List users; filters: `?status=`, `?verification_status=`, `?group_id=` |
| GET | `/admin/users/<user_id>/` | Admin | Get single user |
| POST | `/admin/users/create/` | Admin | Create user manually |
| PATCH | `/admin/users/<user_id>/edit/` | Admin | Edit user fields |
| GET | `/admin/pending/` | Admin | List users pending verification |
| POST | `/admin/verify/<user_id>/` | Admin | Approve or reject user |
| POST | `/admin/set-status/<user_id>/` | Admin | Change user role/status |

#### Admin — Bulk Import

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/admin/students/import/` | Admin | Import students from `.xlsx` file |
| GET | `/admin/students/import/template/` | Admin | Download import template |

Import columns: `ФИО`, `Email`, `Телефон`, `Дата рождения`, `Группа`. Returns result Excel with auto-generated usernames and passwords.

Phone format: `+992XXXXXXXXX` (Tajikistan).

---

### Groups — `/api/groups/`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/admin/` | Admin | List all groups |
| POST | `/admin/create/` | Admin | Create group |
| DELETE | `/admin/<group_id>/delete/` | Admin | Delete group |
| POST | `/admin/assign/<user_id>/` | Admin | Assign user to group |

---

### Books — `/api/books/`

#### Public

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | JWT | List books; optional filter: `?genres=` |
| GET | `/<book_id>/` | JWT | Get single book |

#### Admin

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/admin/create/` | Admin | Create book (multipart) |
| PATCH | `/admin/<book_id>/edit/` | Admin | Edit book |
| DELETE | `/admin/<book_id>/delete/` | Admin | Delete book (removes files from Drive) |

**Book fields**: `title_taj/rus/eng/kor`, `description_taj/rus/eng/kor`, `author`, `genres`, `published_date`, `file` (PDF/EPUB ≤100MB), `cover` (JPEG/PNG/WEBP ≤2MB).

Genres: `Книги Sejong`, `Книги Topik`, `Художественная литература`.

---

### Schedules — `/api/info/schedules/`

#### Admin

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/admin/schedules/` | Admin | List schedules; filters: `?group_name=`, `?teacher_name=` |
| POST | `/admin/schedules/create/` | Admin | Create schedule |
| GET | `/admin/schedules/<id>/` | Admin | Get single schedule |
| PATCH | `/admin/schedules/<id>/edit/` | Admin | Edit schedule |
| DELETE | `/admin/schedules/<id>/delete/` | Admin | Delete schedule |

#### Public

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/schedules/all/` | JWT | All schedules sorted by day |
| GET | `/schedules/group/<group_name>/` | JWT | Schedule for specific group |

**Schedule constraints**:
- `day`: 0–6 (Monday–Sunday)
- `start_time` / `end_time`: HH:MM format
- `classroom`: 301, 303, 306, 307, 308 only
- `book`: 1–8
- Max 1 class per day per group
- Max 6 days per group

---

### Notifications — `/api/info/notifications/`

#### Admin

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/admin/notifications/` | Admin | List notifications; filter: `?status=` |
| POST | `/admin/notifications/create/` | Admin | Create & send push notification (multipart) |
| GET | `/admin/notifications/<id>/` | Admin | Get single notification |
| PATCH | `/admin/notifications/<id>/edit/` | Admin | Edit notification |
| DELETE | `/admin/notifications/<id>/delete/` | Admin | Delete notification |

#### Public

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/notifications/` | JWT | Get notifications targeted at user's status |

**Notification fields**: `title_taj/rus/eng/kor`, `content_taj/rus/eng/kor`, `target_statuses` (array), `images` (up to 10 files).

Creating a notification automatically sends FCM push notifications to all users whose status matches `target_statuses`.

---

### Announcements — `/api/announcements/`

#### Public

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | JWT | List all announcements |
| GET | `/<ann_id>/` | JWT | Get single announcement |

#### Admin

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/admin/create/` | Admin | Create announcement (multipart) |
| PATCH | `/admin/<ann_id>/edit/` | Admin | Edit announcement |
| DELETE | `/admin/<ann_id>/delete/` | Admin | Delete announcement |

**Announcement fields**: `title_taj/rus/eng/kor`, `content_taj/rus/eng/kor`, `images` (up to 10 files). Author is set automatically from the JWT token.

---

## Firestore Collections

| Collection | Description |
|---|---|
| `User` | User accounts |
| `BlacklistedToken` | Revoked JWT tokens (doc ID = JTI) |
| `Group` | Student groups |
| `Book` | E-library books |
| `Schedule` | Class schedules |
| `Notification` | Push notifications |
| `Announcement` | Announcements |

---

## Google Drive Structure

```
Sejong Cloud/
├── users/                   # Avatars
├── book/
│   ├── covers/              # Book cover images
│   └── files/               # Book PDF/EPUB files
├── announcement/
│   └── images/              # Announcement images
└── notifications/
    └── images/              # Notification images
```

All uploaded files are set to public read permission. File URLs follow the format:
```
https://drive.google.com/uc?id=<file_id>
```

---

## Deployment

### Docker / Cloud Run

```bash
# Build image
docker build -t sejong-backend .

# Run locally
docker run -p 8080:8080 \
  -e SECRET_KEY=... \
  -e FIREBASE_CREDENTIALS=/secrets/firebase.json \
  -v /path/to/secrets:/secrets \
  sejong-backend
```

The Dockerfile uses Gunicorn with **2 workers × 8 threads**, 120s timeout.

### Production Environment

Mount credential files as Cloud Run secrets and set env vars per `.env.production.example`.

---

## Multilingual Support

All content models support four languages:

| Suffix | Language |
|---|---|
| `_taj` | Tajik |
| `_rus` | Russian |
| `_eng` | English |
| `_kor` | Korean |

Applies to: Book titles/descriptions, Notifications (title + content), Announcements (title + content).
