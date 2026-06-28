from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "status", "start_date", "end_date")
    list_filter = ("event_type", "status")
    search_fields = ("title", "description", "location")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "start_date"
    ordering = ("-start_date",)
