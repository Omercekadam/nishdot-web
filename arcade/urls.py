from django.urls import path

from . import views

app_name = "arcade"

urlpatterns = [
    path("api/basla/", views.start_run, name="start"),
    path("api/bitir/", views.finish_run, name="finish"),
]
