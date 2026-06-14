from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Group
from users.models import User
from utils.decorators import admin_required


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


@api_view(['GET'])
@admin_required
def admin_list_groups(request):
    """Список всех групп."""
    groups = list(Group.collection.fetch(100))
    return Response({'groups': [{'id': g.id, 'name': g.name} for g in groups]})


@api_view(['POST'])
@admin_required
def admin_create_group(request):
    """Создать новую группу.
    Body: { "name": "название группы" }
    """
    name = request.data.get('name', '').strip()
    if not name:
        return Response({'error': 'Поле "name" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    existing = list(Group.collection.filter('name', '==', name).fetch(1))
    if existing:
        return Response({'error': f'Группа с именем "{name}" уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    group = Group()
    group.name = name
    group.save()
    return Response(
        {'message': f'Группа "{name}" создана.', 'group': {'id': group.id, 'name': group.name}},
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@admin_required
def admin_delete_group(request, group_id):
    """Удалить группу по ID."""
    try:
        group = Group.collection.get(f'groups/{group_id}')
    except Exception:
        group = None
    if not group:
        return Response({'error': 'Группа не найдена'}, status=status.HTTP_404_NOT_FOUND)

    Group.collection.delete(f'groups/{group_id}')
    return Response({'message': f'Группа "{group.name}" удалена.'})


@api_view(['POST'])
@admin_required
def admin_assign_group(request, user_id):
    """Назначить пользователя в группу.
    Body: { "group_id": "<id группы>" }
    """
    group_id = request.data.get('group_id')
    if not group_id:
        return Response({'error': 'Поле "group_id" обязательно'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        group = Group.collection.get(f'groups/{group_id}')
    except Exception:
        group = None
    if not group:
        return Response({'error': 'Группа не найдена'}, status=status.HTTP_404_NOT_FOUND)

    try:
        user = User.collection.get(f'users/{user_id}')
    except Exception:
        user = None
    if not user:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    user.group = group_id
    user.update()
    return Response({
        'message': f'Пользователь добавлен в группу "{group.name}".',
        'user': _user_dict(user, group_name=group.name),
    })
