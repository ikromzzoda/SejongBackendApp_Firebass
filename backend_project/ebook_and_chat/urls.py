from django.urls import path
from . import views

urlpatterns = [
    # Public (jwt_required)
    path('',                      views.list_books, name='books-list'),
    path('<str:book_id>/',        views.get_book,   name='books-detail'),

    # Admin
    path('admin/create/',                    views.admin_create_book, name='admin-books-create'),
    path('admin/<str:book_id>/edit/',        views.admin_edit_book,   name='admin-books-edit'),
    path('admin/<str:book_id>/delete/',      views.admin_delete_book, name='admin-books-delete'),
]
