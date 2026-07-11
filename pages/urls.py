from django.urls import path
from . import views, api

app_name = "pages"

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),
    path("api/contact", api.contact_api_view, name="api_contact"),
    path("legal/<slug:slug>/", views.LegalDocumentDetailView.as_view(), name="legal_document"),
]
