from rest_framework import serializers


class BookSerializer(serializers.Serializer):
    id = serializers.CharField()
    title_taj = serializers.CharField()
    title_rus = serializers.CharField()
    title_eng = serializers.CharField()
    title_kor = serializers.CharField()
    description_taj = serializers.CharField()
    description_rus = serializers.CharField()
    description_eng = serializers.CharField()
    description_kor = serializers.CharField()
    author = serializers.CharField()
    genres = serializers.CharField()
    published_date = serializers.CharField()
    created_at = serializers.SerializerMethodField()
    cover = serializers.CharField()
    cover_id = serializers.CharField()
    file = serializers.CharField()
    file_id = serializers.CharField()

    def get_created_at(self, obj):
        return str(obj.created_at) if obj.created_at else ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {k: ('' if v is None else v) for k, v in data.items()}
