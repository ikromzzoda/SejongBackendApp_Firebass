from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from utils.decorators import admin_required, jwt_required
from utils.drive import upload_book_cover, upload_book_file, delete_file
from .models import Book, VALID_GENRES


ALLOWED_COVER_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_FILE_TYPES  = {'application/pdf', 'application/epub+zip'}
MAX_COVER_SIZE = 2 * 1024 * 1024
MAX_FILE_SIZE  = 100 * 1024 * 1024


def _validate_file(f, allowed_types, max_size, type_error, size_error):
    if f.content_type not in allowed_types:
        return Response({'error': type_error}, status=status.HTTP_400_BAD_REQUEST)
    if f.size > max_size:
        return Response({'error': size_error}, status=status.HTTP_400_BAD_REQUEST)
    return None


def _upload(file_obj, upload_fn, filename, error_label):
    ext = file_obj.name.rsplit('.', 1)[-1] if '.' in file_obj.name else filename.rsplit('.', 1)[-1]
    try:
        return upload_fn(file_obj, f"{filename}.{ext}", file_obj.content_type), None
    except Exception as e:
        return None, Response(
            {'error': f'Ошибка загрузки {error_label} на Google Drive: {e}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )


def _replace_drive_file(file_obj, old_id, upload_fn, filename, error_label):
    result, err = _upload(file_obj, upload_fn, filename, error_label)
    if err:
        return None, None, err
    file_id, url = result
    if old_id:
        delete_file(old_id)
    return file_id, url, None


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
    data = request.data

    if not data.get('title_rus', '').strip():
        return Response({'error': 'Поле "title_rus" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    book_file = request.FILES.get('file')
    if not book_file:
        return Response({'error': 'Файл книги ("file") обязателен'}, status=status.HTTP_400_BAD_REQUEST)

    if err := _validate_file(book_file, ALLOWED_FILE_TYPES, MAX_FILE_SIZE,
                             'Допустимые форматы книги: PDF, EPUB',
                             'Файл книги слишком большой. Максимум 100 МБ'):
        return err

    genres = data.get('genres', '').strip()
    if genres and genres not in VALID_GENRES:
        return Response({'error': f'Допустимые жанры: {", ".join(VALID_GENRES)}'}, status=status.HTTP_400_BAD_REQUEST)

    slug = data.get('title_rus', 'untitled')[:40].replace(' ', '_')
    (file_id, file_url), err = _upload(book_file, upload_book_file, f'book_{slug}', 'файла книги')
    if err:
        return err

    cover_id = cover_url = ''
    cover_file = request.FILES.get('cover')
    if cover_file:
        if err := _validate_file(cover_file, ALLOWED_COVER_TYPES, MAX_COVER_SIZE,
                                 'Допустимые форматы обложки: JPEG, PNG, WEBP',
                                 'Обложка слишком большая. Максимум 2 МБ'):
            delete_file(file_id)
            return err
        (cover_id, cover_url), err = _upload(cover_file, upload_book_cover, f'cover_{slug}', 'обложки')
        if err:
            delete_file(file_id)
            return err

    book = Book()
    for field in ('title_taj', 'title_rus', 'title_eng', 'title_kor',
                  'description_taj', 'description_rus', 'description_eng', 'description_kor',
                  'author', 'published_date'):
        setattr(book, field, data.get(field, '').strip())
    book.genres     = genres
    book.cover      = cover_url
    book.cover_id   = cover_id
    book.file       = file_url
    book.file_id    = file_id
    book.save()

    return Response({'message': 'Книга успешно добавлена', 'book': _book_dict(book)}, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@admin_required
def admin_edit_book(request, book_id):
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
            return Response({'error': f'Допустимые жанры: {", ".join(VALID_GENRES)}'}, status=status.HTTP_400_BAD_REQUEST)
        book.genres = genres
        updated_fields.append('genres')

    cover_file = request.FILES.get('cover')
    if cover_file:
        if err := _validate_file(cover_file, ALLOWED_COVER_TYPES, MAX_COVER_SIZE,
                                 'Допустимые форматы обложки: JPEG, PNG, WEBP',
                                 'Обложка слишком большая. Максимум 2 МБ'):
            return err
        cover_id, cover_url, err = _replace_drive_file(
            cover_file, book.cover_id, upload_book_cover, f'cover_{book_id}', 'обложки')
        if err:
            return err
        book.cover    = cover_url
        book.cover_id = cover_id
        updated_fields.extend(['cover', 'cover_id'])

    book_file = request.FILES.get('file')
    if book_file:
        if err := _validate_file(book_file, ALLOWED_FILE_TYPES, MAX_FILE_SIZE,
                                 'Допустимые форматы книги: PDF, EPUB',
                                 'Файл книги слишком большой. Максимум 100 МБ'):
            return err
        file_id, file_url, err = _replace_drive_file(
            book_file, book.file_id, upload_book_file, f'book_{book_id}', 'файла книги')
        if err:
            return err
        book.file    = file_url
        book.file_id = file_id
        updated_fields.extend(['file', 'file_id'])

    if not updated_fields:
        return Response({'message': 'Нет данных для обновления'}, status=status.HTTP_400_BAD_REQUEST)

    book.update()
    return Response({'message': 'Книга обновлена', 'updated_fields': updated_fields, 'book': _book_dict(book)})


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
