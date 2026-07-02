from rest_framework import serializers

ACTION_CHOICES = ('create', 'update', 'delete')


class AuditLogSerializer(serializers.Serializer):
    id = serializers.CharField()
    admin_user = serializers.CharField()
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    model_name = serializers.CharField()
    object_id = serializers.CharField()
    changes = serializers.DictField(help_text="Изменённые поля (произвольный JSON-объект)")
    timestamp = serializers.CharField()


class ListAuditLogsResponseSerializer(serializers.Serializer):
    total = serializers.CharField(
        help_text='Точное число (int) либо строка вида "150+", если есть ещё записи за пределами выборки.',
    )
    offset = serializers.IntegerField()
    limit = serializers.IntegerField()
    has_more = serializers.BooleanField()
    logs = AuditLogSerializer(many=True)
