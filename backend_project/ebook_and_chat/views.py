from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from utils.decorators import admin_required, jwt_required
from utils.drive import upload_book_cover, upload_book_file, delete_file
from .models import Book, VALID_GENRES


ALLOWED_COVER_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_FILE_TYPES  = {'application/pdf', 'application/epub+zip'}
MAX_COVER_SIZE = 2 * 1024 * 1024   # 2 MB
MAX_FILE_SIZE  = 100 * 1024 * 1024  # 100 MB


def _book_dict(book) -> dict:
    return {
        'id':              book.id,
        'title_taj':       book.title_taj or '',
        'title_rus':       book.title_rus or '',
        'title_eng':       book.title_eng or '',
        'title_kor':       book.title_kor or '',
        'description_taj': book.description_taj or '',
        'description_rus': book.description_rus or '',
        'description_eng': book.description_eng or '',
        'description_kor': book.description_kor or '',
        'author':          book.author or '',
        'genres':          book.genres or '',
        'published_date':  book.published_date or '',
        'created_at':      str(book.created_at) if book.created_at else '',
        'cover':           book.cover or '',
        'cover_id':        book.cover_id or '',
        'file':            book.file or '',
        'file_id':         book.file_id or '',
    }


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@admin_required
def admin_create_book(request):
    """Создать книгу (только для Admin).
    Тело: multipart/form-data
      Обязательные текстовые поля:
        title_rus, file
      Необязательные:
        title_taj, title_eng, title_kor,
        description_taj, description_rus, description_eng, description_kor,
        author, genres, published_date
        cover (файл-изображение)
    """
    data = request.data

    if not data.get('title_rus', '').strip():
        return Response({'error': 'Поле "title_rus" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    book_file = request.FILES.get('file')
    if not book_file:
        return Response({'error': 'Файл книги ("file") обязателен'}, status=status.HTTP_400_BAD_REQUEST)

    if book_file.content_type not in ALLOWED_FILE_TYPES:
        return Response(
            {'error': 'Допустимые форматы книги: PDF, EPUB'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if book_file.size > MAX_FILE_SIZE:
        return Response(
            {'error': 'Файл книги слишком большой. Максимум 100 МБ'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    genres = data.get('genres', '').strip()
    if genres and genres not in VALID_GENRES:
        return Response(
            {'error': f'Допустимые жанры: {", ".join(VALID_GENRES)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --- Загрузка файла книги ---
    ext = book_file.name.rsplit('.', 1)[-1] if '.' in book_file.name else 'pdf'
    book_filename = f"book_{data.get('title_rus', 'untitled')[:40].replace(' ', '_')}.{ext}"
    try:
        file_id, file_url = upload_book_file(book_file, book_filename, book_file.content_type)
    except Exception as e:
        return Response(
            {'error': f'Ошибка загрузки файла книги на Google Drive: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # --- Загрузка обложки (необязательно) ---
    cover_id = ''
    cover_url = ''
    cover_file = request.FILES.get('cover')
    if cover_file:
        if cover_file.content_type not in ALLOWED_COVER_TYPES:
            delete_file(file_id)
            return Response(
                {'error': 'Допустимые форматы обложки: JPEG, PNG, WEBP'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if cover_file.size > MAX_COVER_SIZE:
            delete_file(file_id)
            return Response(
                {'error': 'Обложка слишком большая. Максимум 2 МБ'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cover_ext = cover_file.name.rsplit('.', 1)[-1] if '.' in cover_file.name else 'jpg'
        cover_filename = f"cover_{data.get('title_rus', 'untitled')[:40].replace(' ', '_')}.{cover_ext}"
        try:
            cover_id, cover_url = upload_book_cover(cover_file, cover_filename, cover_file.content_type)
        except Exception as e:
            delete_file(file_id)
            return Response(
                {'error': f'Ошибка загрузки обложки на Google Drive: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    book = Book()
    book.title_taj       = data.get('title_taj', '').strip()
    book.title_rus       = data.get('title_rus', '').strip()
    book.title_eng       = data.get('title_eng', '').strip()
    book.title_kor       = data.get('title_kor', '').strip()
    book.description_taj = data.get('description_taj', '').strip()
    book.description_rus = data.get('description_rus', '').strip()
    book.description_eng = data.get('description_eng', '').strip()
    book.description_kor = data.get('description_kor', '').strip()
    book.author          = data.get('author', '').strip()
    book.genres          = genres
    book.published_date  = data.get('published_date', '').strip()
    book.cover           = cover_url
    book.cover_id        = cover_id
    book.file            = file_url
    book.file_id         = file_id
    book.save()

    return Response(
        {'message': 'Книга успешно добавлена', 'book': _book_dict(book)},
        status=status.HTTP_201_CREATED,
    )


@api_view(['PATCH'])
@admin_required
def admin_edit_book(request, book_id):
    """Редактировать книгу (только для Admin).
    Все поля необязательные. Файлы (cover, file) заменяют старые и удаляют их с Drive.
    """
    try:
        book = Book.collection.get(f'books/{book_id}')
    except Exception:
        book = None
    if not book:
        return Response({'error': 'Книга не найдена'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    updated_fields = []

    for field in ('title_taj', 'title_rus', 'title_eng', 'title_kor',
                  'description_taj', 'description_rus', 'description_eng', 'description_kor',
                  'author', 'published_date'):
        if field in data:
            setattr(book, field, data[field].strip())
            updated_fields.append(field)

    if 'genres' in data:
        genres = data['genres'].strip()
        if genres and genres not in VALID_GENRES:
            return Response(
                {'error': f'Допустимые жанры: {", ".join(VALID_GENRES)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        book.genres = genres
        updated_fields.append('genres')

    # --- Замена обложки ---
    cover_file = request.FILES.get('cover')
    if cover_file:
        if cover_file.content_type not in ALLOWED_COVER_TYPES:
            return Response(
                {'error': 'Допустимые форматы обложки: JPEG, PNG, WEBP'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if cover_file.size > MAX_COVER_SIZE:
            return Response(
                {'error': 'Обложка слишком большая. Максимум 5 МБ'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cover_ext = cover_file.name.rsplit('.', 1)[-1] if '.' in cover_file.name else 'jpg'
        cover_filename = f"cover_{book_id}.{cover_ext}"
        try:
            new_cover_id, new_cover_url = upload_book_cover(cover_file, cover_filename, cover_file.content_type)
        except Exception as e:
            return Response(
                {'error': f'Ошибка загрузки обложки: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if book.cover_id:
            delete_file(book.cover_id)
        book.cover    = new_cover_url
        book.cover_id = new_cover_id
        updated_fields.extend(['cover', 'cover_id'])

    # --- Замена файла книги ---
    book_file = request.FILES.get('file')
    if book_file:
        if book_file.content_type not in ALLOWED_FILE_TYPES:
            return Response(
                {'error': 'Допустимые форматы книги: PDF, EPUB'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if book_file.size > MAX_FILE_SIZE:
            return Response(
                {'error': 'Файл книги слишком большой. Максимум 100 МБ'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ext = book_file.name.rsplit('.', 1)[-1] if '.' in book_file.name else 'pdf'
        book_filename = f"book_{book_id}.{ext}"
        try:
            new_file_id, new_file_url = upload_book_file(book_file, book_filename, book_file.content_type)
        except Exception as e:
            return Response(
                {'error': f'Ошибка загрузки файла книги: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if book.file_id:
            delete_file(book.file_id)
        book.file    = new_file_url
        book.file_id = new_file_id
        updated_fields.extend(['file', 'file_id'])

    if not updated_fields:
        return Response({'message': 'Нет данных для обновления'}, status=status.HTTP_400_BAD_REQUEST)

    book.update()
    return Response({
        'message': 'Книга обновлена',
        'updated_fields': updated_fields,
        'book': _book_dict(book),
    })


@api_view(['DELETE'])
@admin_required
def admin_delete_book(request, book_id):
    """Удалить книгу (только для Admin). Файлы удаляются с Google Drive."""
    try:
        book = Book.collection.get(f'books/{book_id}')
    except Exception:
        book = None
    if not book:
        return Response({'error': 'Книга не найдена'}, status=status.HTTP_404_NOT_FOUND)

    if book.cover_id:
        delete_file(book.cover_id)
    if book.file_id:
        delete_file(book.file_id)

    Book.collection.delete(f'books/{book_id}')
    return Response({'message': 'Книга удалена'})


# ---------------------------------------------------------------------------
# Public (authenticated) endpoints
# ---------------------------------------------------------------------------

@api_view(['GET'])
@jwt_required
def list_books(request):
    """Список всех книг.
    Query params (необязательные):
      ?genres=Книги Sejong|Книги Topik|Художественная литература
    """
    genre_filter = request.query_params.get('genres', '').strip()

    if genre_filter:
        books = list(Book.collection.filter('genres', '==', genre_filter).fetch(200))
    else:
        books = list(Book.collection.fetch(200))

    return Response({
        'total': len(books),
        'books': [_book_dict(b) for b in books],
    })


@api_view(['GET'])
@jwt_required
def get_book(request, book_id):
    """Получить одну книгу по ID."""
    try:
        book = Book.collection.get(f'books/{book_id}')
    except Exception:
        book = None
    if not book:
        return Response({'error': 'Книга не найдена'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'book': _book_dict(book)})
