from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='user-register'),
    path('login/',    views.login,    name='user-login'),
    path('logout/',   views.logout,   name='user-logout'),

    # Admin
    path('admin/pending/',                      views.admin_pending_users, name='admin-pending'),
    path('admin/verify/<str:user_id>/',         views.admin_verify_user,   name='admin-verify'),
    path('admin/set-status/<str:user_id>/',     views.admin_set_status,    name='admin-set-status'),
    path('admin/assign-group/<str:user_id>/',   views.admin_assign_group,  name='admin-assign-group'),
    path('admin/groups/',                       views.admin_list_groups,   name='admin-groups-list'),
    path('admin/groups/create/',                views.admin_create_group,  name='admin-groups-create'),
    path('admin/groups/<str:group_id>/delete/', views.admin_delete_group,  name='admin-groups-delete'),

    # Profile
    path('profile/update/',       views.update_profile, name='profile-update'),
    path('profile/avatar/',       views.change_avatar,  name='profile-avatar'),
]
