from django.contrib import admin
from .models import Event, Raffle, RaffleParticipant, EventGame, EventApplication, EventImage


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "status", "is_applications_open", "start_date", "end_date")
    list_filter = ("event_type", "status", "is_applications_open")
    search_fields = ("title", "description", "location")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "start_date"
    ordering = ("-start_date",)


class RaffleParticipantInline(admin.TabularInline):
    model = RaffleParticipant
    extra = 0
    readonly_fields = ("user", "joined_at")


@admin.register(Raffle)
class RaffleAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "is_active", "created_at")
    list_filter = ("is_active", "event")
    search_fields = ("title", "event__title")
    readonly_fields = ("secret_id",)
    inlines = [RaffleParticipantInline]


@admin.register(EventGame)
class EventGameAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "url")
    list_filter = ("event",)
    search_fields = ("title", "event__title")


@admin.register(EventApplication)
class EventApplicationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "event", "email", "is_nisantasi_student", "created_at")
    list_filter = ("event", "is_nisantasi_student")
    search_fields = ("full_name", "email")
    # national_id şifreli saklanır — panelde ancak çözülmüş readonly hali gösterilir,
    # ham şifreli alan düzenlenemez.
    readonly_fields = ("national_id", "national_id_hash", "show_decrypted_national_id")

    @admin.display(description="T.C. Kimlik No (çözülmüş)")
    def show_decrypted_national_id(self, obj):
        return obj.decrypted_national_id


@admin.register(EventImage)
class EventImageAdmin(admin.ModelAdmin):
    list_display = ("event", "caption", "created_at")
    list_filter = ("event",)
    search_fields = ("event__title", "caption")
