from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/",  include("users.urls")),
    path("api/groups/", include("groups.urls")),
    path("api/books/", include("ebook_and_chat.urls")),
    path("api/info/", include("info.urls")),
    path("api/announcements/", include("announcements.urls")),
    path("api/audit/", include("audit_logs.urls")),
    path("api/chat/", include("chat_group.urls")),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
