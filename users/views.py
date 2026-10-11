import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from core.http import get_client_ip, safe_redirect_url
from dashboard.models import Announcement, SecurityLog
from jams.models import JamApplication

from .api import _log_rate_limited
from .forms import UserLoginForm, UserProfileUpdateForm, UserRegisterForm
from .tokens import email_verification_token
from .verification import send_verification_email

logger = logging.getLogger(__name__)

User = get_user_model()

INVALID_LINK_MESSAGE = "Link geçersiz veya süresi dolmuş; giriş yapıp yeni link isteyebilirsin."

class UserRegisterView(TemplateView):
    """
    Kayıt sayfasını render eder. Sayfadaki form JS ile users:api_register'a
    gönderim yapar; API kullanıcıyı oluşturur, oturumu açar ve doğrulama
    linkini mailler.

    GÜVENLİK: Bu view POST kabul ETMEZ (TemplateView POST'a 405 döner).
    Tek kayıt yolu, hız sınırlı API'dir.
    """
    template_name = "users/register.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("users:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Şablon, alanları (widget class'ları ile) form üzerinden render ediyor.
        context['form'] = UserRegisterForm()
        return context

# Stand cihazı ve kampüs Wi-Fi'ı tek IP'den çıkar; başarılı girişler de sayılır.
@method_decorator(ratelimit(key='ip', rate='30/5m', block=False), name='post')
class UserLoginView(LoginView):
    template_name = "users/login.html"
    form_class = UserLoginForm
    redirect_authenticated_user = True



    def post(self, request, *args, **kwargs):
        if getattr(request, 'limited', False):
            SecurityLog.objects.create(
                ip_address=get_client_ip(request),
                action=SecurityLog.ActionType.LOGIN_BRUTE_FORCE,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return render(request, 'pages/429.html', {'message': 'Çok fazla hatalı giriş denemesi yaptınız. Lütfen 5 dakika sonra tekrar deneyiniz.'}, status=429)
        return super().post(request, *args, **kwargs)
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "users/dashboard.html"
    login_url = "users:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Başvuru ya hesaba doğrudan bağlıdır (yeni kayıtlar) ya da yalnızca
        # e-posta ile eşleşir (hesap açılmadan önce yapılmış eski başvurular).
        # select_related olmadan şablondaki jam.event.title her satırda iki
        # ekstra sorgu atar.
        applications = (
            JamApplication.objects
            .filter(Q(applicant=user) | Q(email__iexact=user.email))
            .select_related("jam__event")
            .distinct()
            .order_by("-created_at")
        )

        # Hedef kitle koşulu ayrı bir Q'da toplanır; published_to_site kısıtı
        # bunun DIŞINDA kalırsa (eski hâli) yalnızca e-posta olarak gönderilen
        # duyurular da site panelinde görünüyordu.
        hedef = Q(target_audience="all") | Q(custom_users=user)

        if user.is_staff or user.role in (User.Role.BOARD, User.Role.ADMIN):
            hedef |= Q(target_audience="board")
        else:
            hedef |= Q(target_audience="members")

        # 6563 sayılı Kanun e-posta/SMS gönderimini düzenler; kullanıcının kendi
        # isteğiyle açtığı panelde içerik göstermek ticari elektronik ileti
        # değildir. Bu yüzden "consented" hedefi site içinde herkese açıktır.
        hedef |= Q(target_audience="consented")

        announcements = (
            Announcement.objects
            .filter(Q(published_to_site=True) & hedef)
            .exclude(dismissed_by=user)
            .distinct()
            .order_by("-created_at")
        )

        context["applications"] = applications
        context["announcements"] = announcements
        if "form" not in context:
            context["form"] = UserProfileUpdateForm(instance=user)
        return context

    def post(self, request, *args, **kwargs):
        form = UserProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil bilgilerin başarıyla güncellendi.")
            return redirect("users:dashboard")

        context = self.get_context_data(form=form)
        return self.render_to_response(context)


def verify_email_view(request, uidb64, token):
    """
    Maildeki doğrulama linki. Giriş gerektirmez: link başka cihazda (ör. telefonda)
    açılabilir; token kimliği zaten kanıtlar.
    """
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, ValidationError, User.DoesNotExist):
        user = None

    if user is not None and user.is_verified:
        messages.info(request, "E-posta adresin zaten doğrulanmış.")
    elif user is not None and email_verification_token.check_token(user, token):
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        messages.success(request, "E-posta adresin doğrulandı. Teşekkürler!")
    else:
        messages.error(request, INVALID_LINK_MESSAGE)
    return redirect("pages:home")


@login_required
@require_POST
@ratelimit(key="user", rate="3/h", block=False)
def resend_verification_view(request):
    """Uyarı bandındaki "Tekrar gönder" butonu. Kullanıcıyı geldiği sayfaya döndürür."""
    geri = safe_redirect_url(request, request.META.get("HTTP_REFERER"))

    if getattr(request, "limited", False):
        # OTP_ABUSE etiketi "doğrulama kötüye kullanımı" olarak kullanılıyor;
        # ayrı bir seçenek migration gerektirirdi.
        _log_rate_limited(request)
        messages.warning(request, "Kısa sürede çok fazla istek gönderdin. Lütfen 1 saat sonra tekrar dene.")
        return redirect(geri)

    if request.user.is_verified:
        messages.info(request, "E-posta adresin zaten doğrulanmış.")
        return redirect(geri)

    try:
        send_verification_email(request, request.user)
    except Exception:
        logger.exception("Doğrulama maili yeniden gönderilemedi (user_id=%s)", request.user.pk)
        messages.error(request, "Doğrulama maili şu an gönderilemedi. Lütfen biraz sonra tekrar dene.")
        return redirect(geri)

    messages.success(
        request,
        f"Doğrulama linkini {request.user.email} adresine gönderdik. Spam klasörünü de kontrol et.",
    )
    return redirect(geri)
