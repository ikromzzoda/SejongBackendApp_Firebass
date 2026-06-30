# API Documentation — Audit Logs App

**Base URL:** `http://127.0.0.1:8000/api/audit`

---

## Описание

Audit Logs — система журналирования действий администраторов. Каждый раз, когда администратор создаёт, изменяет или удаляет объект через API, запись автоматически сохраняется в коллекцию `audit_logs` Firestore.

**Максимум хранится 200 последних записей.** При превышении лимита самые старые логи удаляются автоматически.

---

## Аутентификация

```
Authorization: Bearer <token>
```

| Уровень доступа | Эндпоинты |
|-----------------|-----------|
| Admin | `GET /admin/logs/` |

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
| GET | `/admin/logs/` | Admin | Список логов с фильтрацией и пагинацией |

---

## Объект лога

```json
{
    "id": "audit_logs/AbCdEf123",
    "admin_user": "admin_username",
    "action": "create",
    "model_name": "User",
    "object_id": "users/XyZ789",
    "changes": {
        "username": "new_student",
        "status": "Student"
    },
    "timestamp": "2026-06-30 10:15:43+00:00"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string | ID записи в Firestore |
| `admin_user` | string | `username` администратора, выполнившего действие |
| `action` | string | Тип действия: `create`, `update`, `delete` |
| `model_name` | string | Название затронутой модели (см. таблицу ниже) |
| `object_id` | string | ID изменённого объекта в Firestore |
| `changes` | object | Детали изменений (зависят от действия и модели) |
| `timestamp` | string | Время события (UTC, устанавливается автоматически) |

---

## Что логируется

### Действия по моделям

| Модель | `model_name` | create | update | delete |
|--------|-------------|:---:|:---:|:---:|
| Пользователь | `User` | ✅ | ✅ | — |
| Группа | `Group` | ✅ | ✅ | ✅ |
| Объявление | `Announcement` | ✅ | ✅ | ✅ |
| Книга | `Book` | ✅ | ✅ | ✅ |
| Расписание | `Schedule` | ✅ | ✅ | ✅ |
| Уведомление | `Notification` | ✅ | ✅ | ✅ |
| Раздел политики | `PrivacySection` | ✅ | ✅ | ✅ |

### Поле `changes` по типу действия

**`action: "create"`**

```json
// User — создан вручную
{ "username": "john_doe", "status": "Student" }

// User — массовый импорт
{ "total": 50, "success": 48, "errors": 2 }

// Group
{ "name": "CS-101" }

// Announcement
{ "title_rus": "Важное объявление", "title_taj": "" }

// Book
{ "title_rus": "Python для начинающих", "genres": "IT" }

// Schedule
{ "group_name": "CS-101", "teacher_name": "Иванов Иван", "day": 1 }

// Notification
{ "title_rus": "Занятия отменены", "target_statuses": ["Student", "Teacher"] }

// PrivacySection
{ "title_rus": "Сбор данных", "order": 1 }
```

**`action: "update"`**

```json
// Общий формат для всех моделей
{ "updated_fields": ["title_rus", "content_rus"] }

// User — верификация
{ "verification_action": "approve", "verification_status": "Approved" }

// User — смена статуса
{ "new_status": "Teacher" }

// User — назначение в группу
{ "assigned_group": "groups/AbCdEf", "group_name": "CS-101" }

// User — удаление из группы
{ "removed_from_group": true }
```

**`action: "delete"`**

```json
// Group — включает имя удалённой группы
{ "name": "CS-101" }

// Все остальные модели — пустой объект
{}
```

---

## GET `/admin/logs/`

Список логов, отсортированных от новых к старым. Поддерживает фильтрацию и пагинацию.

> **Важно:** фильтры `action`, `model_name` и `admin_user` применяются по одному — если передано несколько, приоритет отдаётся первому в порядке: `action` → `model_name` → `admin_user`.

**Query параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|:---:|----------|
| `limit` | integer | `50` | Записей на странице (минимум 1, максимум 200) |
| `offset` | integer | `0` | Смещение от начала отсортированного списка |
| `action` | string | — | Фильтр по типу: `create`, `update`, `delete` |
| `model_name` | string | — | Фильтр по модели: `User`, `Group`, `Announcement`, `Book`, `Schedule`, `Notification`, `PrivacySection` |
| `admin_user` | string | — | Фильтр по username администратора |

**Ответ:**

```json
// 200 — успех
{
    "total": "50+",
    "offset": 0,
    "limit": 50,
    "has_more": true,
    "logs": [
        {
            "id": "audit_logs/AbCdEf123",
            "admin_user": "admin1",
            "action": "delete",
            "model_name": "User",
            "object_id": "users/XyZ789",
            "changes": {},
            "timestamp": "2026-06-30 10:15:43+00:00"
        }
    ]
}
```

> `total` — если есть ещё записи (`has_more: true`), значение имеет вид `"50+"`. Если это последняя страница — точное число.  
> `has_more: true` — нужно запросить следующую страницу через `offset`.

---

## Пагинация

Логи сортируются от новых к старым. Для получения следующей страницы увеличивайте `offset` на значение `limit`.

```
Страница 1: ?limit=50&offset=0
Страница 2: ?limit=50&offset=50
Страница 3: ?limit=50&offset=100
```

Когда `has_more: false` — страницы закончились.

---

## Лимит хранения

- В Firestore хранится не более **200** последних логов.
- После каждой записи нового лога система автоматически удаляет самые старые записи, если их количество превышает 200.
- Эта операция прозрачна и не влияет на ответ API.

---

## Коды ответов

| Код | Значение |
|-----|----------|
| 200 | Успех |
| 401 | Не авторизован |
| 403 | Доступ запрещён (не Admin) |

---

## Примеры запросов (Postman)

### Последние 50 логов
```
GET http://127.0.0.1:8000/api/audit/admin/logs/
Authorization: Bearer <admin_token>
```

### Только удаления
```
GET http://127.0.0.1:8000/api/audit/admin/logs/?action=delete
Authorization: Bearer <admin_token>
```

### Только изменения пользователей
```
GET http://127.0.0.1:8000/api/audit/admin/logs/?model_name=User
Authorization: Bearer <admin_token>
```

### Действия конкретного администратора
```
GET http://127.0.0.1:8000/api/audit/admin/logs/?admin_user=admin1
Authorization: Bearer <admin_token>
```

### Вторая страница (записи 51–100)
```
GET http://127.0.0.1:8000/api/audit/admin/logs/?limit=50&offset=50
Authorization: Bearer <admin_token>
```

### Создания книг (последние 20)
```
GET http://127.0.0.1:8000/api/audit/admin/logs/?action=create&model_name=Book&limit=20
Authorization: Bearer <admin_token>
```

> Примечание: при указании нескольких фильтров одновременно — применяется только `action` (он имеет наивысший приоритет).
