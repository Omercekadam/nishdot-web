from django.contrib import admin

from .models import BoardApplication, RecruitmentRound


@admin.register(RecruitmentRound)
class RecruitmentRoundAdmin(admin.ModelAdmin):
    list_display = ("title", "is_open", "created_at")
    list_editable = ("is_open",)


@admin.register(BoardApplication)
class BoardApplicationAdmin(admin.ModelAdmin):
    """Asıl okuma yeri karargah (/management/yonetim-alimi/); burası yedek erişim."""

    list_display = ("user", "round", "grade", "weekly_hours", "status", "created_at")
    list_filter = ("round", "status", "grade", "weekly_hours")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_select_related = ("user", "round")
