import jwt
from functools import wraps
from django.http import JsonResponse
from .jwt_utils import decode_token


def _extract_payload(request):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None, JsonResponse({'error': 'Токен не предоставлен'}, status=401)
    token = auth_header.split(' ', 1)[1]
    try:
        return decode_token(token), None
    except jwt.ExpiredSignatureError:
        return None, JsonResponse({'error': 'Токен истёк'}, status=401)
    except jwt.InvalidTokenError:
        return None, JsonResponse({'error': 'Недействительный токен'}, status=401)


def jwt_required(view_func):
    """
    Полная проверка: подпись + blacklist через поиск по document ID (O(1) в Firestore).
    Используй для защищённых endpoint-ов, где важна мгновенная отмена токена при logout.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        payload, error = _extract_payload(request)
        if error:
            return error

        from users.models import BlacklistedToken
        jti = payload.get('jti', '')
        try:
            bt = BlacklistedToken.collection.get(f'blacklisted_tokens/{jti}')
            if bt:
                return JsonResponse({'error': 'Токен отозван'}, status=401)
        except Exception:
            pass

        request.user_payload = payload
        return view_func(request, *args, **kwargs)
    return wrapper


def jwt_verify_only(view_func):
    """
    Быстрая проверка: только подпись, без обращения к Firestore.
    Подходит для read-only endpoint-ов с высокой нагрузкой,
    где мгновенная отмена токена не критична.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        payload, error = _extract_payload(request)
        if error:
            return error
        request.user_payload = payload
        return view_func(request, *args, **kwargs)
    return wrapper
