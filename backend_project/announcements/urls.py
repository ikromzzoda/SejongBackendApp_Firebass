from django.urls import path
from . import views

urlpatterns = [
    # Связаться с админом (без авторизации) — до <str:ann_id>/, иначе перехватится
    path('contact/',            views.contact_admin,      name='announcements-contact-admin'),

    # Public (jwt_required)
    path('',                    views.list_announcements, name='announcements-list'),
    path('<str:ann_id>/',       views.get_announcement,  name='announcements-detail'),

    # Admin
    path('admin/create/',                    views.admin_create_announcement, name='admin-announcements-create'),
    path('admin/<str:ann_id>/edit/',         views.admin_edit_announcement,   name='admin-announcements-edit'),
    path('admin/<str:ann_id>/delete/',       views.admin_delete_announcement, name='admin-announcements-delete'),

    # Admin: обращения пользователей
    path('admin/contact-messages/',                       views.admin_list_contact_messages,     name='admin-contact-messages-list'),
    path('admin/contact-messages/<str:msg_id>/read/',     views.admin_mark_contact_message_read, name='admin-contact-messages-read'),
    path('admin/contact-messages/<str:msg_id>/delete/',   views.admin_delete_contact_message,    name='admin-contact-messages-delete'),
]
