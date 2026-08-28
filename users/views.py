from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from core.http import get_client_ip
from dashboard.models import Announcement, SecurityLog
from jams.models import JamApplication

from .forms import UserLoginForm, UserProfileUpdateForm, UserRegisterForm

User = get_user_model()

class UserRegisterView(TemplateView):
    """
    Kayıt sayfasını render eder. Sayfadaki form, JS ile OTP'li API akışına
    (users:api_register + users:api_verify) gönderim yapar.

    GÜVENLİK: Bu view POST kabul ETMEZ. Eski CreateView halinde doğrudan
    form POST'u, OTP doğrulaması olmadan kullanıcı oluşturup login ediyordu
    (e-posta doğrulama bypass'ı). TemplateView POST'a otomatik olarak
    405 Method Not Allowed döndürür.
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

@method_decorator(ratelimit(key='ip', rate='5/5m', block=False), name='post')
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
