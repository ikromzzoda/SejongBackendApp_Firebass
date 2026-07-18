from fireo.models import Model
from fireo.fields import TextField, DateTime, ListField, BooleanField


class Announcement(Model):
    title_taj = TextField()
    title_rus = TextField()
    title_eng = TextField()
    title_kor = TextField()

    content_taj = TextField()
    content_rus = TextField()
    content_eng = TextField()
    content_kor = TextField()

    # List of {"file_id": str, "url": str}
    images = ListField()

    time_posted = DateTime(auto=True)
    author = TextField()  # username из JWT

    class Meta:
        collection_name = 'announcements'


class ContactMessage(Model):
    """Обращение к админу. Отправляется без авторизации — в т.ч. пользователями,
    которые не могут зарегистрироваться или войти."""
    name         = TextField()
    email        = TextField()
    phone_number = TextField()
    message      = TextField()
    is_read      = BooleanField()
    created_at   = DateTime(auto=True)

    class Meta:
        collection_name = 'contact_messages'
