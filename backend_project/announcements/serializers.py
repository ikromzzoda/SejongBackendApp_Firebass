from rest_framework import serializers


class AnnouncementImageSerializer(serializers.Serializer):
    file_id = serializers.CharField()
    url = serializers.CharField()


class AnnouncementSerializer(serializers.Serializer):
    id = serializers.CharField()
    title_taj = serializers.CharField()
    title_rus = serializers.CharField()
    title_eng = serializers.CharField()
    title_kor = serializers.CharField()
    content_taj = serializers.CharField()
    content_rus = serializers.CharField()
    content_eng = serializers.CharField()
    content_kor = serializers.CharField()
    images = AnnouncementImageSerializer(many=True)
    time_posted = serializers.CharField()
    author = serializers.CharField()


class AdminCreateAnnouncementRequestSerializer(serializers.Serializer):
    title_taj = serializers.CharField(required=False, help_text="Обязательно хотя бы одно из title_rus/title_taj")
    title_rus = serializers.CharField(required=False)
    title_eng = serializers.CharField(required=False)
    title_kor = serializers.CharField(required=False)
    content_taj = serializers.CharField(required=False)
    content_rus = serializers.CharField(required=False)
    content_eng = serializers.CharField(required=False)
    content_kor = serializers.CharField(required=False)
    images = serializers.ListField(
        child=serializers.FileField(), required=False,
        help_text="До 10 файлов, JPEG/PNG/WEBP, до 2 МБ каждый",
    )


class AdminEditAnnouncementRequestSerializer(serializers.Serializer):
    title_taj = serializers.CharField(required=False)
    title_rus = serializers.CharField(required=False)
    title_eng = serializers.CharField(required=False)
    title_kor = serializers.CharField(required=False)
    content_taj = serializers.CharField(required=False)
    content_rus = serializers.CharField(required=False)
    content_eng = serializers.CharField(required=False)
    content_kor = serializers.CharField(required=False)
    images = serializers.ListField(
        child=serializers.FileField(), required=False,
        help_text="Заменяет все текущие изображения (до 10 файлов, JPEG/PNG/WEBP, до 2 МБ каждый)",
    )


class AdminCreateAnnouncementResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    announcement = AnnouncementSerializer()


class AdminEditAnnouncementResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    updated_fields = serializers.ListField(child=serializers.CharField())
    announcement = AnnouncementSerializer()


class ListAnnouncementsResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    has_more = serializers.BooleanField()
    announcements = AnnouncementSerializer(many=True)


class GetAnnouncementResponseSerializer(serializers.Serializer):
    announcement = AnnouncementSerializer()
