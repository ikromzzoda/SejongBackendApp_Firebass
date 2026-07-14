"""
Синхронизация денормализованных данных пользователя в документах чата.

Аватар отправителя копируется в каждый документ сообщения при записи
(sender_avatar в chat_messages, user_avatar в chat_read_status), поэтому
после смены аватара его нужно проставить и в уже отправленных сообщениях —
иначе история чата продолжает показывать старый аватар.
"""

import threading

from .models import ChatMessage, ChatReadStatus


def sync_user_avatar(user_id: str, group_id: str, avatar: str) -> None:
    """Проставить новый аватар в старых сообщениях и указателе чтения группы."""
    if not group_id:
        return

    try:
        query = ChatMessage.collection.parent(f'groups/{group_id}').filter('sender_id', '==', user_id)
        for msg in query.fetch():
            msg.sender_avatar = avatar
            msg.update()
    except Exception:
        pass

    try:
        rs = ChatReadStatus.collection.get(f'groups/{group_id}/chat_read_status/{user_id}')
        if rs:
            rs.user_avatar = avatar
            rs.update()
    except Exception:
        pass


def sync_user_avatar_async(user_id: str, group_id: str, avatar: str) -> None:
    """Запустить sync_user_avatar в фоне: ответ на смену аватара не ждёт
    перезаписи истории чата. Best-effort — поток теряется при рестарте воркера."""
    thread = threading.Thread(
        target=sync_user_avatar,
        args=(user_id, group_id, avatar),
        daemon=True,
    )
    thread.start()
