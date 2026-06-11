import re
import jwt as pyjwt
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import User, BlacklistedToken
from utils.jwt_utils import generate_token, decode_token


PHONE_RE = re.compile(r'^\+992\d{9}$')


@api_view(['POST'])
def register(request):
    data = request.data

    for field in ('username', 'password', 'email', 'phone_number'):
        if not data.get(field):
            return Response(
                {'error': f'Поле "{field}" обязательно'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if not PHONE_RE.match(data['phone_number']):
        return Response(
            {'error': "Номер должен начинаться с '+992' и содержать 9 цифр после него."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing = list(User.collection.filter('username', '==', data['username']).fetch(1))
    if existing:
        return Response(
            {'error': 'Пользователь с таким username уже существует'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User()
    user.username     = data['username']
    user.fullname     = data.get('fullname', '')
    user.email        = data['email']
    user.phone_number = data['phone_number']
    user.password     = make_password(data['password'])
    user.date_of_birth = data.get('date_of_birth', '')
    user.status               = 'Guest'
    user.verification_status  = 'Pending'
    user.save()

    token = generate_token(
        user_id=user.id,
        username=user.username,
        status=user.status,
        verification_status=user.verification_status,
    )

    return Response({
        'message': 'Регистрация успешна. Ожидайте подтверждения администратора.',
        'token': token,
        'status': user.status,
        'verification_status': user.verification_status,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def login(request):
    data     = request.data
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return Response(
            {'error': 'Введите username и пароль'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    users = list(User.collection.filter('username', '==', username).fetch(1))
    if not users or not check_password(password, users[0].password):
        return Response(
            {'error': 'Неверный username или пароль'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user = users[0]
    resolved_status = 'Student' if user.verification_status == 'Approved' else 'Guest'

    token = generate_token(
        user_id=user.id,
        username=user.username,
        status=resolved_status,
        verification_status=user.verification_status,
    )

    return Response({
        'message': 'Вход выполнен',
        'token': token,
        'status': resolved_status,
        'verification_status': user.verification_status,
    })


@api_view(['POST'])
def logout(request):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response({'error': 'Токен не предоставлен'}, status=status.HTTP_401_UNAUTHORIZED)

    token = auth_header.split(' ', 1)[1]
    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        return Response({'error': 'Токен уже истёк'}, status=status.HTTP_401_UNAUTHORIZED)
    except pyjwt.InvalidTokenError:
        return Response({'error': 'Недействительный токен'}, status=status.HTTP_401_UNAUTHORIZED)

    # Добавляем JTI в чёрный список (document ID = JTI → поиск O(1))
    bt = BlacklistedToken()
    bt.id = payload['jti']
    bt.save()

    return Response({'message': 'Выход выполнен'})
