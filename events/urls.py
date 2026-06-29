from django.urls import path
from .views import EventDetailView, EventApplyWizardView

app_name = "events"

urlpatterns = [
    path("<slug:slug>/", EventDetailView.as_view(), name="detail"),
    path("<slug:slug>/apply/", EventApplyWizardView.as_view(), name="apply"),
]
