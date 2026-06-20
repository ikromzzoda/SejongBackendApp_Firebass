from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='user-register'),
    path('login/',    views.login,    name='user-login'),
    path('logout/',   views.logout,   name='user-logout'),

    # Admin — users
    path('admin/users/',                          views.admin_list_users,    name='admin-users-list'),
    path('admin/users/create/',                   views.admin_create_user,   name='admin-users-create'),
    path('admin/users/<str:user_id>/',            views.admin_get_user,      name='admin-users-get'),
    path('admin/users/<str:user_id>/edit/',       views.admin_edit_user,     name='admin-users-edit'),
    path('admin/pending/',                        views.admin_pending_users, name='admin-pending'),
    path('admin/verify/<str:user_id>/',           views.admin_verify_user,   name='admin-verify'),
    path('admin/set-status/<str:user_id>/',       views.admin_set_status,    name='admin-set-status'),

    # Admin — bulk import
    path('admin/students/import/',                views.admin_bulk_import,          name='admin-bulk-import'),
    path('admin/students/import/template/',       views.admin_bulk_import_template, name='admin-bulk-import-template'),

    # Profile
    path('profile/',        views.get_profile,    name='profile-get'),
    path('profile/update/', views.update_profile, name='profile-update'),
    path('profile/avatar/', views.change_avatar,  name='profile-avatar'),
]
