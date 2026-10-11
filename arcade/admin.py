from django.contrib import admin

from .models import Competition, GameRun
from .services import display_name


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("name", "starts_at", "ends_at", "is_visible")
    list_editable = ("is_visible",)


@admin.register(GameRun)
class GameRunAdmin(admin.ModelAdmin):
    """Ödül için iletişim: e-posta ve doğrulama durumu listede görünür."""

    list_display = ("oyuncu", "eposta", "dogrulandi", "score", "sure", "created_at", "is_disqualified")
    list_filter = ("is_disqualified", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    ordering = ("-score", "created_at")
    list_select_related = ("user",)
    readonly_fields = ("user", "score", "duration_ms", "created_at")
    actions = ("diskalifiye_et", "diskalifiyeyi_kaldir")

    def has_add_permission(self, request):
        return False  # skorlar yalnızca oyundan gelir

    @admin.display(description="Oyuncu", ordering="user__first_name")
    def oyuncu(self, obj):
        return display_name(obj.user) if obj.user else "— sahipsiz —"

    @admin.display(description="E-posta")
    def eposta(self, obj):
        return obj.user.email if obj.user else ""

    @admin.display(description="E-posta doğrulandı", boolean=True)
    def dogrulandi(self, obj):
        return obj.user.is_verified if obj.user else None

    @admin.display(description="Süre", ordering="duration_ms")
    def sure(self, obj):
        dakika, saniye = divmod(obj.duration_ms // 1000, 60)
        return f"{dakika}:{saniye:02d}"

    @admin.action(description="Seçili skorları diskalifiye et")
    def diskalifiye_et(self, request, queryset):
        adet = queryset.update(is_disqualified=True)
        self.message_user(request, f"{adet} skor diskalifiye edildi; tablodan düştü.")

    @admin.action(description="Diskalifiyeyi kaldır")
    def diskalifiyeyi_kaldir(self, request, queryset):
        adet = queryset.update(is_disqualified=False)
        self.message_user(request, f"{adet} skorun diskalifiyesi kaldırıldı.")
