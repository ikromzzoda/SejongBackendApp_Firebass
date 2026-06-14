from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/books/", include("ebook_and_chat.urls")),
    path("api/info/", include("info.urls")),
]
