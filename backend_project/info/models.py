from fireo.models import Model
from fireo.fields import TextField, DateTime, NumberField, ListField


class Schedule(Model):
    day        = NumberField(int_only=True)   # 0=Monday ... 6=Sunday
    start_time = TextField()                  # "HH:MM"
    end_time   = TextField()                  # "HH:MM"
    classroom  = NumberField(int_only=True)   # 301, 303, 306, 307, 308
    group_id   = TextField()                  # Firestore Group document ID
    teacher_id = TextField()                  # Firestore User document ID (Teacher)
    book       = NumberField(int_only=True)   # 1-8
    created_at = DateTime(auto=True)

    class Meta:
        collection_name = 'schedules'


class Notification(Model):
    title_taj       = TextField()
    title_rus       = TextField()
    title_eng       = TextField()
    title_kor       = TextField()
    content_taj     = TextField()
    content_rus     = TextField()
    content_eng     = TextField()
    content_kor     = TextField()
    image_url       = TextField()   # single cover/thumbnail URL (optional)
    images          = ListField()   # [{"file_id": str, "url": str}, ...]
    target_statuses = ListField()   # e.g. ["Student", "Teacher"]
    created_at      = DateTime(auto=True)

    class Meta:
        collection_name = 'notifications'


class PrivacySection(Model):
    title_taj   = TextField()
    title_rus   = TextField()
    title_eng   = TextField()
    title_kor   = TextField()
    content_taj = TextField()
    content_rus = TextField()
    content_eng = TextField()
    content_kor = TextField()
    order       = NumberField(int_only=True)   # порядок отображения
    updated_at  = DateTime(auto=True)

    class Meta:
        collection_name = 'privacy_sections'
