from django.contrib import admin
from .models import GameJam, SuggestedTeam, JamApplication

class JamApplicationInline(admin.TabularInline):
    model = JamApplication
    extra = 0
    fields = ("full_name", "jam_role", "team_status", "status")
    readonly_fields = ("full_name", "jam_role", "team_status")

class SuggestedTeamInline(admin.TabularInline):
    model = SuggestedTeam
    extra = 0
    fields = ("name", "status")

@admin.register(GameJam)
class GameJamAdmin(admin.ModelAdmin):
    list_display = ("event", "application_deadline", "is_applications_open", "max_team_size")
    list_filter = ("is_applications_open",)
    search_fields = ("event__title",)
    inlines = [SuggestedTeamInline]

@admin.register(SuggestedTeam)
class SuggestedTeamAdmin(admin.ModelAdmin):
    list_display = ("name", "jam", "status", "reviewed_by")
    list_filter = ("status", "jam")
    search_fields = ("name", "jam__event__title")
    inlines = [JamApplicationInline]

@admin.register(JamApplication)
class JamApplicationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "jam", "jam_role", "team_status", "status")
    list_filter = ("status", "team_status", "jam", "jam_role")
    search_fields = ("full_name", "email", "team_name")
