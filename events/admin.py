from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "status", "is_applications_open", "start_date", "end_date")
    list_filter = ("event_type", "status", "is_applications_open")
    search_fields = ("title", "description", "location")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "start_date"
    ordering = ("-start_date",)
