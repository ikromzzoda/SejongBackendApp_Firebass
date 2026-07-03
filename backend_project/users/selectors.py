from groups.models import Group


def _resolve_group_name(group_id: str, cache: dict | None = None) -> str:
    if not group_id:
        return ''
    if cache is not None:
        return cache.get(group_id, group_id)
    try:
        g = Group.collection.get(f'groups/{group_id}')
        return g.name if g else group_id
    except Exception:
        return group_id


def _user_dict(user, groups_cache: dict | None = None, full: bool = False):
    d = {
        'id':                  user.id,
        'username':            user.username,
        'fullname':            user.fullname,
        'email':               user.email,
        'phone_number':        user.phone_number,
        'status':              user.status,
        'verification_status': user.verification_status,
        'group_id':            user.group or '',
        'group':               _resolve_group_name(user.group or '', groups_cache),
        'avatar':              user.avatar or '',
        'date_joined':         str(user.date_joined) if user.date_joined else '',
    }
    if full:
        d['date_of_birth'] = user.date_of_birth or ''
        d['device_token']  = user.device_token or ''
    return d
