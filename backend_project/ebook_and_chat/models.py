from fireo.models import Model
from fireo.fields import TextField, DateTime


GENRES_CHOICES = [
    ('Книги Sejong', 'Книги Sejong'),
    ('Книги Topik', 'Книги Topik'),
    ('Художественная литература', 'Художественная литература'),
]

VALID_GENRES = {g[0] for g in GENRES_CHOICES}


class Book(Model):
    # Названия на 4 языках
    title_taj = TextField()
    title_rus = TextField()
    title_eng = TextField()
    title_kor = TextField()

    # Описания на 4 языках
    description_taj = TextField()
    description_rus = TextField()
    description_eng = TextField()
    description_kor = TextField()

    author         = TextField()
    genres         = TextField()
    published_date = TextField()
    created_at     = DateTime(auto=True)

    # Обложка (необязательна)
    cover    = TextField()  # public URL
    cover_id = TextField()  # Google Drive file ID

    # Файл книги
    file    = TextField()   # public URL
    file_id = TextField()   # Google Drive file ID

    class Meta:
        collection_name = 'books'
