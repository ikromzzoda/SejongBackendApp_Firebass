"""
Общие компоненты для drf-spectacular (OpenAPI-документация).

Авторизация в проекте не реализована через DRF `authentication_classes` —
декораторы `jwt_required`/`admin_required` (см. utils/decorators.py) сами
разбирают заголовок `Authorization` и возвращают `JsonResponse` при ошибке.
drf-spectacular не может обнаружить это автоматически, поэтому заголовок и
типовые ответы 401/403 описываются вручную и переиспользуются во всех views.
"""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse
from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


AUTH_HEADER_PARAM = OpenApiParameter(
    name="Authorization",
    type=str,
    location=OpenApiParameter.HEADER,
    required=True,
    description='JWT-токен в формате `Bearer <token>`.',
)

_UNAUTHORIZED_RESPONSE = OpenApiResponse(
    response=ErrorResponseSerializer,
    description=(
        "Токен не передан, истёк, недействителен или отозван "
        '(`{"error": "Токен не предоставлен"}` / `"Токен истёк"` / '
        '`"Недействительный токен"` / `"Токен отозван"`).'
    ),
)

_FORBIDDEN_RESPONSE = OpenApiResponse(
    response=ErrorResponseSerializer,
    description='Требуются права администратора (`{"error": "Доступ запрещён. Требуются права администратора."}`).',
)

# Разворачиваются через `**UNAUTHORIZED_RESPONSES` / `**ADMIN_RESPONSES`
# в `responses={...}` каждого view, защищённого соответствующим декоратором.
UNAUTHORIZED_RESPONSES = {401: _UNAUTHORIZED_RESPONSE}
ADMIN_RESPONSES = {401: _UNAUTHORIZED_RESPONSE, 403: _FORBIDDEN_RESPONSE}
