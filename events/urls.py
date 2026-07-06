from django.urls import path
from .views import EventDetailView, EventApplyWizardView, RaffleJoinView

app_name = "events"

urlpatterns = [
    path("raffle/join/<uuid:secret_id>/", RaffleJoinView.as_view(), name="raffle_join"),
    path("<slug:slug>/", EventDetailView.as_view(), name="detail"),
    path("<slug:slug>/apply/", EventApplyWizardView.as_view(), name="apply"),
]
