import json
from datetime import datetime
from .models import AuditLog

MAX_LOGS = 200


def _cleanup_old_logs() -> None:
    logs = list(AuditLog.collection.fetch(MAX_LOGS + 50))
    if len(logs) <= MAX_LOGS:
        return
    logs.sort(key=lambda l: l.timestamp or datetime.min, reverse=True)
    for old_log in logs[MAX_LOGS:]:
        AuditLog.collection.delete(f'audit_logs/{old_log.id}')


def log_action(request, action: str, model_name: str, object_id: str, changes: dict = None) -> None:
    try:
        admin_user = ''
        if hasattr(request, 'user_payload'):
            admin_user = request.user_payload.get('username', '')

        log = AuditLog()
        log.admin_user = admin_user
        log.action     = action
        log.model_name = model_name
        log.object_id  = str(object_id)
        log.changes    = json.dumps(changes or {}, ensure_ascii=False)
        log.save()

        _cleanup_old_logs()
    except Exception:
        pass
