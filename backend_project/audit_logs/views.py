import json
from datetime import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response

from utils.decorators import admin_required
from .models import AuditLog


def _log_dict(log) -> dict:
    try:
        changes = json.loads(log.changes or '{}')
    except (json.JSONDecodeError, TypeError):
        changes = {}
    return {
        'id':         log.id,
        'admin_user': log.admin_user or '',
        'action':     log.action or '',
        'model_name': log.model_name or '',
        'object_id':  log.object_id or '',
        'changes':    changes,
        'timestamp':  str(log.timestamp) if log.timestamp else '',
    }


@api_view(['GET'])
@admin_required
def list_audit_logs(request):
    try:
        limit = min(max(int(request.query_params.get('limit', 50)), 1), 200)
    except (ValueError, TypeError):
        limit = 50

    try:
        offset = max(int(request.query_params.get('offset', 0)), 0)
    except (ValueError, TypeError):
        offset = 0

    action_filter = request.query_params.get('action', '').strip()
    model_filter  = request.query_params.get('model_name', '').strip()
    admin_filter  = request.query_params.get('admin_user', '').strip()

    fetch_limit = offset + limit + 1  # +1 чтобы определить has_more

    if action_filter:
        logs = list(AuditLog.collection.filter('action', '==', action_filter).fetch(fetch_limit))
    elif model_filter:
        logs = list(AuditLog.collection.filter('model_name', '==', model_filter).fetch(fetch_limit))
    elif admin_filter:
        logs = list(AuditLog.collection.filter('admin_user', '==', admin_filter).fetch(fetch_limit))
    else:
        logs = list(AuditLog.collection.fetch(fetch_limit))

    logs.sort(key=lambda l: l.timestamp or datetime.min, reverse=True)

    page     = logs[offset:offset + limit]
    has_more = len(logs) > offset + limit

    return Response({
        'total':    len(logs) if not has_more else f'{offset + limit}+',
        'offset':   offset,
        'limit':    limit,
        'has_more': has_more,
        'logs':     [_log_dict(l) for l in page],
    })
