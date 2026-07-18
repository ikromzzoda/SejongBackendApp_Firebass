from rest_framework import serializers


class ChatMessageSerializer(serializers.Serializer):
    id            = serializers.CharField()
    sender_id     = serializers.CharField()
    sender_name   = serializers.CharField()
    sender_avatar = serializers.CharField()
    text          = serializers.CharField()
    created_at    = serializers.CharField()
    reply_to_id     = serializers.CharField(allow_blank=True, help_text='ID сообщения, на которое дан ответ (пусто, если это не ответ)')
    reply_to_sender = serializers.CharField(allow_blank=True, help_text='Имя автора цитируемого сообщения')
    reply_to_text   = serializers.CharField(allow_blank=True, help_text='Снапшот текста цитируемого сообщения (до 200 символов)')
    type      = serializers.CharField(help_text="Тип сообщения: 'text' | 'image' | 'voice' | 'audio'")
    file_url  = serializers.CharField(allow_blank=True, help_text='Публичная ссылка на вложение (Google Drive)')
    file_name = serializers.CharField(allow_blank=True, help_text='Оригинальное имя файла')
    duration  = serializers.IntegerField(help_text='Длительность аудио в секундах (0, если не передана)')


class SendMessageRequestSerializer(serializers.Serializer):
    text     = serializers.CharField(required=False, max_length=2000, help_text='Текст сообщения; при наличии файла — подпись (необязательна)')
    file     = serializers.FileField(required=False, help_text='Фото (JPEG/PNG/WebP/GIF, до 3 МБ) или аудио (до 5 МБ)')
    type     = serializers.CharField(required=False, help_text="'voice' — пометить аудиофайл как голосовое сообщение")
    duration = serializers.IntegerField(required=False, help_text='Длительность аудио в секундах (для отрисовки плеера)')
    reply_to = serializers.CharField(required=False, help_text='ID сообщения этого же чата, на которое даётся ответ')


class SendMessageResponseSerializer(serializers.Serializer):
    message      = serializers.CharField()
    chat_message = ChatMessageSerializer()


class ListMessagesResponseSerializer(serializers.Serializer):
    total    = serializers.IntegerField()
    has_more = serializers.BooleanField()
    messages = ChatMessageSerializer(many=True)


class MarkReadResponseSerializer(serializers.Serializer):
    message      = serializers.CharField()
    last_read_at = serializers.CharField()


class ReadStatusEntrySerializer(serializers.Serializer):
    user_id      = serializers.CharField()
    user_name    = serializers.CharField()
    user_avatar  = serializers.CharField()
    last_read_at = serializers.CharField()


class ReadStatusResponseSerializer(serializers.Serializer):
    total       = serializers.IntegerField()
    read_status = ReadStatusEntrySerializer(many=True)


class SeenByResponseSerializer(serializers.Serializer):
    total   = serializers.IntegerField()
    seen_by = ReadStatusEntrySerializer(many=True)


class ChatMemberSerializer(serializers.Serializer):
    user_id  = serializers.CharField()
    username = serializers.CharField()
    fullname = serializers.CharField(allow_blank=True)
    avatar   = serializers.CharField(allow_blank=True)


class ChatMembersResponseSerializer(serializers.Serializer):
    total   = serializers.IntegerField(help_text='Количество студентов в чате группы')
    members = ChatMemberSerializer(many=True)


class ClearChatResponseSerializer(serializers.Serializer):
    message           = serializers.CharField()
    messages_deleted  = serializers.IntegerField()


class FirebaseTokenResponseSerializer(serializers.Serializer):
    firebase_token = serializers.CharField()
    uid            = serializers.CharField()
    group_id       = serializers.CharField()
    expires_in     = serializers.IntegerField()
