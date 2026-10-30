from django.urls import path

from . import views

app_name = "recruitment"

urlpatterns = [
    path("", views.ApplyView.as_view(), name="apply"),
]
