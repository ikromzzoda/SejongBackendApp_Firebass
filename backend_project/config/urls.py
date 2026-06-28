from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/",  include("users.urls")),
    path("api/groups/", include("groups.urls")),
    path("api/books/", include("ebook_and_chat.urls")),
    path("api/info/", include("info.urls")),
    path("api/announcements/", include("announcements.urls")),
]
