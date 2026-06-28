from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from utils.decorators import admin_required, jwt_required
from utils.drive import upload_book_cover, upload_book_file, delete_file
from .models import Book, VALID_GENRES
from .serializers import BookSerializer


ALLOWED_COVER_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_FILE_TYPES  = {'application/pdf', 'application/epub+zip'}
MAX_COVER_SIZE = 2 * 1024 * 1024
MAX_FILE_SIZE  = 100 * 1024 * 1024
BOOKS_CACHE_TTL = 300  # 5 минут

_ALL_CACHE_KEYS = ['books_list_'] + [f'books_list_{g}' for g in VALID_GENRES]


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


def _get_book(book_id: str):
    try:
        return Book.collection.get(f'books/{book_id}')
    except Exception:
        return None


def _invalidate_books_cache():
    cache.delete_many(_ALL_CACHE_KEYS)


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
    book.genres   = genres
    book.cover    = cover_url
    book.cover_id = cover_id
    book.file     = file_url
    book.file_id  = file_id

    try:
        book.save()
    except Exception as e:
        delete_file(file_id)
        if cover_id:
            delete_file(cover_id)
        return Response({'error': f'Ошибка сохранения: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    _invalidate_books_cache()
    return Response({'message': 'Книга успешно добавлена', 'book': BookSerializer(book).data}, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@admin_required
def admin_edit_book(request, book_id):
    book = _get_book(book_id)
    if not book:
        return Response({'error': 'Книга не найдена'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    updated_fields = []
    new_file_ids = []   # загружены в этом запросе; удалить при ошибке сохранения
    old_file_ids = []   # удалить после успешного сохранения

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
        result, err = _upload(cover_file, upload_book_cover, f'cover_{book_id}', 'обложки')
        if err:
            for fid in new_file_ids:
                delete_file(fid)
            return err
        new_cover_id, cover_url = result
        new_file_ids.append(new_cover_id)
        old_file_ids.append(book.cover_id)
        book.cover    = cover_url
        book.cover_id = new_cover_id
        updated_fields.extend(['cover', 'cover_id'])

    book_file = request.FILES.get('file')
    if book_file:
        if err := _validate_file(book_file, ALLOWED_FILE_TYPES, MAX_FILE_SIZE,
                                 'Допустимые форматы книги: PDF, EPUB',
                                 'Файл книги слишком большой. Максимум 100 МБ'):
            for fid in new_file_ids:
                delete_file(fid)
            return err
        result, err = _upload(book_file, upload_book_file, f'book_{book_id}', 'файла книги')
        if err:
            for fid in new_file_ids:
                delete_file(fid)
            return err
        new_file_id, file_url = result
        new_file_ids.append(new_file_id)
        old_file_ids.append(book.file_id)
        book.file    = file_url
        book.file_id = new_file_id
        updated_fields.extend(['file', 'file_id'])

    if not updated_fields:
        return Response({'message': 'Нет данных для обновления'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        book.update()
    except Exception as e:
        # Сохранение не удалось — откатываем новые файлы с Drive
        for fid in new_file_ids:
            delete_file(fid)
        return Response({'error': f'Ошибка сохранения: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # БД обновлена успешно — теперь удаляем старые файлы
    for fid in old_file_ids:
        if fid:
            delete_file(fid)

    _invalidate_books_cache()
    return Response({'message': 'Книга обновлена', 'updated_fields': updated_fields, 'book': BookSerializer(book).data})


@api_view(['DELETE'])
@admin_required
def admin_delete_book(request, book_id):
    book = _get_book(book_id)
    if not book:
        return Response({'error': 'Книга не найдена'}, status=status.HTTP_404_NOT_FOUND)

    if book.cover_id:
        delete_file(book.cover_id)
    if book.file_id:
        delete_file(book.file_id)

    Book.collection.delete(f'books/{book_id}')
    _invalidate_books_cache()
    return Response({'message': 'Книга удалена'})


# ---------------------------------------------------------------------------
# Public (authenticated) endpoints
# ---------------------------------------------------------------------------

@api_view(['GET'])
@jwt_required
def list_books(request):
    """Список книг с пагинацией.
    Query params:
      ?genres=  — фильтр по жанру
      ?limit=   — кол-во книг (по умолчанию 100, макс 500)
      ?offset=  — смещение (по умолчанию 0)
    """
    genre_filter = request.query_params.get('genres', '').strip()

    try:
        limit  = min(int(request.query_params.get('limit', 100)), 500)
        offset = max(int(request.query_params.get('offset', 0)), 0)
    except ValueError:
        return Response(
            {'error': 'Параметры limit и offset должны быть целыми числами'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cache_key = f'books_list_{genre_filter}'
    books_data = cache.get(cache_key)

    if books_data is None:
        if genre_filter:
            qs = list(Book.collection.filter('genres', '==', genre_filter).fetch(1000))
        else:
            qs = list(Book.collection.fetch(1000))
        books_data = BookSerializer(qs, many=True).data
        cache.set(cache_key, books_data, BOOKS_CACHE_TTL)

    total = len(books_data)
    page  = books_data[offset: offset + limit]

    return Response({
        'total':  total,
        'limit':  limit,
        'offset': offset,
        'books':  page,
    })


@api_view(['GET'])
@jwt_required
def get_book(request, book_id):
    book = _get_book(book_id)
    if not book:
        return Response({'error': 'Книга не найдена'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'book': BookSerializer(book).data})
