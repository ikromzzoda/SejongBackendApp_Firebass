from django.urls import path
from . import views

urlpatterns = [
    # Schedules — Admin
    path('admin/schedules/',                              views.admin_list_schedules,  name='admin-schedule-list'),
    path('admin/schedules/create/',                       views.admin_create_schedule, name='admin-schedule-create'),
    path('admin/schedules/<str:schedule_id>/',            views.admin_get_schedule,    name='admin-schedule-get'),
    path('admin/schedules/<str:schedule_id>/edit/',       views.admin_edit_schedule,   name='admin-schedule-edit'),
    path('admin/schedules/<str:schedule_id>/delete/',     views.admin_delete_schedule, name='admin-schedule-delete'),

    # Schedules — Authenticated users
    path('schedules/all/',                                views.get_all_schedules,     name='all-schedules'),
    path('schedules/group/<str:group_name>/',             views.get_group_schedule,    name='group-schedule'),

    # Notifications — Admin
    path('admin/notifications/',                          views.admin_list_notifications,  name='admin-notification-list'),
    path('admin/notifications/create/',                   views.admin_create_notification, name='admin-notification-create'),
    path('admin/notifications/<str:notif_id>/',           views.admin_get_notification,    name='admin-notification-get'),
    path('admin/notifications/<str:notif_id>/edit/',      views.admin_edit_notification,   name='admin-notification-edit'),
    path('admin/notifications/<str:notif_id>/delete/',    views.admin_delete_notification, name='admin-notification-delete'),

    # Notifications — Authenticated users
    path('notifications/',                                views.get_my_notifications,      name='my-notifications'),

    # Privacy Policy — Admin
    path('admin/privacy/',                                    views.admin_list_privacy_sections,   name='admin-privacy-list'),
    path('admin/privacy/create/',                             views.admin_create_privacy_section,  name='admin-privacy-create'),
    path('admin/privacy/<str:section_id>/edit/',              views.admin_edit_privacy_section,    name='admin-privacy-edit'),
    path('admin/privacy/<str:section_id>/delete/',            views.admin_delete_privacy_section,  name='admin-privacy-delete'),

    # Privacy Policy — Public (authenticated)
    path('privacy/',                                          views.get_privacy_policy,            name='privacy-policy'),
]
