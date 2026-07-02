from rest_framework import serializers

from .models import GENRES_CHOICES


class BookCreateRequestSerializer(serializers.Serializer):
    title_rus = serializers.CharField()
    title_taj = serializers.CharField(required=False)
    title_eng = serializers.CharField(required=False)
    title_kor = serializers.CharField(required=False)
    description_taj = serializers.CharField(required=False)
    description_rus = serializers.CharField(required=False)
    description_eng = serializers.CharField(required=False)
    description_kor = serializers.CharField(required=False)
    author = serializers.CharField(required=False)
    published_date = serializers.CharField(required=False)
    genres = serializers.ChoiceField(choices=GENRES_CHOICES, required=False)
    file = serializers.FileField(help_text="PDF или EPUB, до 100 МБ")
    cover = serializers.FileField(required=False, help_text="JPEG/PNG/WEBP, до 2 МБ")


class BookEditRequestSerializer(serializers.Serializer):
    title_taj = serializers.CharField(required=False)
    title_rus = serializers.CharField(required=False)
    title_eng = serializers.CharField(required=False)
    title_kor = serializers.CharField(required=False)
    description_taj = serializers.CharField(required=False)
    description_rus = serializers.CharField(required=False)
    description_eng = serializers.CharField(required=False)
    description_kor = serializers.CharField(required=False)
    author = serializers.CharField(required=False)
    published_date = serializers.CharField(required=False)
    genres = serializers.ChoiceField(choices=GENRES_CHOICES, required=False)
    file = serializers.FileField(required=False, help_text="PDF или EPUB, до 100 МБ — заменяет текущий файл")
    cover = serializers.FileField(required=False, help_text="JPEG/PNG/WEBP, до 2 МБ — заменяет текущую обложку")


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

    def get_created_at(self, obj) -> str:
        return str(obj.created_at) if obj.created_at else ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {k: ('' if v is None else v) for k, v in data.items()}


class BookCreateResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    book = BookSerializer()


class BookEditResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    updated_fields = serializers.ListField(child=serializers.CharField())
    book = BookSerializer()


class ListBooksResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()
    books = BookSerializer(many=True)


class GetBookResponseSerializer(serializers.Serializer):
    book = BookSerializer()
