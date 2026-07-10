from django.urls import path

from . import views

urlpatterns = [
    path('firebase-token/', views.firebase_token, name='chat-firebase-token'),
    path('messages/', views.messages, name='chat-messages'),
    path('messages/<str:message_id>/seen/', views.message_seen, name='chat-message-seen'),
    path('messages/<str:message_id>/', views.delete_message, name='chat-delete-message'),
    path('read/', views.mark_read, name='chat-mark-read'),
    path('read-status/', views.read_status, name='chat-read-status'),
]
