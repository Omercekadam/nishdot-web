from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="index"),
    path("api/update-status/", views.update_application_status, name="api_update_status"),
    path("api/export-csv/", views.export_applications_csv, name="api_export_csv"),
    
    # Workspace Routes
    path('events/', views.EventBuilderView.as_view(), name='events'),
    path('notes/', views.MeetingNotesView.as_view(), name='notes'),
    path('tasks/', views.KanbanView.as_view(), name='tasks'),
    path('assets/', views.AssetsView.as_view(), name='assets'),
    path('members/', views.MembersDirectoryView.as_view(), name='members'),
    path('broadcast/', views.BroadcastCenterView.as_view(), name='broadcast'),
]
