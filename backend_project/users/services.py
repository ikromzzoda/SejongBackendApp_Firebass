import re
import uuid
import random
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail

from .validators import _username_taken


# Подтверждение email при регистрации — та же политика, что и у сброса пароля
EMAIL_CODE_LIFETIME_MINUTES = 15
EMAIL_CODE_MAX_ATTEMPTS     = 5
EMAIL_CODE_RESEND_SECONDS   = 600  # повторная отправка кода — не чаще раза в 10 минут

# Единый ответ resend-code: не раскрываем, зарегистрирован ли email
RESEND_CODE_MESSAGE = 'Если такой email зарегистрирован и не подтверждён, код отправлен на почту.'

RESET_CODE_LIFETIME_MINUTES = 15
RESET_CODE_MAX_ATTEMPTS     = 5
RESET_CODE_RESEND_SECONDS   = 600  # повторная отправка кода — не чаще раза в 10 минут

# Единый ответ forgot-password: не раскрываем, зарегистрирован ли email
FORGOT_PASSWORD_MESSAGE = 'Если такой email зарегистрирован, код отправлен на почту.'


def _clear_email_code(user):
    user.email_code_hash     = ''
    user.email_code_expires  = None
    user.email_code_attempts = 0


def _send_email_verification_code(user, now):
    """Генерирует 6-значный код, сохраняет его хэш на пользователе и шлёт код на почту.
    Поля пользователя только выставляются — save/update вызывает вызывающий код.
    """
    code = f'{secrets.randbelow(1_000_000):06d}'
    user.email_code_hash     = make_password(code)
    user.email_code_expires  = now + timedelta(minutes=EMAIL_CODE_LIFETIME_MINUTES)
    user.email_code_attempts = 0
    user.email_code_sent_at  = now

    try:
        send_mail(
            subject='Sejong: код подтверждения email',
            message=(
                f'Ваш код подтверждения email: {code}\n\n'
                f'Код действует {EMAIL_CODE_LIFETIME_MINUTES} минут.\n'
                'Если вы не запрашивали этот код, просто проигнорируйте это письмо.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        # Не раскрываем наружу проблемы SMTP; код остаётся валидным до истечения
        pass


def _clear_reset_code(user):
    user.reset_code_hash     = ''
    user.reset_code_expires  = None
    user.reset_code_attempts = 0


_TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}


def _transliterate(text: str) -> str:
    return ''.join(_TRANSLIT.get(c, c) for c in text.lower())


def _generate_username(fullname: str, batch_taken: set) -> str:
    parts = fullname.strip().split()
    if parts:
        base = _transliterate(parts[0])
        base = re.sub(r'[^a-z0-9]', '', base)[:12] or 'student'
    else:
        base = 'student'
    for _ in range(20):
        candidate = f"{base}_{random.randint(1000, 9999)}"
        if candidate not in batch_taken and not _username_taken(candidate):
            return candidate
    return f"student_{uuid.uuid4().hex[:8]}"


def _generate_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    pwd += [secrets.choice(chars) for _ in range(length - 3)]
    secrets.SystemRandom().shuffle(pwd)
    return ''.join(pwd)
