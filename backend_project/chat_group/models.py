from fireo.models import Model
from fireo.fields import TextField, DateTime


class ChatMessage(Model):
    """
    Сообщение группового чата.

    Хранится в сабколлекции groups/{group_id}/chat_messages, чтобы
    security rules Firestore могли проверять членство по group_id из
    custom claims (см. firestore.rules в корне проекта).
    """
    sender_id     = TextField(required=True)
    sender_name   = TextField()
    sender_avatar = TextField()
    text          = TextField(required=True)
    # Без auto=True: FireO пишет SERVER_TIMESTAMP-сентинел, из-за чего
    # значение недоступно сразу после save() для ответа клиенту
    created_at    = DateTime()

    class Meta:
        collection_name = 'chat_messages'


class ChatReadStatus(Model):
    """
    Указатель чтения: до какого момента пользователь дочитал чат группы.

    Document ID = ID пользователя, хранится в
    groups/{group_id}/chat_read_status/{user_id}. Сообщение считается
    просмотренным пользователем, если его created_at <= last_read_at
    (та же модель, что в Telegram — без списка просмотров на каждое сообщение).
    """
    user_name    = TextField()
    user_avatar  = TextField()
    last_read_at = DateTime(required=True)

    class Meta:
        collection_name = 'chat_read_status'
