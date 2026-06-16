from fireo.models import Model
from fireo.fields import TextField, DateTime, ListField


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
