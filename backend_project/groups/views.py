from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import Group
from users.models import User
from utils.decorators import admin_required
from utils.schema import AUTH_HEADER_PARAM, ADMIN_RESPONSES, ErrorResponseSerializer, MessageResponseSerializer
from audit_logs.utils import log_action
from .serializers import (
    GroupSerializer,
    AdminListGroupsResponseSerializer,
    AdminCreateGroupRequestSerializer,
    AdminCreateGroupResponseSerializer,
    AdminRenameGroupRequestSerializer,
    AdminListGroupMembersResponseSerializer,
    AdminAssignGroupRequestSerializer,
    AdminGroupMemberActionResponseSerializer,
)


def _user_dict(user, group_name: str = ''):
    return {
        'id': user.id,
        'username': user.username,
        'fullname': user.fullname,
        'email': user.email,
        'phone_number': user.phone_number,
        'status': user.status,
        'verification_status': user.verification_status,
        'group': group_name,
    }


def _get_group_or_404(group_id):
    try:
        group = Group.collection.get(f'groups/{group_id}')
    except Exception:
        group = None
    if not group:
        return None, Response({'error': 'Группа не найдена'}, status=status.HTTP_404_NOT_FOUND)
    return group, None


def _get_user_or_404(user_id):
    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return None, Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
    return user, None


@extend_schema(
    tags=['Groups'],
    summary='Список групп (admin)',
    description='Для каждой группы возвращает ID преподавателя (пользователь со статусом Teacher в этой группе) и количество студентов.',
    parameters=[
        AUTH_HEADER_PARAM,
        OpenApiParameter('limit', OpenApiTypes.INT, description='Максимум записей (по умолчанию 20, максимум 100)'),
    ],
    responses={200: AdminListGroupsResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['GET'])
@admin_required
def admin_list_groups(request):
    try:
        limit = min(int(request.query_params.get('limit', 20)), 100)
    except (ValueError, TypeError):
        limit = 20

    raw = list(Group.collection.fetch(limit + 1))
    has_more = len(raw) > limit

    # Один проход по пользователям вместо двух запросов на каждую группу
    teacher_by_group: dict[str, str] = {}
    students_by_group: dict[str, int] = {}
    for u in User.collection.fetch(1000):
        if not u.group:
            continue
        if u.status == 'Teacher' and u.group not in teacher_by_group:
            teacher_by_group[u.group] = u.id
        elif u.status == 'Student':
            students_by_group[u.group] = students_by_group.get(u.group, 0) + 1

    groups = [
        {
            'id':             g.id,
            'name':           g.name,
            'teacher_id':     teacher_by_group.get(g.id, ''),
            'students_count': students_by_group.get(g.id, 0),
            'created_at':     str(g.created_at) if g.created_at else '',
        }
        for g in raw[:limit]
    ]
    return Response({'total': len(groups), 'has_more': has_more, 'groups': groups})


@extend_schema(
    tags=['Groups'],
    summary='Создать группу (admin)',
    parameters=[AUTH_HEADER_PARAM],
    request=AdminCreateGroupRequestSerializer,
    responses={201: AdminCreateGroupResponseSerializer, 400: ErrorResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['POST'])
@admin_required
def admin_create_group(request):
    name = request.data.get('name', '').strip()
    if not name:
        return Response({'error': 'Поле "name" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    existing = list(Group.collection.filter('name', '==', name).fetch(1))
    if existing:
        return Response({'error': f'Группа с именем "{name}" уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    group = Group()
    group.name = name
    group.save()
    log_action(request, 'create', 'Group', group.id, {'name': name})
    return Response(
        {'message': f'Группа "{name}" создана.', 'group': {'id': group.id, 'name': group.name}},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=['Groups'],
    summary='Удалить группу (admin)',
    description='Удаляет группу и снимает её со всех участников (их поле group становится пустым).',
    parameters=[AUTH_HEADER_PARAM],
    responses={200: MessageResponseSerializer, 404: ErrorResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['DELETE'])
@admin_required
def admin_delete_group(request, group_id):
    group, err = _get_group_or_404(group_id)
    if err:
        return err

    members = list(User.collection.filter('group', '==', group_id).fetch(500))
    for member in members:
        member.group = ''
        member.update()

    Group.collection.delete(f'groups/{group_id}')
    log_action(request, 'delete', 'Group', group_id, {'name': group.name})
    return Response({'message': f'Группа "{group.name}" удалена.'})


@extend_schema(
    tags=['Groups'],
    summary='Переименовать группу (admin)',
    parameters=[AUTH_HEADER_PARAM],
    request=AdminRenameGroupRequestSerializer,
    responses={200: AdminCreateGroupResponseSerializer, 400: ErrorResponseSerializer, 404: ErrorResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['PATCH'])
@admin_required
def admin_rename_group(request, group_id):
    group, err = _get_group_or_404(group_id)
    if err:
        return err

    new_name = request.data.get('name', '').strip()
    if not new_name:
        return Response({'error': 'Поле "name" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    existing = list(Group.collection.filter('name', '==', new_name).fetch(1))
    if existing:
        return Response({'error': f'Группа с именем "{new_name}" уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    group.name = new_name
    group.update()
    log_action(request, 'update', 'Group', group_id, {'new_name': new_name})
    return Response({'message': 'Группа переименована.', 'group': {'id': group.id, 'name': group.name}})


@extend_schema(
    tags=['Groups'],
    summary='Участники группы (admin)',
    parameters=[AUTH_HEADER_PARAM],
    responses={200: AdminListGroupMembersResponseSerializer, 404: ErrorResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['GET'])
@admin_required
def admin_list_group_members(request, group_id):
    group, err = _get_group_or_404(group_id)
    if err:
        return err

    members = list(User.collection.filter('group', '==', group_id).fetch(500))
    return Response({
        'group': {'id': group.id, 'name': group.name},
        'total': len(members),
        'members': [_user_dict(u, group_name=group.name) for u in members],
    })


@extend_schema(
    tags=['Groups'],
    summary='Добавить пользователя в группу (admin)',
    parameters=[AUTH_HEADER_PARAM],
    request=AdminAssignGroupRequestSerializer,
    responses={200: AdminGroupMemberActionResponseSerializer, 400: ErrorResponseSerializer, 404: ErrorResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['POST'])
@admin_required
def admin_assign_group(request, user_id):
    group_id = request.data.get('group_id')
    if not group_id:
        return Response({'error': 'Поле "group_id" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    user, err = _get_user_or_404(user_id)
    if err:
        return err

    group, err = _get_group_or_404(group_id)
    if err:
        return err

    user.group = group_id
    user.update()
    log_action(request, 'update', 'User', user_id, {'assigned_group': group_id, 'group_name': group.name})
    return Response({
        'message': f'Пользователь добавлен в группу "{group.name}".',
        'user': _user_dict(user, group_name=group.name),
    })


@extend_schema(
    tags=['Groups'],
    summary='Удалить пользователя из группы (admin)',
    parameters=[AUTH_HEADER_PARAM],
    responses={200: AdminGroupMemberActionResponseSerializer, 400: ErrorResponseSerializer, 404: ErrorResponseSerializer, **ADMIN_RESPONSES},
)
@api_view(['DELETE'])
@admin_required
def admin_remove_from_group(request, user_id):
    user, err = _get_user_or_404(user_id)
    if err:
        return err

    if not user.group:
        return Response(
            {'error': 'Пользователь не состоит ни в одной группе'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.group = ''
    user.update()
    log_action(request, 'update', 'User', user_id, {'removed_from_group': True})
    return Response({'message': 'Пользователь удалён из группы.', 'user': _user_dict(user)})
