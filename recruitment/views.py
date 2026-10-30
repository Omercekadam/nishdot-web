"""
Yönetim Kurulu Alımı — Görünümler
==================================

Üye tarafı:      /basvuru/ — yalnızca giriş yapmış üyeler, dönem açıkken, bir kez.
Karargah tarafı: /management/yonetim-alimi/ — başvuruları okuma, süzme, durum
                 verme, CSV ve dönemi açıp kapatma (yalnızca staff).
"""

import csv

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from core.http import safe_redirect_url
from dashboard.views import StaffRequiredMixin

from .forms import BoardApplicationForm
from .models import BoardApplication, RecruitmentRound

APPLY_TEMPLATE = "recruitment/apply.html"


class ApplyView(LoginRequiredMixin, View):
    """Giriş yapmamış ziyaretçi giriş sayfasına, oradan (kayıt dahil) buraya döner."""

    def _context(self, round_, **extra):
        return {"round": round_, **extra}

    def get(self, request):
        round_ = RecruitmentRound.current_open()
        if round_ is None:
            return render(request, APPLY_TEMPLATE, {"closed": True})
        mevcut = BoardApplication.objects.filter(round=round_, user=request.user).first()
        if mevcut:
            return render(request, APPLY_TEMPLATE, self._context(round_, existing=mevcut))
        user = request.user
        form = BoardApplicationForm(initial={
            "department": user.department,
            "phone": user.phone_number,
            "portfolio": user.portfolio_url,
        })
        return render(request, APPLY_TEMPLATE, self._context(round_, form=form))

    def post(self, request):
        round_ = RecruitmentRound.current_open()
        if round_ is None:
            return render(request, APPLY_TEMPLATE, {"closed": True})
        if BoardApplication.objects.filter(round=round_, user=request.user).exists():
            return redirect("recruitment:apply")

        form = BoardApplicationForm(request.POST)
        if not form.is_valid():
            return render(request, APPLY_TEMPLATE, self._context(round_, form=form))

        basvuru = form.save(commit=False)
        basvuru.round = round_
        basvuru.user = request.user
        try:
            basvuru.save()
        except IntegrityError:
            # Çift tıklama: ilk istek kaydetti, ikincisi benzersizlik kısıtına takıldı.
            return redirect("recruitment:apply")
        messages.success(request, "Başvurun alındı. Teşekkürler!")
        return redirect("recruitment:apply")


# --------------------------------------------------------------------- karargah

FILTERS = {
    # GET parametresi → süzgeç; tanımsız değerler yok sayılır
    "pozisyon": lambda qs, v: qs.filter(positions__contains=v) if v in BoardApplication.Position.values else qs,
    "sinif": lambda qs, v: qs.filter(grade=v) if v in BoardApplication.Grade.values else qs,
    "durum": lambda qs, v: qs.filter(status=v) if v in BoardApplication.Status.values else qs,
}


def _filtered_applications(round_, params):
    qs = round_.applications.select_related("user").order_by("-created_at")
    for anahtar, uygula in FILTERS.items():
        if params.get(anahtar):
            qs = uygula(qs, params[anahtar])
    return qs


def _default_title():
    """Eylülden itibaren yeni akademik yıl: 2026 Ekim → "2026-2027 Yönetim Kurulu"."""
    bugun = timezone.localdate()
    yil = bugun.year if bugun.month >= 8 else bugun.year - 1
    return f"{yil}-{yil + 1} Yönetim Kurulu"


class ManageView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/recruitment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        round_ = RecruitmentRound.current()
        context["round"] = round_
        context["default_title"] = _default_title()
        if round_ is not None:
            context["applications"] = _filtered_applications(round_, self.request.GET)
            context["total"] = round_.applications.count()
        context["filters"] = {k: self.request.GET.get(k, "") for k in FILTERS}
        context["positions"] = BoardApplication.Position.choices
        context["grades"] = BoardApplication.Grade.choices
        context["statuses"] = BoardApplication.Status.choices
        return context


@staff_member_required
@require_POST
def create_round(request):
    title = (request.POST.get("title") or "").strip()[:120] or _default_title()
    RecruitmentRound.objects.create(title=title, is_open=False)
    messages.success(request, f"“{title}” dönemi oluşturuldu. Hazır olunca başvuruları aç.")
    return redirect("dashboard:recruitment")


@staff_member_required
@require_POST
def toggle_round(request):
    round_ = RecruitmentRound.current()
    if round_ is not None:
        round_.is_open = not round_.is_open
        round_.save(update_fields=["is_open", "updated_at"])
        if round_.is_open:
            messages.success(request, "Başvurular açıldı; ana sayfada duyuru görünüyor.")
        else:
            messages.info(request, "Başvurular kapatıldı; form ve ana sayfa duyurusu kalktı.")
    return redirect("dashboard:recruitment")


@staff_member_required
@require_POST
def update_status(request):
    app = get_object_or_404(BoardApplication, pk=request.POST.get("app_id"))
    yeni = request.POST.get("status")
    if yeni in BoardApplication.Status.values:
        app.status = yeni
        app.save(update_fields=["status", "updated_at"])
    return redirect(safe_redirect_url(request, request.POST.get("next"), fallback=reverse("dashboard:recruitment")))


def _csv_safe(deger):
    """Excel formül enjeksiyonu: =, +, -, @ ile başlayan hücre metin olarak yazılsın."""
    metin = "" if deger is None else str(deger)
    return "'" + metin if metin[:1] in ("=", "+", "-", "@") else metin


@staff_member_required
def export_csv(request):
    round_ = RecruitmentRound.current()
    if round_ is None:
        return HttpResponse("Henüz alım dönemi yok.", status=404)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="yonetim_basvurulari_{round_.pk}.csv"'
    response.write("﻿".encode("utf8"))  # Excel'in UTF-8'i tanıması için BOM
    writer = csv.writer(response, delimiter=";")  # Türkçe Excel noktalı virgül bekler
    writer.writerow([
        "Ad Soyad", "E-Posta", "Telefon", "Bölüm", "Sınıf", "Pozisyonlar", "Haftalık Süre",
        "Neden katılmak istiyor", "Kulüp hakkında", "Proje / fikir", "Deneyim",
        "Portfolyo", "Eklemek istedikleri", "Durum", "Başvuru Tarihi",
    ])
    for app in _filtered_applications(round_, request.GET):
        writer.writerow([_csv_safe(v) for v in (
            app.user.get_full_name(), app.user.email, app.phone, app.department,
            app.get_grade_display(), ", ".join(app.position_labels), app.get_weekly_hours_display(),
            app.motivation, app.club_opinion, app.project_idea, app.experience,
            app.portfolio, app.extra, app.get_status_display(),
            timezone.localtime(app.created_at).strftime("%Y-%m-%d %H:%M"),
        )])
    return response
