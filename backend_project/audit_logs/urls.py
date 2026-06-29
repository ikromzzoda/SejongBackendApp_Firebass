from django.urls import path
from . import views

urlpatterns = [
    path('admin/logs/', views.list_audit_logs, name='audit-logs-list'),
]
