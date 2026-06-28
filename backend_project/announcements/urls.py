from django.urls import path
from . import views

urlpatterns = [
    # Public (jwt_required)
    path('',                    views.list_announcements, name='announcements-list'),
    path('<str:ann_id>/',       views.get_announcement,  name='announcements-detail'),

    # Admin
    path('admin/create/',                    views.admin_create_announcement, name='admin-announcements-create'),
    path('admin/<str:ann_id>/edit/',         views.admin_edit_announcement,   name='admin-announcements-edit'),
    path('admin/<str:ann_id>/delete/',       views.admin_delete_announcement, name='admin-announcements-delete'),
]
