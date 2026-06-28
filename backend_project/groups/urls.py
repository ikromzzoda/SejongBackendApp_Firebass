from django.urls import path
from . import views

urlpatterns = [
    path('admin/',                               views.admin_list_groups,        name='groups-list'),
    path('admin/create/',                        views.admin_create_group,       name='groups-create'),
    path('admin/<str:group_id>/delete/',         views.admin_delete_group,       name='groups-delete'),
    path('admin/<str:group_id>/rename/',         views.admin_rename_group,       name='groups-rename'),
    path('admin/<str:group_id>/members/',        views.admin_list_group_members, name='groups-members'),
    path('admin/assign/<str:user_id>/',          views.admin_assign_group,       name='groups-assign'),
    path('admin/unassign/<str:user_id>/',        views.admin_remove_from_group,  name='groups-unassign'),
]
