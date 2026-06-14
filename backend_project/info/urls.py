from django.urls import path
from . import views

urlpatterns = [
    # Admin
    path('admin/schedules/',                              views.admin_list_schedules,  name='admin-schedule-list'),
    path('admin/schedules/create/',                       views.admin_create_schedule, name='admin-schedule-create'),
    path('admin/schedules/<str:schedule_id>/',            views.admin_get_schedule,    name='admin-schedule-get'),
    path('admin/schedules/<str:schedule_id>/edit/',       views.admin_edit_schedule,   name='admin-schedule-edit'),
    path('admin/schedules/<str:schedule_id>/delete/',     views.admin_delete_schedule, name='admin-schedule-delete'),

    # Authenticated users
    path('schedules/all/',                  views.get_all_schedules,  name='all-schedules'),
    path('schedules/group/<str:group_name>/', views.get_group_schedule, name='group-schedule'),
]
