from fireo.models import Model
from fireo.fields import TextField, DateTime, NumberField


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
