from fireo.models import Model
from fireo.fields import TextField, DateTime


class Group(Model):
    name       = TextField(required=True)
    created_at = DateTime(auto=True)

    class Meta:
        collection_name = 'groups'
