from fireo.models import Model
from fireo.fields import TextField, DateTime


class AuditLog(Model):
    admin_user = TextField()
    action     = TextField()   # "create" | "update" | "delete"
    model_name = TextField()   # "User" | "Group" | "Announcement" | "Book" | "Schedule" | "Notification"
    object_id  = TextField()
    changes    = TextField()   # JSON string with change details
    timestamp  = DateTime(auto=True)

    class Meta:
        collection_name = 'audit_logs'
