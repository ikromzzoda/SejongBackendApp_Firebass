import re

from rest_framework.response import Response
from rest_framework import status

from .models import User


PHONE_RE = re.compile(r'^\+992\d{9}$')

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_AVATAR_SIZE = 3 * 1024 * 1024  # 3 MB

VALID_STATUSES = {'Student', 'Teacher', 'Admin', 'Guest'}


def _require_fields(data, *fields):
    for field in fields:
        if not data.get(field):
            return Response(
                {'error': f'Поле "{field}" обязательно'},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return None


def _validate_phone(phone: str):
    if not PHONE_RE.match(phone):
        return Response(
            {'error': "Номер должен начинаться с '+992' и содержать 9 цифр после него."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def _username_taken(username: str) -> bool:
    return bool(list(User.collection.filter('username', '==', username).fetch(1)))
