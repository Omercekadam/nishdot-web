from django.urls import path
from .views import HomePageView
from . import api

app_name = "pages"

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("api/contact", api.contact_api_view, name="api_contact"),
]
