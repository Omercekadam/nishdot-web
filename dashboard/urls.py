from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="index"),
    path("api/update-status/", views.update_application_status, name="api_update_status"),
    path("api/export-csv/", views.export_applications_csv, name="api_export_csv"),
    
    # Workspace Routes
    path('events/', views.EventBuilderView.as_view(), name='events'),
    path('api/save-event/', views.api_save_event, name='api_save_event'),
    path('api/toggle-jam-status/', views.api_toggle_jam_status, name='api_toggle_jam_status'),
    path('notes/', views.MeetingNotesView.as_view(), name='notes'),
    path('api/save-note/', views.api_save_note, name='api_save_note'),
    path('api/delete-note/', views.api_delete_note, name='api_delete_note'),
    path('tasks/', views.KanbanView.as_view(), name='tasks'),
    path('api/save-task/', views.api_save_task, name='api_save_task'),
    path('api/update-task-status/', views.api_update_task_status, name='api_update_task_status'),
    path('api/delete-task/', views.api_delete_task, name='api_delete_task'),
    path('assets/', views.AssetsView.as_view(), name='assets'),
    path('api/save-asset/', views.api_save_asset, name='api_save_asset'),
    path('api/delete-asset/', views.api_delete_asset, name='api_delete_asset'),
    path('members/', views.MembersDirectoryView.as_view(), name='members'),
    path('api/update-user-profile/', views.api_update_user_profile, name='api_update_user_profile'),
    path('broadcast/', views.BroadcastCenterView.as_view(), name='broadcast'),
    path('api/create-broadcast/', views.api_create_broadcast, name='api_create_broadcast'),
    path('api/dismiss-announcement/<int:announcement_id>/', views.api_dismiss_announcement, name='api_dismiss_announcement'),
    path('api/resolve-log/', views.api_resolve_log, name='api_resolve_log'),
    path('api/delete-log/', views.api_delete_log, name='api_delete_log'),
    
    # Raffles
    path('raffles/', views.RaffleListView.as_view(), name='raffles'),
    path('api/create-raffle/', views.api_create_raffle, name='api_create_raffle'),
    path('raffles/<int:pk>/qr/', views.RaffleQRView.as_view(), name='raffle_qr'),
    path('raffles/<int:pk>/draw/', views.RaffleDrawView.as_view(), name='raffle_draw'),
    path('api/raffles/<int:pk>/participants/', views.api_raffle_participants, name='api_raffle_participants'),
    path('api/raffles/<int:pk>/remove-participant/', views.api_raffle_remove_participant, name='api_raffle_remove_participant'),
    path('api/raffles/<int:pk>/pick-winner/', views.api_raffle_pick_winner, name='api_raffle_pick_winner'),
    path('api/raffles/<int:pk>/toggle/', views.api_raffle_toggle, name='api_raffle_toggle'),
]
