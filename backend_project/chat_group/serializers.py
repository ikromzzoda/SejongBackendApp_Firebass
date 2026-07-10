from rest_framework import serializers


class ChatMessageSerializer(serializers.Serializer):
    id            = serializers.CharField()
    sender_id     = serializers.CharField()
    sender_name   = serializers.CharField()
    sender_avatar = serializers.CharField()
    text          = serializers.CharField()
    created_at    = serializers.CharField()


class SendMessageRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000)


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


class FirebaseTokenResponseSerializer(serializers.Serializer):
    firebase_token = serializers.CharField()
    uid            = serializers.CharField()
    group_id       = serializers.CharField()
    expires_in     = serializers.IntegerField()
