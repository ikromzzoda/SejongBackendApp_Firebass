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


@api_view(['GET'])
@admin_required
def admin_list_groups(request):
    try:
        limit = min(int(request.query_params.get('limit', 20)), 100)
    except (ValueError, TypeError):
        limit = 20

    raw = list(Group.collection.fetch(limit + 1))
    has_more = len(raw) > limit
    groups = [{'id': g.id, 'name': g.name} for g in raw[:limit]]
    return Response({'total': len(groups), 'has_more': has_more, 'groups': groups})


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
    return Response(
        {'message': f'Группа "{name}" создана.', 'group': {'id': group.id, 'name': group.name}},
        status=status.HTTP_201_CREATED,
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
    return Response({'message': f'Группа "{group.name}" удалена.'})


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
    return Response({'message': 'Группа переименована.', 'group': {'id': group.id, 'name': group.name}})


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
    return Response({
        'message': f'Пользователь добавлен в группу "{group.name}".',
        'user': _user_dict(user, group_name=group.name),
    })


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
    return Response({'message': 'Пользователь удалён из группы.', 'user': _user_dict(user)})
