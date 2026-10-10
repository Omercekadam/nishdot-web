# Yılan Oyunu + İsteğe Bağlı E-posta Doğrulaması — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Üyelikte e-posta doğrulamasını zorunluluktan çıkarmak (anında giriş + 3 gün geçerli link + hatırlatma bandı) ve ana sayfaya liderlik tablolu bir yılan oyunu eklemek.

**Architecture:** Parça A `users` uygulamasında kalır: OTP akışı silinir, yerine `PasswordResetTokenGenerator` tabanlı bir doğrulama linki gelir; uyarı bandı ve genel mesaj bileşeni `base.html`'e eklenir. Parça B yeni `arcade` uygulamasıdır: istemcide oynanan oyun skorunu imzalı tek kullanımlık bir biletle gönderir, sunucu hafif korkuluklarla kaydeder. Yarışma penceresi ve aç/kapa anahtarı admin'deki `Competition` kaydıdır.

**Tech Stack:** Django 6.0.6, Python 3.12, django-ratelimit 4.1, Tailwind 3.4 (derlenmiş `output.css` commit'lenir), kütüphanesiz JS (canvas).

**Spec:** `docs/superpowers/specs/2026-10-05-yilan-oyunu-ve-istege-bagli-dogrulama-design.md`

## Global Constraints

- Dal: `oyun-ve-dogrulama`. `main`'e dokunulmaz; yedek etiketi `yedek/stand-oncesi` → `24d4142`.
- **Push yapılmaz** — push'u kullanıcı yapar. Sadece commit.
- Commit mesajları ASCII Türkçe, repo stilinde (ör. `Dogrulama tokeni ekle`). **`Co-Authored-By` satırı eklenmez** (kullanıcı kuralı: "contributorda claude olarak gözükme").
- Yeni bağımlılık eklenmez.
- **KVKK metnine dokunulmaz.** Oyun bölümündeki bildirim metni birebir: `Skorunu kaydettiğinde adın ve soyadının baş harfi tabloda herkese açık görünür.`
- `CustomUser.verification_code` ve `code_expires_at` alanları **silinmez** (yedek etikete dönüş şema uyumlu kalsın). `users` uygulamasında migration oluşmamalı.
- Yeni Tailwind sınıfı eklenen her görevden sonra `npm run build:css`; `static/css/output.css` commit'lenir (sunucuda npm yok).
- `MAX_SCORE = 397` (20×20 ızgara, başlangıç uzunluğu 3). `snake.js`'teki `GRID`/`START_LEN` ile birlikte değişir.
- Oyun hız sınırı `1200/h`, `key='user_or_ip'`. Doğrulama maili tekrar gönderimi `3/h`, `key='user'`.
- Test komutları (Git Bash, repo kökünden):
  ```bash
  export DJANGO_SETTINGS_MODULE=nishdot.settings.development
  venv/Scripts/python.exe manage.py test <etiket> -v 2
  ```
- Test kuralları: hız sınırı durumu cache'te tutulur → hız sınırına dokunan her test sınıfının `setUp`'ında `cache.clear()`. Hız sınırını test etmeyen API testleri `@override_settings(RATELIMIT_ENABLE=False)`.

---

## Dosya Haritası

| Dosya | Durum | Sorumluluk |
|---|---|---|
| `core/http.py` | değişir | `safe_redirect_url()` — açık yönlendirmeye karşı `next`/Referer süzgeci |
| `nishdot/settings/base.py` | değişir | `EMAIL_TIMEOUT`, `arcade` uygulaması, context processor |
| `users/tokens.py` | yeni | `email_verification_token` |
| `users/verification.py` | yeni | Doğrulama linki üretimi ve maili |
| `users/api.py` | yeniden yazılır | Kayıt: anında giriş + mail; OTP uçları silinir |
| `users/views.py` | değişir | `verify_email_view`, `resend_verification_view` |
| `users/forms.py` | değişir | Doğrulanmamış girişi reddeden kontrol silinir |
| `users/urls.py` | değişir | OTP rotaları çıkar, doğrulama rotaları girer |
| `templates/emails/verify_email{.html,.txt,_subject.txt}` | yeni | Doğrulama maili |
| `templates/emails/otp_verification.html` | silinir | |
| `templates/components/verify_banner.html` | yeni | "E-postanı doğrula" bandı |
| `templates/components/messages.html` | yeni | Genel Django mesajları |
| `templates/base.html` | değişir | Bant + mesajlar navbar'ın altına |
| `templates/users/register.html` | yeniden yazılır | OTP adımı yok, `next` taşınır |
| `templates/users/login.html`, `templates/users/dashboard.html` | değişir | Yerel mesaj döngüleri çıkar, `next` taşınır |
| `dashboard/models.py` | değişir | `SecurityLog.ActionType.GAME_SPAM` |
| `arcade/` | yeni uygulama | models, services, views, urls, signals, admin, context_processors, tests |
| `templates/arcade/_section.html`, `_row.html` | yeni | Ana sayfa oyun bölümü, tablo satırı |
| `templates/pages/home.html`, `templates/components/navbar.html`, `pages/views.py` | değişir | Bölümün yerleşimi |
| `static/js/snake.js` | yeni | Oyun |
| `pages/management/commands/purge_expired_data.py` | değişir | 3. adım: eski oyun skorları |
| `README.md`, `docs/ARCHITECTURE.md` | değişir | OTP anlatımı → link; `arcade` |

---

# PARÇA A — İsteğe bağlı e-posta doğrulaması

### Task 1: Güvenli yönlendirme yardımcısı, doğrulama tokenı, SMTP zaman aşımı

**Files:**
- Modify: `core/http.py`
- Create: `users/tokens.py`
- Modify: `nishdot/settings/base.py` (E-MAIL bölümü)
- Test: `core/tests.py`, `users/tests.py`

**Interfaces:**
- Produces: `core.http.safe_redirect_url(request, url, fallback="/") -> str`; `users.tokens.email_verification_token` (`make_token(user)`, `check_token(user, token)`).

- [ ] **Step 1: Başarısız testleri yaz**

`core/tests.py` en üstteki import'lara ekle:

```python
from django.test import RequestFactory

from core.http import safe_redirect_url
```

Dosyanın sonuna ekle:

```python
class SafeRedirectUrlTests(TestCase):
    """next / Referer yalnızca site içini gösteriyorsa kullanılmalı (open redirect)."""

    def setUp(self):
        self.request = RequestFactory().get("/")

    def test_internal_path_allowed(self):
        self.assertEqual(safe_redirect_url(self.request, "/#oyun"), "/#oyun")

    def test_external_url_rejected(self):
        self.assertEqual(safe_redirect_url(self.request, "https://kotu.example.com/"), "/")

    def test_scheme_relative_url_rejected(self):
        self.assertEqual(safe_redirect_url(self.request, "//kotu.example.com"), "/")

    def test_empty_or_non_string_falls_back(self):
        self.assertEqual(safe_redirect_url(self.request, None), "/")
        self.assertEqual(safe_redirect_url(self.request, ""), "/")
        self.assertEqual(safe_redirect_url(self.request, 42), "/")
```

`users/tests.py` en üstteki import'lara ekle:

```python
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone

from users.tokens import email_verification_token
```

Dosyanın sonuna ekle:

```python
class EmailVerificationTokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="t@example.com", email="t@example.com",
            password="SuperGizli123", is_verified=False,
        )

    def test_token_survives_login(self):
        """Kayıt token'ı üretip hemen login() çağırıyor; last_login değişince link ölmemeli."""
        token = email_verification_token.make_token(self.user)
        self.user.last_login = timezone.now()
        self.user.save(update_fields=["last_login"])
        self.assertTrue(email_verification_token.check_token(self.user, token))

    def test_token_dies_after_verification(self):
        token = email_verification_token.make_token(self.user)
        self.user.is_verified = True
        self.assertFalse(email_verification_token.check_token(self.user, token))

    def test_token_dies_after_email_change(self):
        token = email_verification_token.make_token(self.user)
        self.user.email = "baska@example.com"
        self.assertFalse(email_verification_token.check_token(self.user, token))

    def test_password_reset_token_not_accepted(self):
        token = default_token_generator.make_token(self.user)
        self.assertFalse(email_verification_token.check_token(self.user, token))
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test core.tests.SafeRedirectUrlTests users.tests.EmailVerificationTokenTests -v 2`
Expected: `ImportError` (`safe_redirect_url`, `users.tokens` yok).

- [ ] **Step 3: Uygula**

`core/http.py` — import'ların altına:

```python
from django.utils.http import url_has_allowed_host_and_scheme
```

Dosyanın sonuna:

```python
def safe_redirect_url(request, url, fallback="/"):
    """
    Kullanıcıdan gelen yönlendirme adresini (next, Referer) yalnızca bu sitenin
    içini gösteriyorsa döndürür; değilse fallback.

    Açık yönlendirme (open redirect) açığını kapatır: ?next=https://kotu-site.com
    ile gelen biri kayıttan sonra dışarı gönderilmez.
    """
    if isinstance(url, str) and url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return fallback
```

`users/tokens.py` (yeni):

```python
"""
E-posta Doğrulama Tokenı
=========================

Şifre sıfırlama token'ıyla aynı altyapı (HMAC + zaman damgası, veritabanına
yazılmaz) — farklı hash girdisi ve farklı tuzla.

Neden last_login ve parola hash'i YOK?
    Varsayılan PasswordResetTokenGenerator ikisini de hash'e katar. Kayıt akışı
    token'ı üretir üretmez login() çağırıyor ve login() last_login'i
    güncelliyor; dahil etseydik her link doğar doğmaz geçersiz olurdu.

    - is_verified hash'te → link bir kez kullanılınca ölür.
    - email hash'te       → adres değişirse eski link ölür.
    - Süre: PASSWORD_RESET_TIMEOUT (Django varsayılanı 3 gün).
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    # Farklı tuz: şifre sıfırlama token'ı doğrulama linkinde (ya da tersi) geçmez.
    key_salt = "users.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.is_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()
```

`nishdot/settings/base.py` — `DEFAULT_FROM_EMAIL = ...` satırının hemen altına:

```python

# SMTP sunucusu yanıt vermezse istek asılı kalmasın: 10 sn sonra hata fırlatılır.
# Kayıt akışı bu hatayı loglayıp yine başarılı döner (bkz. users/api.py).
EMAIL_TIMEOUT = 10
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `venv/Scripts/python.exe manage.py test core.tests.SafeRedirectUrlTests users.tests.EmailVerificationTokenTests -v 2`
Expected: 8 test, OK.

- [ ] **Step 5: Commit**

```bash
git add core/http.py core/tests.py users/tokens.py users/tests.py nishdot/settings/base.py
git commit -m "Dogrulama tokeni, guvenli yonlendirme yardimcisi ve SMTP zaman asimi"
```

---

### Task 2: Doğrulama maili, doğrulama linki ve "tekrar gönder" ucu

**Files:**
- Create: `users/verification.py`
- Create: `templates/emails/verify_email.html`, `templates/emails/verify_email.txt`, `templates/emails/verify_email_subject.txt`
- Modify: `users/views.py`, `users/urls.py`
- Test: `users/tests.py`

**Interfaces:**
- Consumes: `email_verification_token`, `safe_redirect_url` (Task 1); `users.api._log_rate_limited(request, action=None)` (mevcut).
- Produces: `users.verification.send_verification_email(request, user)` (hata fırlatabilir); `users.views.INVALID_LINK_MESSAGE`; URL adları `users:verify_email` (`/auth/dogrula/<uidb64>/<token>/`) ve `users:resend_verification` (`/auth/dogrulama-gonder/`).

- [ ] **Step 1: Başarısız testleri yaz**

`users/tests.py` import'larına ekle:

```python
from django.contrib.messages import get_messages
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from dashboard.models import SecurityLog
from users.views import INVALID_LINK_MESSAGE
```

Dosyanın sonuna ekle:

```python
def _verify_url(user, token=None):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    return reverse("users:verify_email", args=[uidb64, token or email_verification_token.make_token(user)])


def _messages(resp):
    return [str(m) for m in get_messages(resp.wsgi_request)]


class VerifyEmailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="v@example.com", email="v@example.com",
            password="SuperGizli123", is_verified=False,
        )

    def test_valid_link_verifies_without_login(self):
        """Link başka cihazda açılabilir; giriş gerekmez."""
        resp = self.client.get(_verify_url(self.user))
        self.assertRedirects(resp, "/", fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_second_click_says_already_verified(self):
        url = _verify_url(self.user)
        self.client.get(url)
        resp = self.client.get(url)
        self.assertIn("E-posta adresin zaten doğrulanmış.", _messages(resp))

    def test_bad_token_rejected(self):
        resp = self.client.get(_verify_url(self.user, token="bozuk-token"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)
        self.assertIn(INVALID_LINK_MESSAGE, _messages(resp))

    def test_bad_uid_rejected(self):
        resp = self.client.get(reverse("users:verify_email", args=["zzzz", "bozuk-token"]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(INVALID_LINK_MESSAGE, _messages(resp))


class ResendVerificationTests(TestCase):
    def setUp(self):
        cache.clear()  # hız sınırı sayaçları testler arası sızmasın
        self.user = User.objects.create_user(
            username="r@example.com", email="r@example.com",
            password="SuperGizli123", is_verified=False,
        )
        self.url = reverse("users:resend_verification")

    def test_requires_login(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("users:login"), resp["Location"])
        self.assertEqual(len(mail.outbox), 0)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_sends_link_and_returns_to_page(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.url, HTTP_REFERER="http://testserver/events/")
        self.assertRedirects(resp, "http://testserver/events/", fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["r@example.com"])
        self.assertIn("/auth/dogrula/", mail.outbox[0].body)

    def test_external_referer_falls_back_home(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.url, HTTP_REFERER="https://kotu.example.com/")
        self.assertRedirects(resp, "/", fetch_redirect_response=False)

    def test_verified_user_gets_no_mail(self):
        self.user.is_verified = True
        self.user.save()
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.assertEqual(len(mail.outbox), 0)

    def test_fourth_request_limited_and_logged(self):
        self.client.force_login(self.user)
        for _ in range(4):
            self.client.post(self.url)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(SecurityLog.objects.count(), 1)
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test users.tests.VerifyEmailViewTests users.tests.ResendVerificationTests -v 2`
Expected: `ImportError: cannot import name 'INVALID_LINK_MESSAGE'`.

- [ ] **Step 3: Mail şablonlarını yaz**

`templates/emails/verify_email_subject.txt`:

```
Nishdot - E-posta adresini doğrula
```

`templates/emails/verify_email.txt`:

```
{% autoescape off %}Merhaba {{ first_name }},

Nishdot'a hoş geldin! Hesabın hazır, hemen kullanabilirsin.
E-posta adresini doğrulamak için şu linke tıkla:

{{ verify_url }}

Link 3 gün geçerlidir. Doğrulama, sana ulaşmamız gerektiğinde
(ör. ödül kazanırsan) e-postanın doğru olduğundan emin olmamız içindir.

Bu maili spam klasöründe bulduysan "Spam değil" olarak işaretle;
sonraki maillerimiz gelen kutuna düşer.

Bu hesabı sen açmadıysan bu mesajı görmezden gelebilirsin.

İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü
{% endautoescape %}
```

`templates/emails/verify_email.html` (düzen `otp_verification.html`'den; buton satır içi stil — bazı istemciler `<style>`'ı atar):

```html
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Nishdot E-posta Doğrulama</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f5; margin: 0; padding: 0; color: #27272a; }
        .container { max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); }
        .header { background-color: #18181b; padding: 30px; text-align: center; border-bottom: 4px solid #EB596D; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 1px; }
        .content { padding: 40px 30px; text-align: center; }
        .greeting { font-size: 20px; font-weight: 600; margin-bottom: 20px; }
        .message { font-size: 16px; line-height: 1.5; color: #52525b; margin-bottom: 30px; }
        .fallback { font-size: 12px; color: #a1a1aa; margin: 24px 0; word-break: break-all; }
        .fallback a { color: #EB596D; }
        .warning { font-size: 14px; line-height: 1.6; color: #71717a; }
        .footer { background-color: #f4f4f5; padding: 20px; text-align: center; font-size: 12px; color: #a1a1aa; border-top: 1px solid #e4e4e7; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NISHDOT</h1>
        </div>
        <div class="content">
            <div class="greeting">Merhaba {{ first_name }},</div>
            <div class="message">
                Nishdot'a hoş geldin! Hesabın hazır, hemen kullanabilirsin.
                E-posta adresini doğrulamak için aşağıdaki butona tıkla.
            </div>
            <a href="{{ verify_url }}" style="display:inline-block;background-color:#EB596D;color:#ffffff;text-decoration:none;font-weight:600;font-size:16px;padding:14px 32px;border-radius:8px;">E-postamı doğrula</a>
            <div class="fallback">
                Buton çalışmazsa bu adresi tarayıcına yapıştır:<br>
                <a href="{{ verify_url }}">{{ verify_url }}</a>
            </div>
            <div class="warning">
                Link <strong>3 gün</strong> boyunca geçerlidir.<br>
                Bu maili spam klasöründe bulduysan "Spam değil" olarak işaretle; sonraki maillerimiz gelen kutuna düşer.<br>
                Bu hesabı sen açmadıysan bu mesajı görmezden gelebilirsin.
            </div>
        </div>
        <div class="footer">
            &copy; 2026 İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü
        </div>
    </div>
</body>
</html>
```

- [ ] **Step 4: Gönderim modülünü yaz**

`users/verification.py` (yeni):

```python
"""
E-posta Doğrulama Maili
========================

Doğrulama zorunlu değildir — hiçbir işlemi kilitlemez, yalnızca uyarı bandı
gösterilir. Link 3 gün geçerlidir: mail geç gelse ya da spam'e düşse de çalışır.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def build_verification_url(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    return request.build_absolute_uri(reverse("users:verify_email", args=[uidb64, token]))


def send_verification_email(request, user):
    """Doğrulama linkini gönderir. Başarısızlıkta exception fırlatır (çağıran karar verir)."""
    context = {
        "first_name": user.first_name,
        "verify_url": build_verification_url(request, user),
    }
    subject = render_to_string("emails/verify_email_subject.txt").strip()
    text_body = render_to_string("emails/verify_email.txt", context)
    html_body = render_to_string("emails/verify_email.html", context)

    msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
```

- [ ] **Step 5: Görünümleri yaz**

`users/views.py` — import bloğunu şununla değiştir:

```python
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
```

Dosyanın sonuna ekle:

```python


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
```

`users/urls.py` — `# API Endpoints` satırının hemen üstüne:

```python
    # E-posta doğrulama (isteğe bağlı; hiçbir işlemi kilitlemez)
    path("dogrula/<uidb64>/<token>/", views.verify_email_view, name="verify_email"),
    path("dogrulama-gonder/", views.resend_verification_view, name="resend_verification"),

```

- [ ] **Step 6: Testlerin geçtiğini gör**

Run: `venv/Scripts/python.exe manage.py test users -v 2`
Expected: tümü OK (eski OTP testleri hâlâ geçer; Task 3'te silinecek).

- [ ] **Step 7: Commit**

```bash
git add users/verification.py users/views.py users/urls.py users/tests.py templates/emails/verify_email.html templates/emails/verify_email.txt templates/emails/verify_email_subject.txt
git commit -m "E-posta dogrulama linki ve tekrar gonder ucu"
```

---

### Task 3: Kayıt akışı — anında giriş, OTP'nin kaldırılması

**Files:**
- Modify (yeniden yaz): `users/api.py`, `templates/users/register.html`
- Modify: `users/forms.py:100-106`, `users/urls.py`, `users/views.py` (`UserRegisterView` docstring), `templates/users/login.html`
- Delete: `templates/emails/otp_verification.html`
- Test: `users/tests.py` (`OtpApiTests` silinir, yerine `RegisterApiTests`, `LoginTests`, `RegisterPageTests`)

**Interfaces:**
- Consumes: `send_verification_email` (Task 2), `safe_redirect_url` (Task 1).
- Produces: `POST /auth/api/register/` gövdesi `{email, password, first_name, last_name, next?}` → `200 {"success": true, "redirect": "<güvenli adres>"}`; oturum açık döner. `users.api._log_rate_limited` korunur.

- [ ] **Step 1: Testleri değiştir**

`users/tests.py` import'larına ekle:

```python
import re
from unittest import mock
```

`class OtpApiTests(TestCase):` sınıfını (üstündeki `@override_settings(RATELIMIT_ENABLE=False)` dahil) tamamen sil ve yerine şunu koy:

```python
@override_settings(RATELIMIT_ENABLE=False)
class RegisterApiTests(TestCase):
    def setUp(self):
        cache.clear()

    def _register(self, email="yeni@example.com", next_url=None):
        govde = {"email": email, "password": "SuperGizli123", "first_name": "Yeni", "last_name": "Uye"}
        if next_url is not None:
            govde["next"] = next_url
        return self.client.post(
            reverse("users:api_register"), data=json.dumps(govde), content_type="application/json",
        )

    def test_register_logs_in_unverified_user(self):
        resp = self._register()
        self.assertEqual(resp.status_code, 200)
        user = User.objects.get(email="yeni@example.com")
        self.assertFalse(user.is_verified)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_register_sends_verification_link(self):
        self._register()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["yeni@example.com"])
        self.assertIn("/auth/dogrula/", mail.outbox[0].body)

    def test_mailed_link_verifies_account(self):
        """Uçtan uca: login()'den SONRA da maildeki link çalışmalı."""
        self._register()
        yol = re.search(r"/auth/dogrula/[\w-]+/[\w-]+/", mail.outbox[0].body).group(0)
        self.client.get(yol)
        self.assertTrue(User.objects.get(email="yeni@example.com").is_verified)

    def test_register_succeeds_when_mail_fails(self):
        with mock.patch("users.api.send_verification_email", side_effect=OSError("SMTP kapalı")):
            with self.assertLogs("users.api", level="ERROR"):
                resp = self._register()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_returns_safe_next(self):
        self.assertEqual(self._register(next_url="/#oyun").json()["redirect"], "/#oyun")

    def test_register_rejects_external_next(self):
        self.assertEqual(self._register(next_url="https://kotu.example.com/").json()["redirect"], "/")

    def test_register_without_next_goes_home(self):
        self.assertEqual(self._register().json()["redirect"], "/")

    def test_duplicate_email_rejected(self):
        self._register()
        self.assertEqual(self._register().status_code, 400)

    def test_old_otp_endpoints_removed(self):
        self.assertEqual(self.client.post("/auth/api/verify/").status_code, 404)
        self.assertEqual(self.client.post("/auth/api/resend-otp/").status_code, 404)


@override_settings(RATELIMIT_ENABLE=False)
class LoginTests(TestCase):
    def setUp(self):
        User.objects.create_user(
            username="u@example.com", email="u@example.com",
            password="SuperGizli123", is_verified=False,
        )

    def test_unverified_user_can_log_in(self):
        resp = self.client.post(reverse("users:login"), {"username": "u@example.com", "password": "SuperGizli123"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_returns_to_next(self):
        resp = self.client.post(
            reverse("users:login") + "?next=/%23oyun",
            {"username": "u@example.com", "password": "SuperGizli123"},
        )
        self.assertEqual(resp["Location"], "/#oyun")

    def test_register_link_keeps_next(self):
        resp = self.client.get(reverse("users:login") + "?next=/%23oyun")
        self.assertContains(resp, reverse("users:register") + "?next=/%23oyun")


class RegisterPageTests(TestCase):
    def test_page_has_no_otp_step_and_keeps_next(self):
        resp = self.client.get(reverse("users:register") + "?next=/%23oyun")
        self.assertNotContains(resp, "verify-section")
        self.assertContains(resp, 'name="next" value="/#oyun"')
        self.assertContains(resp, reverse("users:login") + "?next=/%23oyun")
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test users.tests.RegisterApiTests users.tests.LoginTests users.tests.RegisterPageTests -v 2`
Expected: FAIL — oturum açılmıyor, `redirect` anahtarı yok, doğrulanmamış giriş reddediliyor, OTP uçları 200/400 dönüyor.

- [ ] **Step 3: `users/api.py`'yi yeniden yaz** (dosyanın tamamı)

```python
"""
Kullanıcı Kayıt API'si
=======================

Akış: register → kullanıcı oluştur → anında oturum aç → doğrulama linkini maille.
E-posta doğrulaması hiçbir işlemi kilitlemez; doğrulanmamış hesap yalnızca
hatırlatma bandını görür (templates/components/verify_banner.html).

Mail gönderilemezse kayıt yine başarılıdır: hata loglanır, kullanıcı banttaki
"Tekrar gönder" ile yeni link ister. (Eskiden 15 dk'lık OTP kodu vardı; mail
geç gelince ya da spam'e düşünce kişi hesabına hiç giremiyordu.)
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from core.http import get_client_ip, safe_redirect_url
from dashboard.models import SecurityLog

from .verification import send_verification_email

logger = logging.getLogger(__name__)

User = get_user_model()


def _log_rate_limited(request, action=None):
    SecurityLog.objects.create(
        ip_address=get_client_ip(request),
        action=action or SecurityLog.ActionType.OTP_ABUSE,
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )


@ratelimit(key='ip', rate='3/h', block=False)
@require_POST
def register_api_view(request):
    if getattr(request, 'limited', False):
        _log_rate_limited(request, SecurityLog.ActionType.REGISTER_SPAM)
        return JsonResponse(
            {'error': 'Kısa sürede çok fazla istek gönderdiniz. Lütfen 1 saat sonra tekrar deneyiniz.'},
            status=429,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON verisi.'}, status=400)

    if not all([data.get('email'), data.get('password'), data.get('first_name'), data.get('last_name')]):
        return JsonResponse({'error': 'Eksik bilgi girdiniz.'}, status=400)

    email = data['email'].strip().lower()

    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Bu e-posta adresi zaten kullanılıyor.'}, status=400)

    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            is_verified=False,
        )
    except Exception:
        logger.exception("Kayıt sırasında kullanıcı oluşturulamadı (email=%s)", email)
        return JsonResponse({'error': 'Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.'}, status=500)

    # Tek kimlik doğrulama backend'i (ModelBackend) olduğu için backend argümanı gerekmez.
    # login(), oturumdaki veriyi korur: üye olmadan oynanan oyun skorları
    # (arcade) bu sayede yeni hesaba bağlanır.
    login(request, user)
    messages.success(request, f"Hoş geldin {user.first_name}! Hesabın oluşturuldu.")

    try:
        send_verification_email(request, user)
    except Exception:
        # Kayıt başarısız sayılmaz: kullanıcı uyarı bandından yeni link isteyebilir.
        logger.exception("Doğrulama maili gönderilemedi (email=%s)", email)

    return JsonResponse({
        'success': True,
        'redirect': safe_redirect_url(request, data.get('next')),
    })
```

- [ ] **Step 4: Rotaları, giriş formunu ve docstring'i güncelle**

`users/urls.py` — şu iki satırı sil:

```python
    path("api/verify/", api.verify_otp_api_view, name="api_verify"),
    path("api/resend-otp/", api.resend_otp_api_view, name="api_resend_otp"),
```

`users/forms.py` — `UserLoginForm.clean` içindeki şu bloğu:

```python
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                if not getattr(self.user_cache, 'is_verified', True):
                    raise forms.ValidationError("Lütfen önce e-posta adresinizi doğrulayın.")
                self.confirm_login_allowed(self.user_cache)
```

şununla değiştir:

```python
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            # E-posta doğrulaması girişi engellemez; doğrulanmamış hesap
            # yalnızca uyarı bandını görür (bkz. components/verify_banner.html).
            self.confirm_login_allowed(self.user_cache)
```

`users/views.py` — `UserRegisterView` docstring'ini şununla değiştir:

```python
    """
    Kayıt sayfasını render eder. Sayfadaki form JS ile users:api_register'a
    gönderim yapar; API kullanıcıyı oluşturur, oturumu açar ve doğrulama
    linkini mailler.

    GÜVENLİK: Bu view POST kabul ETMEZ (TemplateView POST'a 405 döner).
    Tek kayıt yolu, hız sınırlı API'dir.
    """
```

- [ ] **Step 5: `templates/users/register.html`'i yeniden yaz** (dosyanın tamamı)

```html
{% extends 'base.html' %}
{% block title %}Kayıt Ol | Nishdot{% endblock %}

{% block content %}
<div class="min-h-[calc(100vh-80px)] bg-zinc-900 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
    <!-- Neon Glow Background -->
    <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-pink/10 rounded-full blur-[120px] pointer-events-none"></div>

    <div class="max-w-md w-full space-y-8 relative bg-zinc-800/30 p-10 rounded-2xl border border-white/5 shadow-[0_8px_30px_rgb(0,0,0,0.8)] backdrop-blur-md">
        <div>
            <h2 class="mt-2 text-center text-3xl font-extrabold text-white">
                Hesap Oluştur
            </h2>
            <p class="mt-4 text-center text-sm text-zinc-400">
                Zaten hesabın var mı?
                <a href="{% url 'users:login' %}{% if request.GET.next %}?next={{ request.GET.next|urlencode }}{% endif %}" class="font-medium text-brand-pink hover:text-brand-pink/80 transition-colors">
                    Giriş yap
                </a>
            </p>
        </div>

        <form id="register-form" class="mt-8 space-y-4">
            {% csrf_token %}
            <!-- Kayıttan sonra dönülecek adres (ör. oyun bölümü). Sunucu yalnızca site içi adresleri kabul eder. -->
            <input type="hidden" name="next" value="{{ request.GET.next }}">

            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label for="{{ form.first_name.id_for_label }}" class="block text-sm font-medium text-zinc-300 mb-2">Ad</label>
                    {{ form.first_name }}
                </div>
                <div>
                    <label for="{{ form.last_name.id_for_label }}" class="block text-sm font-medium text-zinc-300 mb-2">Soyad</label>
                    {{ form.last_name }}
                </div>
            </div>

            <div>
                <label for="{{ form.email.id_for_label }}" class="block text-sm font-medium text-zinc-300 mb-2">E-Posta Adresi</label>
                {{ form.email }}
            </div>

            <div>
                <label for="{{ form.password.id_for_label }}" class="block text-sm font-medium text-zinc-300 mb-2">Şifre</label>
                {{ form.password }}
            </div>

            <div>
                <label for="{{ form.password_confirm.id_for_label }}" class="block text-sm font-medium text-zinc-300 mb-2">Şifre Tekrar</label>
                {{ form.password_confirm }}
            </div>

            <div id="register-error" class="hidden text-red-400 text-sm p-3 bg-red-500/10 rounded-lg border border-red-500/30"></div>

            <div class="pt-4">
                <button type="submit" id="btn-register" class="w-full btn-primary py-3 flex justify-center shadow-[0_0_20px_rgba(235,89,109,0.3)] hover:shadow-[0_0_35px_rgba(235,89,109,0.6)]">
                    Kayıt Ol
                </button>
            </div>
        </form>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('register-form');

    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const btnRegister = document.getElementById('btn-register');
        const errorBox = document.getElementById('register-error');
        errorBox.classList.add('hidden');

        const data = Object.fromEntries(new FormData(registerForm).entries());

        // Şifre eşleşme kontrolü (basit frontend validasyonu)
        if (data.password !== data.password_confirm) {
            errorBox.textContent = "Şifreler uyuşmuyor.";
            errorBox.classList.remove('hidden');
            return;
        }

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        let redirecting = false;

        btnRegister.disabled = true;
        btnRegister.innerHTML = 'İşleniyor...';

        try {
            const response = await fetch('{% url "users:api_register" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (response.ok) {
                // Oturum sunucuda açıldı; doğrulama linki mailde, hatırlatma bandı sitede.
                redirecting = true;
                btnRegister.innerHTML = 'Hesabın hazır! Yönlendiriliyor...';
                window.location.href = result.redirect || '/';
            } else {
                errorBox.textContent = result.error || "Kayıt olurken bir hata oluştu.";
                errorBox.classList.remove('hidden');
            }
        } catch (error) {
            errorBox.textContent = "Bağlantı hatası: " + error.message;
            errorBox.classList.remove('hidden');
        } finally {
            if (!redirecting) {
                btnRegister.disabled = false;
                btnRegister.innerHTML = 'Kayıt Ol';
            }
        }
    });
});
</script>
{% endblock %}
```

- [ ] **Step 6: `templates/users/login.html` — kayıt linki `next`'i taşısın, eski `verified` bloğu gitsin**

Şunu:

```html
                <a href="{% url 'users:register' %}" class="font-medium text-brand-pink hover:text-brand-pink/80 transition-colors">
```

şununla değiştir:

```html
                <a href="{% url 'users:register' %}{% if request.GET.next %}?next={{ request.GET.next|urlencode }}{% endif %}" class="font-medium text-brand-pink hover:text-brand-pink/80 transition-colors">
```

Şu bloğu tamamen sil (artık kimse `?verified=true` ile gelmiyor):

```html
        {% if request.GET.verified == 'true' %}
        <div class="p-4 rounded-xl text-sm font-medium bg-green-500/10 text-green-400 border border-green-500/50 mb-4">
            Doğrulama başarılı! Şimdi giriş yapabilirsiniz.
        </div>
        {% endif %}
```

(Yerel `{% if messages %}` döngüsü Task 4'te genel bileşen gelince silinir.)

- [ ] **Step 7: Kullanılmayan OTP mail şablonunu sil**

```bash
git rm templates/emails/otp_verification.html
```

- [ ] **Step 8: Testlerin geçtiğini gör + artık referans kalmadığını doğrula**

Run: `venv/Scripts/python.exe manage.py test users -v 2`
Expected: tümü OK.

Run: `grep -rn "api_verify\|api_resend_otp\|send_otp_email\|_generate_otp\|otp_verification" --include=*.py --include=*.html users templates`
Expected: çıktı yok.

Run: `venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
Expected: `No changes detected` (OTP alanları modelde duruyor).

- [ ] **Step 9: Commit**

```bash
git add users/api.py users/forms.py users/urls.py users/views.py users/tests.py templates/users/register.html templates/users/login.html
git commit -m "Kayitta aninda giris; OTP akisi kaldirildi, dogrulama linke tasindi"
```

---

### Task 4: Genel mesaj bileşeni ve doğrulama uyarı bandı

**Files:**
- Create: `templates/components/messages.html`, `templates/components/verify_banner.html`
- Modify: `templates/base.html`, `templates/users/login.html`, `templates/users/dashboard.html`
- Modify: `static/css/output.css` (derleme)
- Test: `users/tests.py`

**Interfaces:**
- Consumes: `users:resend_verification` (Task 2), `INVALID_LINK_MESSAGE` (Task 2).
- Produces: Her sayfada navbar altında `data-verify-banner` (yalnızca doğrulanmamış girişli kullanıcıda) ve mesaj şeritleri.

- [ ] **Step 1: Başarısız testleri yaz** (`users/tests.py` sonuna)

```python
class VerifyBannerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="b@example.com", email="b@example.com",
            password="SuperGizli123", is_verified=False,
        )

    def test_shown_to_unverified_user(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("pages:home"))
        self.assertContains(resp, "data-verify-banner")
        self.assertContains(resp, reverse("users:resend_verification"))

    def test_hidden_for_verified_user(self):
        self.user.is_verified = True
        self.user.save()
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(reverse("pages:home")), "data-verify-banner")

    def test_hidden_for_anonymous(self):
        self.assertNotContains(self.client.get(reverse("pages:home")), "data-verify-banner")


class GlobalMessagesTests(TestCase):
    def test_message_rendered_once_on_login_page(self):
        """Yerel döngü + genel bileşen çift gösterim yapmamalı."""
        self.client.get(reverse("users:verify_email", args=["zzzz", "bozuk-token"]))
        resp = self.client.get(reverse("users:login"))
        self.assertContains(resp, INVALID_LINK_MESSAGE, count=1)

    def test_message_rendered_on_home(self):
        resp = self.client.get(reverse("users:verify_email", args=["zzzz", "bozuk-token"]), follow=True)
        self.assertContains(resp, INVALID_LINK_MESSAGE, count=1)
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test users.tests.VerifyBannerTests users.tests.GlobalMessagesTests -v 2`
Expected: bant testleri FAIL; `test_message_rendered_on_home` FAIL (ana sayfa mesaj göstermiyor).

- [ ] **Step 3: Bileşenleri yaz**

`templates/components/verify_banner.html`:

```html
{% if user.is_authenticated and not user.is_verified %}
<!-- E-posta doğrulama hatırlatması: hiçbir işlemi kilitlemez, kapatılamaz. -->
<div class="bg-amber-500/10 border-b border-amber-500/30" data-verify-banner>
    <div class="container-main py-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-sm text-amber-200">
        <p class="flex-1">
            E-posta adresini henüz doğrulamadın. Gelen kutunu ve spam klasörünü kontrol et.
        </p>
        <form action="{% url 'users:resend_verification' %}" method="post" class="shrink-0">
            {% csrf_token %}
            <button type="submit" class="font-semibold text-amber-100 underline decoration-amber-400/50 underline-offset-4 hover:decoration-amber-200 transition-colors">
                Tekrar gönder
            </button>
        </form>
    </div>
</div>
{% endif %}
```

`templates/components/messages.html`:

```html
{% if messages %}
<!-- Django mesajları — tüm sayfalarda tek yerden gösterilir. -->
<div class="container-main pt-4 space-y-2" role="status" aria-live="polite">
    {% for message in messages %}
    <div class="flex items-start justify-between gap-4 p-4 rounded-xl text-sm font-medium border
        {% if message.level == DEFAULT_MESSAGE_LEVELS.ERROR %}bg-red-500/10 text-red-400 border-red-500/50
        {% elif message.level == DEFAULT_MESSAGE_LEVELS.WARNING %}bg-amber-500/10 text-amber-300 border-amber-500/50
        {% elif message.level == DEFAULT_MESSAGE_LEVELS.SUCCESS %}bg-green-500/10 text-green-400 border-green-500/50
        {% else %}bg-sky-500/10 text-sky-300 border-sky-500/50{% endif %}" data-message>
        <span>{{ message }}</span>
        <button type="button" class="shrink-0 leading-none opacity-70 hover:opacity-100 transition-opacity" aria-label="Kapat" onclick="this.closest('[data-message]').remove()">&times;</button>
    </div>
    {% endfor %}
</div>
{% endif %}
```

- [ ] **Step 4: `base.html`'e yerleştir, yerel döngüleri sil**

`templates/base.html` — şunu:

```html
    {% include 'components/navbar.html' %}
```

şununla değiştir:

```html
    {% include 'components/navbar.html' %}
    {% include 'components/verify_banner.html' %}
    {% include 'components/messages.html' %}
```

`templates/users/login.html` ve `templates/users/dashboard.html` — ikisinde de şu bloğu tamamen sil:

```html
        {% if messages %}
            {% for message in messages %}
                <div class="p-4 rounded-xl text-sm font-medium {% if message.tags == 'error' %}bg-red-500/10 text-red-400 border border-red-500/50{% else %}bg-green-500/10 text-green-400 border border-green-500/50{% endif %}">
                    {{ message }}
                </div>
            {% endfor %}
        {% endif %}
```

Run: `grep -rn "for message in messages" templates`
Expected: yalnızca `templates/components/messages.html`.

- [ ] **Step 5: CSS'i derle** (yeni sınıflar: `sky-*`, `amber-*` varyantları)

Run: `npm run build:css`
Expected: `Done in ...ms`, `static/css/output.css` değişti.

- [ ] **Step 6: Tüm testler**

Run: `venv/Scripts/python.exe manage.py test -v 1`
Expected: OK.

- [ ] **Step 7: Commit**

```bash
git add templates/components/messages.html templates/components/verify_banner.html templates/base.html templates/users/login.html templates/users/dashboard.html static/css/output.css users/tests.py
git commit -m "Genel mesaj bileseni ve e-posta dogrulama uyari bandi"
```

---

### Task 5 (KARARA BAĞLI): Stand için kayıt/giriş hız sınırları

> Yalnızca kullanıcı onaylarsa uygulanır. Sorun: kayıt **IP başına saatte 3**, giriş **IP başına 5 dakikada 5** (başarılı girişler de sayılır). Standda ortak bir cihaz ya da kampüs Wi-Fi'ı (çoğu öğrenci aynı genel IP) kullanılırsa 4. kişi kayıt olamaz. Önerilen: kayıt `30/h`, giriş `30/5m`. 10+ karakterli parolada 30/5dk kaba kuvvete pratik bir kapı açmaz.

**Files:**
- Modify: `users/api.py` (`register_api_view` dekoratörü), `users/views.py` (`UserLoginView` dekoratörü)
- Test: `users/tests.py`

- [ ] **Step 1: Başarısız testleri yaz** (`users/tests.py` sonuna)

```python
class SharedIpRateLimitTests(TestCase):
    """Stand cihazı / kampüs NAT: aynı IP'den birkaç kişi kayıt olup giriş yapabilmeli."""

    def setUp(self):
        cache.clear()

    def test_five_registrations_from_one_ip(self):
        for i in range(5):
            resp = self.client.post(
                reverse("users:api_register"),
                data=json.dumps({"email": f"kisi{i}@example.com", "password": "SuperGizli123",
                                 "first_name": "Kişi", "last_name": "Bir"}),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200, f"{i + 1}. kayıt engellendi")

    def test_six_logins_from_one_ip(self):
        for _ in range(6):
            resp = self.client.post(reverse("users:login"), {"username": "yok@example.com", "password": "yanlis"})
        self.assertEqual(resp.status_code, 200)  # form hatası, 429 değil
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test users.tests.SharedIpRateLimitTests -v 2`
Expected: FAIL (`4. kayıt engellendi`, ikinci test 429).

- [ ] **Step 3: Uygula**

`users/api.py`:

```python
# Stand haftası: ortak cihaz ve kampüs Wi-Fi'ında (tek genel IP) kayıtlar tıkanmasın.
@ratelimit(key='ip', rate='30/h', block=False)
```

`users/views.py`:

```python
# Kampüs Wi-Fi'ında öğrencilerin çoğu aynı genel IP'den çıkar; başarılı girişler de sayılır.
@method_decorator(ratelimit(key='ip', rate='30/5m', block=False), name='post')
```

- [ ] **Step 4: Geçtiğini gör**

Run: `venv/Scripts/python.exe manage.py test users -v 1`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add users/api.py users/views.py users/tests.py
git commit -m "Kayit ve giris hiz sinirlari stand/kampus NAT icin gevsetildi"
```

---

# PARÇA B — Yılan oyunu ve liderlik tablosu

### Task 6: `arcade` uygulaması, modeller, `GAME_SPAM`

**Files:**
- Create: `arcade/__init__.py` (boş), `arcade/apps.py`, `arcade/models.py`, `arcade/tests.py`, `arcade/migrations/0001_initial.py` (üretilir)
- Modify: `nishdot/settings/base.py` (`LOCAL_APPS`), `dashboard/models.py`
- Create: `dashboard/migrations/0010_securitylog_game_spam.py` (üretilir)

**Interfaces:**
- Produces: `arcade.models.MAX_SCORE = 397`, `UNCLAIMED_TTL = timedelta(hours=24)`, `PENDING_SESSION_KEY = "arcade_pending"`; `Competition` (`name`, `starts_at`, `ends_at`, `is_visible`, `Competition.current() -> Competition | None`, `.status -> Competition.Status` = `"upcoming" | "live" | "ended"`); `GameRun` (`user` null'lanabilir FK, `score`, `duration_ms`, `nonce` unique, `is_disqualified`, `created_at`); `SecurityLog.ActionType.GAME_SPAM`. Test yardımcıları `arcade/tests.py`'de: `yarisma(...)`, `oyuncu(email, first_name="Ali", last_name="Veli", **kw)`, `kosu(user, score, at=None, **kw)`.

- [ ] **Step 1: Uygulama iskeleti**

`arcade/__init__.py`: boş dosya.

`arcade/apps.py`:

```python
from django.apps import AppConfig


class ArcadeConfig(AppConfig):
    name = "arcade"
    verbose_name = "Oyun (Yılan)"
```

`nishdot/settings/base.py` — `LOCAL_APPS` listesine `"dashboard",` satırından sonra:

```python
    "arcade",
```

- [ ] **Step 2: Başarısız testleri yaz**

`arcade/tests.py`:

```python
"""
Yılan oyunu: model, liderlik tablosu, API, sahiplenme ve temizlik testleri.
"""
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from arcade.models import Competition, GameRun

User = get_user_model()


def yarisma(baslangic=timedelta(days=-1), bitis=timedelta(days=6), gorunur=True, name="Stand Haftası"):
    """Varsayılan: dün başlamış, 6 gün sonra bitecek, ana sayfada görünen yarışma."""
    simdi = timezone.now()
    return Competition.objects.create(
        name=name, starts_at=simdi + baslangic, ends_at=simdi + bitis, is_visible=gorunur,
    )


def oyuncu(email, first_name="Ali", last_name="Veli", **kw):
    return User.objects.create_user(
        username=email, email=email, password="SuperGizli123",
        first_name=first_name, last_name=last_name, **kw,
    )


def kosu(user, score, at=None, **kw):
    """Bir oyun kaydı; at verilirse created_at (auto_now_add) sonradan ezilir."""
    run = GameRun.objects.create(
        user=user, score=score, duration_ms=60_000, nonce=secrets.token_hex(16), **kw,
    )
    if at is not None:
        GameRun.objects.filter(pk=run.pk).update(created_at=at)
        run.refresh_from_db()
    return run


class CompetitionTests(TestCase):
    def test_current_returns_latest_visible(self):
        yarisma(gorunur=False, baslangic=timedelta(hours=-1), name="Gizli")
        yarisma(baslangic=timedelta(days=-30), bitis=timedelta(days=-20), name="Eski")
        yeni = yarisma(name="Yeni")
        self.assertEqual(Competition.current(), yeni)

    def test_current_none_when_nothing_visible(self):
        yarisma(gorunur=False)
        self.assertIsNone(Competition.current())

    def test_status(self):
        self.assertEqual(yarisma(baslangic=timedelta(days=1), bitis=timedelta(days=2)).status, "upcoming")
        self.assertEqual(yarisma().status, "live")
        self.assertEqual(yarisma(baslangic=timedelta(days=-3), bitis=timedelta(days=-1)).status, "ended")

    def test_clean_rejects_end_before_start(self):
        simdi = timezone.now()
        c = Competition(name="Ters", starts_at=simdi, ends_at=simdi - timedelta(hours=1))
        with self.assertRaises(ValidationError):
            c.clean()
```

- [ ] **Step 3: Başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test arcade -v 2`
Expected: `ImportError: cannot import name 'Competition'`.

- [ ] **Step 4: Modelleri yaz**

`arcade/models.py`:

```python
"""
Yılan Oyunu — Veri Modeli
==========================

Competition: admin'den yönetilen yarışma penceresi + aç/kapa anahtarı
             ("Ana sayfada göster"). Stand haftası bitince kutu kaldırılır;
             deploy gerekmez.
GameRun:     tek bir oyunun skoru. Yarışmaya FK ile bağlı DEĞİLDİR; hangi
             yarışmaya sayılacağını created_at zaman damgası belirler.
"""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel

# 20x20 ızgara, başlangıç uzunluğu 3 → en fazla 400 - 3 = 397 yem.
# static/js/snake.js'teki GRID / START_LEN ile birlikte değişmelidir.
MAX_SCORE = 397

# Üye olmadan oynanan skor, bu süre içinde aynı tarayıcıdan giriş/kayıt
# yapılırsa hesaba bağlanır; sonra purge_expired_data siler.
UNCLAIMED_TTL = timedelta(hours=24)

# Sahipsiz skor kimliklerinin tutulduğu oturum anahtarı.
PENDING_SESSION_KEY = "arcade_pending"


class Competition(TimeStampedModel):
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Başlamadı"
        LIVE = "live", "Sürüyor"
        ENDED = "ended", "Bitti"

    name = models.CharField(max_length=120, verbose_name="Ad")
    starts_at = models.DateTimeField(verbose_name="Başlangıç")
    ends_at = models.DateTimeField(verbose_name="Bitiş")
    is_visible = models.BooleanField(
        default=False,
        verbose_name="Ana sayfada göster",
        help_text="Açıkken ana sayfada oyun bölümü ve menü bağlantısı görünür. "
                  "Kapatınca oyun tamamen kapanır (API dahil).",
    )

    class Meta:
        ordering = ["-starts_at"]
        verbose_name = "Yarışma"
        verbose_name_plural = "Yarışmalar"

    def __str__(self):
        return self.name

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Bitiş, başlangıçtan sonra olmalı."})

    @classmethod
    def current(cls):
        """Ana sayfada gösterilen yarışma; yoksa None (oyun kapalı)."""
        return cls.objects.filter(is_visible=True).order_by("-starts_at").first()

    @property
    def status(self):
        simdi = timezone.now()
        if simdi < self.starts_at:
            return self.Status.UPCOMING
        if simdi > self.ends_at:
            return self.Status.ENDED
        return self.Status.LIVE


class GameRun(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="game_runs",
        verbose_name="Oyuncu",
        help_text="Boşsa skor henüz sahiplenilmemiş (üye olmadan oynanmış).",
    )
    score = models.PositiveIntegerField(verbose_name="Skor")
    duration_ms = models.PositiveIntegerField(verbose_name="Süre (ms)")
    # Biletin tek kullanımlık olmasını veritabanı garanti eder.
    nonce = models.CharField(max_length=32, unique=True, editable=False)
    is_disqualified = models.BooleanField(default=False, verbose_name="Diskalifiye")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Tarih")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Oyun skoru"
        verbose_name_plural = "Oyun skorları"

    def __str__(self):
        return f"Skor {self.score}"
```

`dashboard/models.py` — `SecurityLog.ActionType` içinde `OTP_ABUSE` satırının altına:

```python
        GAME_SPAM = "game_spam", "Oyun Skoru (Spam) Sınırı"
```

- [ ] **Step 5: Migration'ları üret**

Run:
```bash
venv/Scripts/python.exe manage.py makemigrations arcade
venv/Scripts/python.exe manage.py makemigrations dashboard --name securitylog_game_spam
```
Expected: `arcade/migrations/0001_initial.py` (Competition, GameRun) ve `dashboard/migrations/0010_securitylog_game_spam.py` (AlterField action). Başka uygulamada migration çıkmamalı.

- [ ] **Step 6: Testlerin geçtiğini gör**

Run: `venv/Scripts/python.exe manage.py test arcade -v 2`
Expected: 4 test OK.

Run: `venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
Expected: `No changes detected`.

- [ ] **Step 7: Commit**

```bash
git add arcade nishdot/settings/base.py dashboard/models.py dashboard/migrations/0010_securitylog_game_spam.py
git commit -m "arcade uygulamasi: Competition ve GameRun modelleri"
```

---

### Task 7: Liderlik tablosu servisi ve admin

**Files:**
- Create: `arcade/services.py`, `arcade/admin.py`
- Test: `arcade/tests.py`

**Interfaces:**
- Consumes: `Competition`, `GameRun` (Task 6).
- Produces: `display_name(user) -> str`; `leaderboard(competition, limit=10, user=None) -> {"tablo": [{"sira": int, "ad": str, "skor": int, "bu_sen_misin": bool}], "sen": {"sira": int, "en_iyi": int} | None}` (`user` AnonymousUser olabilir); `home_context(user) -> None | {"competition", "status", "tablo", "sen"}`.

- [ ] **Step 1: Başarısız testleri yaz**

`arcade/tests.py` import'larına ekle:

```python
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from arcade.services import display_name, leaderboard
```

Dosyanın sonuna ekle:

```python
class DisplayNameTests(TestCase):
    def test_formats(self):
        ornekler = [
            ("ilker", "yılmaz", "ilker Y."),
            ("Ömer", "ince", "Ömer İ."),   # Python upper(): "i" → "I" olurdu
            ("Ali", "ışık", "Ali I."),
            ("Ali", "", "Ali"),
            ("", "Veli", "Oyuncu"),
        ]
        for ad, soyad, beklenen in ornekler:
            with self.subTest(ad=ad, soyad=soyad):
                self.assertEqual(display_name(User(first_name=ad, last_name=soyad)), beklenen)


class LeaderboardTests(TestCase):
    def setUp(self):
        self.yarisma = yarisma()
        self.ali = oyuncu("ali@example.com", "Ali", "Veli")
        self.ayse = oyuncu("ayse@example.com", "Ayşe", "Kaya")

    def _ozet(self, **kw):
        return [(s["ad"], s["skor"]) for s in leaderboard(self.yarisma, **kw)["tablo"]]

    def test_best_score_per_player(self):
        kosu(self.ali, 5)
        kosu(self.ali, 12)
        kosu(self.ayse, 8)
        self.assertEqual(self._ozet(), [("Ali V.", 12), ("Ayşe K.", 8)])

    def test_tie_goes_to_earlier(self):
        simdi = timezone.now()
        kosu(self.ayse, 10, at=simdi - timedelta(hours=1))
        kosu(self.ali, 10, at=simdi - timedelta(hours=2))
        self.assertEqual(self._ozet()[0], ("Ali V.", 10))

    def test_excludes_disqualified_unclaimed_and_out_of_window(self):
        kosu(self.ali, 50, is_disqualified=True)
        kosu(None, 60)
        kosu(self.ayse, 70, at=self.yarisma.starts_at - timedelta(minutes=1))
        kosu(self.ayse, 3)
        self.assertEqual(self._ozet(), [("Ayşe K.", 3)])

    def test_limit_and_own_rank_outside_top(self):
        for i in range(12):
            kosu(oyuncu(f"o{i}@example.com"), 100 - i)
        kosu(self.ali, 1)
        sonuc = leaderboard(self.yarisma, limit=10, user=self.ali)
        self.assertEqual(len(sonuc["tablo"]), 10)
        self.assertEqual(sonuc["sen"], {"sira": 13, "en_iyi": 1})
        self.assertFalse(any(s["bu_sen_misin"] for s in sonuc["tablo"]))

    def test_own_row_flagged(self):
        kosu(self.ali, 9)
        sonuc = leaderboard(self.yarisma, user=self.ali)
        self.assertTrue(sonuc["tablo"][0]["bu_sen_misin"])
        self.assertEqual(sonuc["sen"], {"sira": 1, "en_iyi": 9})

    def test_anonymous_has_no_row(self):
        kosu(self.ali, 9)
        self.assertIsNone(leaderboard(self.yarisma, user=AnonymousUser())["sen"])


class GameRunAdminTests(TestCase):
    def setUp(self):
        admin = User.objects.create_superuser(
            username="admin@example.com", email="admin@example.com", password="SuperGizli123",
        )
        self.client.force_login(admin)
        self.url = reverse("admin:arcade_gamerun_changelist")

    def test_changelist_renders(self):
        kosu(oyuncu("ali@example.com"), 5)
        kosu(None, 3)
        resp = self.client.get(self.url)
        self.assertContains(resp, "Ali V.")
        self.assertContains(resp, "— sahipsiz —")

    def test_disqualify_action_drops_score_from_board(self):
        y = yarisma()
        run = kosu(oyuncu("ali@example.com"), 40)
        self.client.post(self.url, {"action": "diskalifiye_et", "_selected_action": [run.pk]})
        self.assertEqual(leaderboard(y)["tablo"], [])
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test arcade -v 2`
Expected: `ModuleNotFoundError: No module named 'arcade.services'`.

- [ ] **Step 3: Servisi yaz**

`arcade/services.py`:

```python
"""
Liderlik Tablosu
=================

Kurallar:
    - Kapsam: yarışma penceresinde (starts_at ≤ created_at ≤ ends_at),
      sahiplenilmiş (user dolu) ve diskalifiye edilmemiş koşular.
    - Her oyuncunun EN İYİ skoru sayılır; eşitlikte o skora DAHA ÖNCE ulaşan üstte.

Uygulama: koşular (-score, created_at) sırasıyla okunur, her oyuncunun ilk
görülen kaydı alınır. Stand haftası ölçeğinde (yüzler/binler) yeterince hızlı;
gerekirse sonradan önbelleklenir.
"""

from .models import Competition, GameRun

TABLE_SIZE = 10

# Python'un upper()'ı Türkçe bilmez: "i".upper() == "I" (doğrusu "İ").
_TR_UPPER = {"i": "İ", "ı": "I"}


def display_name(user):
    """Tabloda görünen ad: "Ömer S." — ad + soyadın Türkçe büyütülmüş baş harfi."""
    ad = (user.first_name or "").strip()
    if not ad:
        return "Oyuncu"
    soyad = (user.last_name or "").strip()
    if not soyad:
        return ad
    bas_harf = _TR_UPPER.get(soyad[0], soyad[0].upper())
    return f"{ad} {bas_harf}."


def leaderboard(competition, limit=TABLE_SIZE, user=None):
    """
    Döner: {"tablo": [{"sira", "ad", "skor", "bu_sen_misin"}, ...],
            "sen": {"sira", "en_iyi"} | None}
    """
    kosular = (
        GameRun.objects
        .filter(
            created_at__gte=competition.starts_at,
            created_at__lte=competition.ends_at,
            user__isnull=False,
            is_disqualified=False,
        )
        .select_related("user")
        .order_by("-score", "created_at")
    )
    user_id = user.pk if user is not None and user.is_authenticated else None

    tablo, sen, gorulen = [], None, set()
    for kosu in kosular.iterator():
        if kosu.user_id in gorulen:
            continue
        gorulen.add(kosu.user_id)
        sira = len(gorulen)
        bu_sen = kosu.user_id == user_id
        if sira <= limit:
            tablo.append({
                "sira": sira,
                "ad": display_name(kosu.user),
                "skor": kosu.score,
                "bu_sen_misin": bu_sen,
            })
        if bu_sen:
            sen = {"sira": sira, "en_iyi": kosu.score}
        if sira >= limit and (user_id is None or sen is not None):
            break
    return {"tablo": tablo, "sen": sen}


def home_context(user):
    """Ana sayfa oyun bölümünün bağlamı; oyun kapalıysa None."""
    competition = Competition.current()
    if competition is None:
        return None
    status = competition.status
    tablo = {"tablo": [], "sen": None}
    if status != Competition.Status.UPCOMING:
        tablo = leaderboard(competition, user=user)
    return {"competition": competition, "status": status, **tablo}
```

- [ ] **Step 4: Admin'i yaz**

`arcade/admin.py`:

```python
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
```

- [ ] **Step 5: Testlerin geçtiğini gör**

Run: `venv/Scripts/python.exe manage.py test arcade -v 2`
Expected: tümü OK.

- [ ] **Step 6: Commit**

```bash
git add arcade/services.py arcade/admin.py arcade/tests.py
git commit -m "Liderlik tablosu servisi ve oyun admini"
```

---

### Task 8: Oyun API'si (`basla` / `bitir`)

**Files:**
- Create: `arcade/views.py`, `arcade/urls.py`
- Modify: `nishdot/urls.py`
- Test: `arcade/tests.py`

**Interfaces:**
- Consumes: `Competition.current()`, `GameRun`, `MAX_SCORE`, `PENDING_SESSION_KEY` (Task 6); `leaderboard` (Task 7); `SecurityLog.ActionType.GAME_SPAM`.
- Produces: `POST /oyun/api/basla/` (ad `arcade:start`) → `{"bilet": str}`; `POST /oyun/api/bitir/` (ad `arcade:finish`) gövde `{bilet, skor, sure_ms}` → `{"kaydedildi": true, "bekliyor": bool, "durum": "upcoming"|"live"|"ended", "tablo": [...], "sen": {...}|null}`; ret → `400 {"error": "Skor kaydedilemedi."}`; sınır → `429`; oyun kapalı → `404`. `arcade.views.GAME_RATE` (testte `mock.patch` ile düşürülür).

> Spec'e küçük ek: yanıta `"durum"` anahtarı eklendi — sayfa açıkken yarışma başlar/biterse JS doğru mesajı göstersin diye.

- [ ] **Step 1: Başarısız testleri yaz**

`arcade/tests.py` import'larına ekle:

```python
import json
import time
from unittest import mock

from django.core import signing
from django.core.cache import cache
from django.test import override_settings

from dashboard.models import SecurityLog
```

Dosyanın sonuna ekle:

```python
@override_settings(RATELIMIT_ENABLE=False)
class GameApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.yarisma = yarisma()

    def _bilet(self):
        return self.client.post(reverse("arcade:start")).json()["bilet"]

    def _bitir(self, bilet, skor=7, sure_ms=1000):
        return self.client.post(
            reverse("arcade:finish"),
            data=json.dumps({"bilet": bilet, "skor": skor, "sure_ms": sure_ms}),
            content_type="application/json",
        )

    def assertRejected(self, **kwargs):
        with self.assertLogs("arcade.views", level="WARNING"):
            resp = self._bitir(**kwargs)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {"error": "Skor kaydedilemedi."})  # sebep sızdırılmaz

    def test_start_returns_ticket(self):
        resp = self.client.post(reverse("arcade:start"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("bilet", resp.json())

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("arcade:start")).status_code, 405)

    def test_endpoints_404_when_switched_off(self):
        Competition.objects.update(is_visible=False)
        self.assertEqual(self.client.post(reverse("arcade:start")).status_code, 404)
        self.assertEqual(self._bitir("x").status_code, 404)

    def test_logged_in_score_saved_to_account(self):
        ali = oyuncu("ali@example.com")
        self.client.force_login(ali)
        resp = self._bitir(self._bilet(), skor=7)
        self.assertEqual(resp.status_code, 200)
        veri = resp.json()
        self.assertFalse(veri["bekliyor"])
        self.assertEqual(veri["durum"], "live")
        self.assertEqual(veri["sen"], {"sira": 1, "en_iyi": 7})
        self.assertEqual(veri["tablo"][0]["ad"], "Ali V.")
        self.assertEqual(GameRun.objects.get().user, ali)

    def test_anonymous_score_saved_unclaimed_and_remembered(self):
        resp = self._bitir(self._bilet())
        self.assertTrue(resp.json()["bekliyor"])
        self.assertIsNone(resp.json()["sen"])
        run = GameRun.objects.get()
        self.assertIsNone(run.user)
        self.assertEqual(self.client.session["arcade_pending"], [run.pk])

    def test_pending_list_capped_at_20(self):
        oturum = self.client.session
        oturum["arcade_pending"] = list(range(1000, 1020))
        oturum.save()
        self._bitir(self._bilet())
        bekleyen = self.client.session["arcade_pending"]
        self.assertEqual(len(bekleyen), 20)
        self.assertEqual(bekleyen[-1], GameRun.objects.get().pk)

    def test_ticket_single_use(self):
        bilet = self._bilet()
        self.assertEqual(self._bitir(bilet).status_code, 200)
        self.assertRejected(bilet=bilet)
        self.assertEqual(GameRun.objects.count(), 1)

    def test_tampered_ticket_rejected(self):
        self.assertRejected(bilet=self._bilet() + "x")

    def test_expired_ticket_rejected(self):
        with mock.patch("django.core.signing.time.time", return_value=time.time() - 31 * 60):
            bilet = signing.dumps({"n": "a" * 32, "t": 0}, salt="arcade.run")
        self.assertRejected(bilet=bilet)

    def test_duration_longer_than_elapsed_rejected(self):
        # Bilet az önce verildi; 60 sn'lik oyun iddiası imkânsız.
        self.assertRejected(bilet=self._bilet(), sure_ms=60_000)

    def test_score_above_max_rejected(self):
        self.assertRejected(bilet=self._bilet(), skor=398)

    def test_bool_score_rejected(self):
        self.assertRejected(bilet=self._bilet(), skor=True)

    def test_upcoming_competition_saves_but_returns_empty_board(self):
        Competition.objects.update(
            starts_at=timezone.now() + timedelta(days=1), ends_at=timezone.now() + timedelta(days=7),
        )
        self.client.force_login(oyuncu("ali@example.com"))
        veri = self._bitir(self._bilet()).json()
        self.assertEqual((veri["durum"], veri["tablo"], veri["sen"]), ("upcoming", [], None))
        self.assertEqual(GameRun.objects.count(), 1)


class GameRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        yarisma()

    def test_limit_returns_429_and_logs(self):
        with mock.patch("arcade.views.GAME_RATE", "2/h"):
            kodlar = [self.client.post(reverse("arcade:start")).status_code for _ in range(3)]
        self.assertEqual(kodlar, [200, 200, 429])
        self.assertEqual(SecurityLog.objects.filter(action=SecurityLog.ActionType.GAME_SPAM).count(), 1)
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test arcade.tests.GameApiTests arcade.tests.GameRateLimitTests -v 2`
Expected: `NoReverseMatch: 'arcade' is not a registered namespace`.

- [ ] **Step 3: Görünümleri yaz**

`arcade/views.py`:

```python
"""
Yılan Oyunu API'si
===================

POST /oyun/api/basla/  → imzalı, tek kullanımlık bilet
POST /oyun/api/bitir/  → {bilet, skor, sure_ms} ile skoru kaydet

Skor istemcide hesaplanır; sunucu oyunu tekrar oynatmaz (ödüller küçük —
bilinçli karar, bkz. spec §2 ve §8). Korkuluklar bariz sahteliği ve sel
baskınını durdurur:
    1. skor 0–397, süre 0–30 dk aralığında tamsayı
    2. bilet imzalı ve en fazla 30 dk önce verilmiş
    3. bildirilen süre, bilet verildiğinden beri geçen gerçek süreyi aşamaz
       (yüksek skor iddiası o kadar beklemeyi gerektirir)
    4. bilet tek kullanımlık (nonce unique)

Ret sebebi istemciye söylenmez (yalnızca "Skor kaydedilemedi."); log'a yazılır.
"""

import json
import logging
import secrets
import time

from django.core import signing
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from core.http import get_client_ip
from dashboard.models import SecurityLog

from .models import MAX_SCORE, PENDING_SESSION_KEY, Competition, GameRun
from .services import leaderboard

logger = logging.getLogger(__name__)

TICKET_SALT = "arcade.run"
TICKET_MAX_AGE = 30 * 60          # sn
MAX_DURATION_MS = 30 * 60 * 1000
CLOCK_SLACK_MS = 2000             # saat farkı ve ağ gecikmesi payı
PENDING_LIMIT = 20                # oturumda tutulan sahipsiz skor kimliği

# Kampüs Wi-Fi'ında öğrencilerin çoğu aynı genel IP'den çıkar ve yeni başlayan
# biri 5-10 sn'de ölüp yeniden başlar. Sınırın tek işi veritabanını sel
# baskınından korumaktır; tablonun bütünlüğünü süre kontrolü korur.
GAME_RATE = "1200/h"

REJECTED = "Skor kaydedilemedi."


def _game_rate(group, request):
    # Sabit çağrı anında okunur; testler mock.patch ile düşürebilir.
    return GAME_RATE


def _now_ms():
    return int(time.time() * 1000)


def _active_competition():
    """Oyun kapalıysa (ana sayfada gösterilen yarışma yoksa) 404."""
    competition = Competition.current()
    if competition is None:
        raise Http404
    return competition


def _rate_limited(request):
    SecurityLog.objects.create(
        ip_address=get_client_ip(request),
        action=SecurityLog.ActionType.GAME_SPAM,
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    return JsonResponse({"error": "Çok hızlı gidiyorsun, biraz sonra tekrar dene."}, status=429)


def _reject(request, reason):
    logger.warning("Oyun skoru reddedildi: %s (ip=%s)", reason, get_client_ip(request))
    return JsonResponse({"error": REJECTED}, status=400)


@ratelimit(key="user_or_ip", rate=_game_rate, block=False)
@require_POST
def start_run(request):
    _active_competition()
    if getattr(request, "limited", False):
        return _rate_limited(request)
    bilet = signing.dumps({"n": secrets.token_hex(16), "t": _now_ms()}, salt=TICKET_SALT)
    return JsonResponse({"bilet": bilet})


@ratelimit(key="user_or_ip", rate=_game_rate, block=False)
@require_POST
def finish_run(request):
    competition = _active_competition()
    if getattr(request, "limited", False):
        return _rate_limited(request)

    try:
        data = json.loads(request.body)
        bilet, skor, sure_ms = data["bilet"], data["skor"], data["sure_ms"]
    except (ValueError, KeyError, TypeError):
        return _reject(request, "gövde okunamadı")

    # bool, int'in alt sınıfıdır: True skor olarak geçmesin.
    if type(skor) is not int or type(sure_ms) is not int or not isinstance(bilet, str):
        return _reject(request, "tür")
    if not (0 <= skor <= MAX_SCORE and 0 < sure_ms <= MAX_DURATION_MS):
        return _reject(request, f"aralık (skor={skor}, sure_ms={sure_ms})")

    try:
        payload = signing.loads(bilet, salt=TICKET_SALT, max_age=TICKET_MAX_AGE)
        nonce, verildi_ms = str(payload["n"]), int(payload["t"])
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        return _reject(request, "bilet geçersiz veya süresi dolmuş")

    if _now_ms() - verildi_ms + CLOCK_SLACK_MS < sure_ms:
        return _reject(request, f"süre tutarsız (sure_ms={sure_ms})")

    user = request.user if request.user.is_authenticated else None
    try:
        with transaction.atomic():
            run = GameRun.objects.create(user=user, score=skor, duration_ms=sure_ms, nonce=nonce)
    except IntegrityError:
        return _reject(request, "bilet ikinci kez kullanıldı")

    if user is None:
        # Giriş/kayıt sonrası arcade.signals bu kimlikleri hesaba bağlar.
        bekleyen = request.session.get(PENDING_SESSION_KEY, [])[-(PENDING_LIMIT - 1):]
        request.session[PENDING_SESSION_KEY] = [*bekleyen, run.pk]

    tablo = {"tablo": [], "sen": None}
    if competition.status != Competition.Status.UPCOMING:
        tablo = leaderboard(competition, user=user)

    return JsonResponse({
        "kaydedildi": True,
        "bekliyor": user is None,
        "durum": competition.status,
        "tablo": tablo["tablo"],
        "sen": tablo["sen"],
    })
```

`arcade/urls.py`:

```python
from django.urls import path

from . import views

app_name = "arcade"

urlpatterns = [
    path("api/basla/", views.start_run, name="start"),
    path("api/bitir/", views.finish_run, name="finish"),
]
```

`nishdot/urls.py` — `path("management/", ...)` satırından sonra:

```python

    # Stand haftası yılan oyunu (admin'den aç/kapa)
    path("oyun/", include("arcade.urls")),
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `venv/Scripts/python.exe manage.py test arcade -v 2`
Expected: tümü OK.

- [ ] **Step 5: Commit**

```bash
git add arcade/views.py arcade/urls.py arcade/tests.py nishdot/urls.py
git commit -m "Oyun API'si: imzali bilet, skor gonderimi ve korkuluklar"
```

---

### Task 9: Sahipsiz skorun girişte/kayıtta sahiplenilmesi

**Files:**
- Create: `arcade/signals.py`
- Modify: `arcade/apps.py`
- Test: `arcade/tests.py`

**Interfaces:**
- Consumes: `PENDING_SESSION_KEY`, `UNCLAIMED_TTL`, `GameRun` (Task 6); `users:api_register`'ın `login()` çağırması (Task 3).
- Produces: `user_logged_in` alıcısı `claim_pending_runs`.

- [ ] **Step 1: Başarısız testleri yaz** (`arcade/tests.py` sonuna)

```python
@override_settings(RATELIMIT_ENABLE=False)
class ClaimPendingRunsTests(TestCase):
    def setUp(self):
        cache.clear()
        yarisma()

    def _anonim_oyna(self, skor=9):
        bilet = self.client.post(reverse("arcade:start")).json()["bilet"]
        self.client.post(
            reverse("arcade:finish"),
            data=json.dumps({"bilet": bilet, "skor": skor, "sure_ms": 1000}),
            content_type="application/json",
        )
        return GameRun.objects.latest("created_at")

    def _giris(self, email):
        self.client.post(reverse("users:login"), {"username": email, "password": "SuperGizli123"})

    def test_claimed_on_login(self):
        oyuncu("ali@example.com")
        run = self._anonim_oyna()
        self._giris("ali@example.com")
        run.refresh_from_db()
        self.assertEqual(run.user.email, "ali@example.com")
        self.assertNotIn("arcade_pending", self.client.session)

    def test_claimed_on_register(self):
        run = self._anonim_oyna()
        self.client.post(
            reverse("users:api_register"),
            data=json.dumps({"email": "yeni@example.com", "password": "SuperGizli123",
                             "first_name": "Yeni", "last_name": "Üye", "next": "/#oyun"}),
            content_type="application/json",
        )
        run.refresh_from_db()
        self.assertEqual(run.user.email, "yeni@example.com")

    def test_old_unclaimed_run_not_claimed(self):
        oyuncu("ali@example.com")
        run = self._anonim_oyna()
        GameRun.objects.filter(pk=run.pk).update(created_at=timezone.now() - timedelta(hours=25))
        self._giris("ali@example.com")
        run.refresh_from_db()
        self.assertIsNone(run.user)

    def test_someone_elses_run_not_taken(self):
        ayse = oyuncu("ayse@example.com", "Ayşe", "Kaya")
        onun = kosu(ayse, 30)
        oturum = self.client.session
        oturum["arcade_pending"] = [onun.pk]
        oturum.save()
        oyuncu("ali@example.com")
        self._giris("ali@example.com")
        onun.refresh_from_db()
        self.assertEqual(onun.user, ayse)
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test arcade.tests.ClaimPendingRunsTests -v 2`
Expected: `test_claimed_on_login` ve `test_claimed_on_register` FAIL (`run.user` None).

- [ ] **Step 3: Uygula**

`arcade/signals.py`:

```python
"""
Sahipsiz Skorların Sahiplenilmesi
==================================

Üye olmadan oynanan skorların kimlikleri oturumda (PENDING_SESSION_KEY)
tutulur. Aynı tarayıcıdan giriş ya da kayıt yapılınca (kayıt da login()
çağırır) son 24 saatteki sahipsiz skorlar hesaba bağlanır.

Django'nun login()'i anonim oturumdan girişte oturum anahtarını yeniler
(cycle_key) ama verisini korur; liste girişten sonra da okunabilir.
"""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

from .models import PENDING_SESSION_KEY, UNCLAIMED_TTL, GameRun


@receiver(user_logged_in, dispatch_uid="arcade_claim_pending_runs")
def claim_pending_runs(sender, request, user, **kwargs):
    session = getattr(request, "session", None)
    if session is None:
        return
    bekleyen = session.pop(PENDING_SESSION_KEY, None)
    if not bekleyen:
        return
    # user__isnull: oturuma başkasının kaydı yazılmış olsa bile yalnızca sahipsizler bağlanır.
    GameRun.objects.filter(
        pk__in=bekleyen,
        user__isnull=True,
        created_at__gte=timezone.now() - UNCLAIMED_TTL,
    ).update(user=user)
```

`arcade/apps.py` — `ArcadeConfig`'e ekle:

```python

    def ready(self):
        # user_logged_in alıcısını bağlar (sahipsiz skorların sahiplenilmesi).
        from . import signals  # noqa: F401
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `venv/Scripts/python.exe manage.py test arcade users -v 1`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add arcade/signals.py arcade/apps.py arcade/tests.py
git commit -m "Uye olmadan yapilan skor giris ve kayitta hesaba baglanir"
```

---

### Task 10: Ana sayfa bölümü, navbar bağlantısı, aç/kapa anahtarı

**Files:**
- Create: `arcade/context_processors.py`, `templates/arcade/_section.html`, `templates/arcade/_row.html`
- Modify: `nishdot/settings/base.py` (`context_processors`), `pages/views.py`, `templates/pages/home.html`, `templates/components/navbar.html`
- Modify: `static/css/output.css` (derleme)
- Test: `arcade/tests.py`

**Interfaces:**
- Consumes: `home_context(user)` (Task 7); `arcade:start`, `arcade:finish` (Task 8).
- Produces: şablon değişkeni `arcade_visible` (her sayfa) ve `arcade` (ana sayfa). DOM sözleşmesi (Task 11'deki `snake.js` bunlara bağlıdır): `section[data-arcade]` + `data-csrf`, `data-start-url`, `data-finish-url`, `data-verified`; kimlikler `#snake-play`, `#snake-canvas`, `#snake-start`, `#snake-start-btn`, `#snake-over`, `#snake-final`, `#snake-best`, `#snake-msg`, `#snake-guest`, `#snake-again`, `#snake-score`, `#snake-pad` (`[data-dir]` butonları), `#arcade-board`, `template#arcade-row` (`[data-sira]`, `[data-ad]`, `[data-skor]`), `#arcade-me`, `#arcade-verify`.

- [ ] **Step 1: Başarısız testleri yaz** (`arcade/tests.py` sonuna)

```python
class HomeSectionTests(TestCase):
    KVKK_NOTU = "Skorunu kaydettiğinde adın ve soyadının baş harfi tabloda herkese açık görünür."

    def test_hidden_when_switched_off(self):
        yarisma(gorunur=False)
        resp = self.client.get(reverse("pages:home"))
        self.assertNotContains(resp, 'id="oyun"')
        self.assertNotContains(resp, 'href="/#oyun"')
        self.assertNotContains(resp, "js/snake")

    def test_visible_when_switched_on(self):
        yarisma()
        resp = self.client.get(reverse("pages:home"))
        self.assertContains(resp, 'id="oyun"')
        self.assertContains(resp, 'href="/#oyun"')
        self.assertContains(resp, "js/snake")
        self.assertContains(resp, self.KVKK_NOTU)

    def test_navbar_link_on_other_pages(self):
        yarisma()
        self.assertContains(self.client.get(reverse("users:login")), 'href="/#oyun"')

    def test_board_with_own_row_highlighted(self):
        yarisma()
        ali = oyuncu("ali@example.com", is_verified=True)
        kosu(ali, 15)
        self.client.force_login(ali)
        resp = self.client.get(reverse("pages:home"))
        self.assertContains(resp, "Ali V.")
        self.assertContains(resp, "data-me", count=1)

    def test_unverified_player_in_table_sees_hint(self):
        yarisma()
        ali = oyuncu("ali@example.com", is_verified=False)
        kosu(ali, 15)
        self.client.force_login(ali)
        resp = self.client.get(reverse("pages:home"))
        self.assertContains(resp, 'id="arcade-verify" class="mt-3')  # "hidden" ile başlamıyor

    def test_upcoming_shows_start_time_not_board(self):
        yarisma(baslangic=timedelta(days=1), bitis=timedelta(days=7))
        resp = self.client.get(reverse("pages:home"))
        self.assertContains(resp, "şimdiden ısın")
        self.assertNotContains(resp, 'id="arcade-board"')
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test arcade.tests.HomeSectionTests -v 2`
Expected: `test_hidden_when_switched_off` geçer, diğerleri FAIL.

- [ ] **Step 3: Context processor ve görünüm**

`arcade/context_processors.py`:

```python
from .models import Competition


def arcade_visible(request):
    """Navbar her sayfada var; oyun bağlantısı yalnızca oyun açıkken görünür."""
    return {"arcade_visible": Competition.current() is not None}
```

`nishdot/settings/base.py` — `TEMPLATES[0]["OPTIONS"]["context_processors"]` listesinin sonuna:

```python
                "arcade.context_processors.arcade_visible",
```

`pages/views.py` — import'lara `from arcade.services import home_context` ekle; `HomePageView.get_context_data` içinde `return context`'ten önce:

```python
        # Yılan oyunu bölümü; admin'de "Ana sayfada göster" kapalıysa None.
        context['arcade'] = home_context(self.request.user)
```

- [ ] **Step 4: Şablonlar**

`templates/arcade/_row.html`:

```html
<li class="flex items-center gap-3 rounded-xl border border-white/5 bg-zinc-800/40 px-4 py-3 data-[me]:border-brand-pink/50 data-[me]:bg-brand-pink/10"{% if me %} data-me{% endif %}>
    <span class="w-10 font-bold text-brand-pink tabular-nums" data-sira>{% if sira %}#{{ sira }}{% endif %}</span>
    <span class="flex-1 truncate text-zinc-200" data-ad>{{ ad }}</span>
    <span class="font-bold text-white tabular-nums" data-skor>{{ skor }}</span>
</li>
```

`templates/arcade/_section.html`:

```html
{# Yılan oyunu — yalnızca admin'de "Ana sayfada göster" açık bir yarışma varken render edilir (arcade/services.home_context). #}
{# data-csrf: şablon token'a dokunduğu için anonim ziyaretçiye de CSRF çerezi gider; yoksa ilk gönderim 403 alırdı. #}
<section id="oyun" class="py-20 bg-zinc-900 border-t border-zinc-800/50 scroll-mt-20"
         data-arcade
         data-csrf="{{ csrf_token }}"
         data-start-url="{% url 'arcade:start' %}"
         data-finish-url="{% url 'arcade:finish' %}"
         data-verified="{% if user.is_verified %}1{% else %}0{% endif %}">
    <div class="container-main">
        <div class="text-center mb-10">
            <h2 class="section-title">Yılan</h2>
            <p class="section-subtitle">{{ arcade.competition.name }}</p>
            <p class="text-zinc-400 mt-4 max-w-xl mx-auto">
                Yemleri topla, duvara ve kendine çarpma. Her yem 1 puan; yılan büyüdükçe hızlanır.
                Yarışma sonunda tablonun zirvesindekilere küçük ödüllerimiz var.
            </p>
        </div>

        <div id="snake-play" class="flex flex-col items-center gap-4">
            <div class="relative w-full max-w-[480px] aspect-square">
                <canvas id="snake-canvas" class="block w-full h-full rounded-2xl border border-zinc-800 bg-zinc-950 touch-none select-none"
                        role="img" aria-label="Yılan oyunu alanı"></canvas>

                <div id="snake-start" class="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-2xl bg-zinc-950/70">
                    <button type="button" id="snake-start-btn" class="btn-primary px-8 py-3 text-lg">Başla</button>
                    <p class="text-xs text-zinc-400">Ok tuşları / WASD · telefonda kaydır ya da yön tuşları</p>
                </div>

                <div id="snake-over" class="hidden absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-2xl bg-zinc-950/85 px-6 text-center">
                    <p class="text-sm uppercase tracking-widest text-zinc-500">Skorun</p>
                    <p id="snake-final" class="text-6xl font-black text-white tabular-nums">0</p>
                    <p id="snake-best" class="text-sm text-zinc-400"></p>
                    <p id="snake-msg" class="text-sm text-zinc-300 max-w-xs"></p>
                    <div id="snake-guest" class="hidden flex flex-col sm:flex-row gap-2">
                        <a href="{% url 'users:register' %}?next=/%23oyun" class="btn-primary">Tabloya girmek için üye ol</a>
                        <a href="{% url 'users:login' %}?next=/%23oyun" class="btn-outline">Giriş yap</a>
                    </div>
                    <button type="button" id="snake-again" class="btn-outline mt-2">Tekrar</button>
                </div>
            </div>

            <p class="text-sm text-zinc-400" aria-live="polite">
                Skor: <span id="snake-score" class="font-bold text-white tabular-nums">0</span>
            </p>

            <!-- Yön tuşları: yalnızca dokunmatik ekranlarda görünür -->
            <div id="snake-pad" class="hidden [@media(pointer:coarse)]:grid grid-cols-3 gap-2 select-none" aria-label="Yön tuşları">
                <span></span>
                <button type="button" data-dir="up" class="h-16 w-16 rounded-2xl border border-zinc-700 bg-zinc-800 text-2xl text-zinc-200 active:bg-brand-pink active:text-white touch-manipulation" aria-label="Yukarı">&#9650;</button>
                <span></span>
                <button type="button" data-dir="left" class="h-16 w-16 rounded-2xl border border-zinc-700 bg-zinc-800 text-2xl text-zinc-200 active:bg-brand-pink active:text-white touch-manipulation" aria-label="Sol">&#9664;</button>
                <button type="button" data-dir="down" class="h-16 w-16 rounded-2xl border border-zinc-700 bg-zinc-800 text-2xl text-zinc-200 active:bg-brand-pink active:text-white touch-manipulation" aria-label="Aşağı">&#9660;</button>
                <button type="button" data-dir="right" class="h-16 w-16 rounded-2xl border border-zinc-700 bg-zinc-800 text-2xl text-zinc-200 active:bg-brand-pink active:text-white touch-manipulation" aria-label="Sağ">&#9654;</button>
            </div>

            <p class="text-xs text-zinc-500 text-center max-w-md">
                Skorunu kaydettiğinde adın ve soyadının baş harfi tabloda herkese açık görünür.
            </p>
        </div>

        <div class="max-w-md mx-auto mt-12">
            {% if arcade.status == "upcoming" %}
                <p class="text-center text-zinc-300 bg-zinc-800/40 border border-white/5 rounded-2xl p-6">
                    Yarışma <strong class="text-white">{{ arcade.competition.starts_at|date:"j F, H:i" }}</strong> itibarıyla başlıyor — şimdiden ısın.
                </p>
            {% else %}
                <h3 class="text-xl font-bold text-white text-center mb-1">Liderlik Tablosu</h3>
                {% if arcade.status == "ended" %}
                    <p class="text-center text-sm text-zinc-400 mb-4">Yarışma bitti. Final sıralaması:</p>
                {% else %}
                    <p class="text-center text-sm text-zinc-500 mb-4">Herkesin en iyi skoru sayılır.</p>
                {% endif %}

                <ol id="arcade-board" class="space-y-2">
                    {% for satir in arcade.tablo %}
                        {% include "arcade/_row.html" with sira=satir.sira ad=satir.ad skor=satir.skor me=satir.bu_sen_misin %}
                    {% empty %}
                        <li class="text-center text-zinc-500 py-6">Henüz skor yok — ilk sen ol!</li>
                    {% endfor %}
                </ol>
                <template id="arcade-row">{% include "arcade/_row.html" only %}</template>

                <p id="arcade-me" class="{% if not arcade.sen or arcade.sen.sira <= arcade.tablo|length %}hidden {% endif %}mt-3 text-center text-sm text-zinc-300">{% if arcade.sen %}Senin sıran: #{{ arcade.sen.sira }} · en iyin {{ arcade.sen.en_iyi }}{% endif %}</p>
                <p id="arcade-verify" class="{% if not arcade.sen or user.is_verified %}hidden {% endif %}mt-3 text-center text-sm text-amber-300">
                    Ödül kazanırsan sana ulaşabilmemiz için e-postanı doğrula.
                </p>
            {% endif %}
        </div>
    </div>
</section>
```

`templates/pages/home.html` — `<!-- ABOUT US SECTION -->` satırının hemen üstüne:

```html
{% if arcade %}
{% include "arcade/_section.html" %}
{% endif %}

```

Aynı dosyada `{% block extra_scripts %}` satırının hemen altına:

```html
{% if arcade %}<script src="{% static 'js/snake.js' %}" defer></script>{% endif %}
```

`templates/components/navbar.html` — "Etkinlikler" bağlantısının `</a>`'sından sonra, "Hakkımızda"dan önce:

```html
                {% if arcade_visible %}
                <a href="{% url 'pages:home' %}#oyun" class="nav-link text-zinc-300 hover:text-white transition-colors relative group py-2">
                    Oyun
                    <span class="absolute left-0 bottom-0 w-full h-[2px] bg-brand-pink transform scale-x-0 transition-transform duration-300 origin-left group-[.active]:scale-x-100 group-hover:scale-x-100"></span>
                </a>
                {% endif %}
```

- [ ] **Step 5: CSS'i derle ve yeni sınıfların çıktıda olduğunu doğrula**

Run: `npm run build:css`

Run: `for s in "data-me" "pointer:coarse" "aspect-square" "touch-none"; do printf "%s: " "$s"; grep -c "$s" static/css/output.css; done`
Expected: dördü de ≥ 1 (Tailwind yeni sınıfları üretmiş).

- [ ] **Step 6: Testlerin geçtiğini gör**

Run: `venv/Scripts/python.exe manage.py test -v 1`
Expected: OK.

- [ ] **Step 7: Commit**

```bash
git add arcade/context_processors.py templates/arcade nishdot/settings/base.py pages/views.py templates/pages/home.html templates/components/navbar.html static/css/output.css arcade/tests.py
git commit -m "Ana sayfada oyun bolumu, liderlik tablosu ve navbar baglantisi"
```

---

### Task 11: `snake.js` — oyunun kendisi

**Files:**
- Create: `static/js/snake.js`

**Interfaces:**
- Consumes: Task 10'daki DOM sözleşmesi; Task 8'deki API gövdeleri/yanıtları.

> JS için otomatik test yok (spec §5.11); doğrulama Step 2–4'teki tarayıcı kontrolüyle ve ekip testiyle yapılır.

- [ ] **Step 1: Oyunu yaz**

`static/js/snake.js`:

```js
/*
 * Nishdot — Yılan (stand haftası oyunu)
 * =====================================
 * Kütüphanesiz. Ayarlar ana sayfadaki #oyun bölümünün data-* niteliklerinden
 * okunur (templates/arcade/_section.html).
 *
 * Kurallar sunucuyla uyumlu olmalı (arcade/models.py → MAX_SCORE = 397):
 * 20x20 ızgara, başlangıç uzunluğu 3 → en fazla 397 yem. GRID ya da START_LEN
 * değişirse MAX_SCORE da değişmeli.
 *
 * Akış: Başla → POST basla/ (bilet) → oyun → bitiş → POST bitir/ → tablo güncellenir.
 * Duraklatma yok: sekme gizlenirse oyun biter ve skor keepalive ile gönderilir.
 */
(function () {
    "use strict";

    const root = document.querySelector("[data-arcade]");
    if (!root) return;

    const GRID = 20;
    const START_LEN = 3;
    const BASE_SPEED = 8;      // adım/sn
    const SPEED_STEP = 0.25;   // her yemde eklenen adım/sn
    const MAX_SPEED = 16;
    const SWIPE_MIN = 24;      // px — bu kadar kaymadan yön değişmez
    const MAX_FRAME_MS = 250;  // takılan bir karede yılan ışınlanmasın

    const COLORS = {
        bg: "#09090b",
        grid: "rgba(255, 255, 255, 0.035)",
        head: "#EB596D",
        body: "rgba(235, 89, 109, 0.72)",
        food: "#fecdd3",
        glow: "#EB596D",
    };

    const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
    const KEYS = {
        ArrowUp: "up", KeyW: "up",
        ArrowDown: "down", KeyS: "down",
        ArrowLeft: "left", KeyA: "left",
        ArrowRight: "right", KeyD: "right",
    };

    const cfg = root.dataset;
    const $ = (sel) => root.querySelector(sel);
    const canvas = $("#snake-canvas");
    const ctx = canvas.getContext("2d");
    const ui = {
        play: $("#snake-play"),
        start: $("#snake-start"),
        startBtn: $("#snake-start-btn"),
        over: $("#snake-over"),
        final: $("#snake-final"),
        best: $("#snake-best"),
        msg: $("#snake-msg"),
        guest: $("#snake-guest"),
        again: $("#snake-again"),
        score: $("#snake-score"),
        pad: $("#snake-pad"),
        board: $("#arcade-board"),
        rowTpl: $("#arcade-row"),
        me: $("#arcade-me"),
        verify: $("#arcade-verify"),
    };

    let game = null;      // null: hiç oynanmadı; game.over: bitti
    let cell = 0;         // bir hücrenin CSS piksel boyu
    let localBest = 0;    // bu sayfa açıkken en iyi skor (anonim için)
    let starting = false;

    // ---------------------------------------------------------------- çizim

    function resize() {
        const size = canvas.clientWidth;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.round(size * dpr);
        canvas.height = Math.round(size * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        cell = size / GRID;
        draw();
    }

    function block(x, y, color) {
        const pad = cell * 0.06;
        const s = cell - pad * 2;
        ctx.fillStyle = color;
        if (ctx.roundRect) {
            ctx.beginPath();
            ctx.roundRect(x * cell + pad, y * cell + pad, s, s, s * 0.3);
            ctx.fill();
        } else {
            ctx.fillRect(x * cell + pad, y * cell + pad, s, s);
        }
    }

    function draw() {
        const size = cell * GRID;
        ctx.fillStyle = COLORS.bg;
        ctx.fillRect(0, 0, size, size);

        ctx.strokeStyle = COLORS.grid;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let i = 1; i < GRID; i++) {
            ctx.moveTo(i * cell, 0);
            ctx.lineTo(i * cell, size);
            ctx.moveTo(0, i * cell);
            ctx.lineTo(size, i * cell);
        }
        ctx.stroke();

        if (!game) return;

        if (game.food) {
            ctx.save();
            ctx.shadowColor = COLORS.glow;
            ctx.shadowBlur = cell * 0.8;
            ctx.fillStyle = COLORS.food;
            ctx.beginPath();
            ctx.arc((game.food[0] + 0.5) * cell, (game.food[1] + 0.5) * cell, cell * 0.3, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }

        for (let i = game.snake.length - 1; i >= 0; i--) {
            const p = game.snake[i];
            block(p[0], p[1], i === 0 ? COLORS.head : COLORS.body);
        }
    }

    // ---------------------------------------------------------------- oyun

    function newGame(ticket) {
        const mid = Math.floor(GRID / 2);
        const snake = [];
        for (let i = 0; i < START_LEN; i++) snake.push([mid - i, mid]);   // sağa bakar
        game = {
            snake,
            dir: "right",
            queue: [],          // tamponlanmış yön değişiklikleri (en fazla 2)
            food: null,
            score: 0,
            speed: BASE_SPEED,
            acc: 0,
            last: 0,
            startedAt: performance.now(),
            ticket,
            over: false,
        };
        game.food = placeFood();
    }

    function placeFood() {
        const taken = new Set(game.snake.map((p) => p[0] * GRID + p[1]));
        const free = [];
        for (let x = 0; x < GRID; x++) {
            for (let y = 0; y < GRID; y++) {
                if (!taken.has(x * GRID + y)) free.push([x, y]);
            }
        }
        return free.length ? free[Math.floor(Math.random() * free.length)] : null;
    }

    function step() {
        if (game.queue.length) game.dir = game.queue.shift();
        const d = DIRS[game.dir];
        const head = game.snake[0];
        const next = [head[0] + d[0], head[1] + d[1]];
        const eats = game.food && next[0] === game.food[0] && next[1] === game.food[1];

        // Yem yenmiyorsa kuyruk bu adımda çekilir; kuyruğun hücresine girmek serbest.
        const body = eats ? game.snake : game.snake.slice(0, -1);
        const hitsWall = next[0] < 0 || next[1] < 0 || next[0] >= GRID || next[1] >= GRID;
        const hitsSelf = body.some((p) => p[0] === next[0] && p[1] === next[1]);
        if (hitsWall || hitsSelf) {
            end(false);
            return;
        }

        game.snake.unshift(next);
        if (eats) {
            game.score += 1;
            game.speed = Math.min(MAX_SPEED, BASE_SPEED + game.score * SPEED_STEP);
            ui.score.textContent = game.score;
            game.food = placeFood();
            if (!game.food) end(false);   // tahta doldu (397)
        } else {
            game.snake.pop();
        }
    }

    function turn(dir) {
        if (!game || game.over) return;
        const q = game.queue;
        const last = q.length ? q[q.length - 1] : game.dir;
        if (q.length >= 2 || dir === last) return;
        const a = DIRS[dir];
        const b = DIRS[last];
        if (a[0] === -b[0] && a[1] === -b[1]) return;   // 180° geri dönüş yok
        q.push(dir);
    }

    function frame(now) {
        if (!game || game.over) return;
        if (!game.last) game.last = now;
        game.acc += Math.min(now - game.last, MAX_FRAME_MS);
        game.last = now;
        while (!game.over && game.acc >= 1000 / game.speed) {
            game.acc -= 1000 / game.speed;
            step();
        }
        draw();
        if (!game.over) requestAnimationFrame(frame);
    }

    async function start() {
        if (starting || (game && !game.over)) return;
        starting = true;
        ui.startBtn.disabled = true;
        ui.again.disabled = true;

        let ticket = null;
        try {
            const res = await post(cfg.startUrl, {});
            if (res.ok) ticket = (await res.json()).bilet;
        } catch (err) {
            // Bağlantı yoksa yine oynansın; skor kaydedilemez, bitişte söylenir.
        }

        starting = false;
        ui.startBtn.disabled = false;
        ui.again.disabled = false;
        newGame(ticket);
        ui.score.textContent = "0";
        ui.start.classList.add("hidden");
        ui.over.classList.add("hidden");
        ui.play.scrollIntoView({ behavior: "smooth", block: "center" });
        requestAnimationFrame(frame);
    }

    function end(hidden) {
        game.over = true;
        draw();
        const score = game.score;
        const durationMs = Math.max(1, Math.round(performance.now() - game.startedAt));
        localBest = Math.max(localBest, score);

        ui.final.textContent = score;
        ui.best.textContent = "En iyin: " + localBest;
        ui.msg.textContent = "Kaydediliyor…";
        ui.guest.classList.add("hidden");
        ui.over.classList.remove("hidden");

        submit(score, durationMs, game.ticket, hidden);
    }

    // ---------------------------------------------------------------- sunucu

    function post(url, body, keepalive) {
        // keepalive: sekme kapanırken de istek tamamlanır; özel başlığa (CSRF) izin verir.
        return fetch(url, {
            method: "POST",
            credentials: "same-origin",
            keepalive: Boolean(keepalive),
            headers: { "Content-Type": "application/json", "X-CSRFToken": cfg.csrf },
            body: JSON.stringify(body),
        });
    }

    async function submit(score, durationMs, ticket, keepalive) {
        const failed = "Bağlantı sorunu nedeniyle bu skor kaydedilemedi.";
        if (!ticket) {
            ui.msg.textContent = failed;
            return;
        }
        let res;
        let data;
        try {
            res = await post(cfg.finishUrl, { bilet: ticket, skor: score, sure_ms: durationMs }, keepalive);
            data = await res.json();
        } catch (err) {
            ui.msg.textContent = failed;
            return;
        }
        if (!res.ok) {
            ui.msg.textContent = data.error || "Skor kaydedilemedi.";
            return;
        }

        if (data.sen) ui.best.textContent = "En iyin: " + data.sen.en_iyi;

        if (data.durum === "ended") {
            ui.msg.textContent = "Yarışma bitti; bu skor sıralamaya girmez.";
        } else if (data.durum === "upcoming") {
            ui.msg.textContent = "Isınma turu! Yarışma başlayınca skorlar sayılmaya başlar.";
        } else if (data.bekliyor) {
            ui.msg.textContent = "Skorun bu tarayıcıda 24 saat bekler; üye olursan ya da giriş yaparsan tabloya eklenir.";
        } else {
            ui.msg.textContent = data.sen ? "Tablodaki sıran: #" + data.sen.sira : "Skorun kaydedildi.";
        }
        if (data.bekliyor) ui.guest.classList.remove("hidden");

        renderBoard(data.tablo, data.sen);
    }

    function renderBoard(rows, me) {
        if (!ui.board || !ui.rowTpl) return;   // yarışma başlamadı: tablo yok
        if (rows.length) {
            ui.board.replaceChildren(...rows.map((r) => {
                const li = ui.rowTpl.content.firstElementChild.cloneNode(true);
                li.querySelector("[data-sira]").textContent = "#" + r.sira;
                li.querySelector("[data-ad]").textContent = r.ad;
                li.querySelector("[data-skor]").textContent = r.skor;
                if (r.bu_sen_misin) li.setAttribute("data-me", "");
                return li;
            }));
        }
        if (ui.me) {
            const outside = Boolean(me) && me.sira > rows.length;
            ui.me.textContent = outside ? "Senin sıran: #" + me.sira + " · en iyin " + me.en_iyi : "";
            ui.me.classList.toggle("hidden", !outside);
        }
        if (ui.verify) ui.verify.classList.toggle("hidden", !(me && cfg.verified !== "1"));
    }

    // ---------------------------------------------------------------- girdi

    window.addEventListener("keydown", (e) => {
        if (!game || game.over) return;
        const dir = KEYS[e.code];
        if (dir) {
            e.preventDefault();   // oyun sürerken sayfa kaymasın
            turn(dir);
        } else if (e.code === "Space") {
            e.preventDefault();
        }
    });

    let touch = null;
    canvas.addEventListener("touchstart", (e) => {
        const t = e.changedTouches[0];
        touch = [t.clientX, t.clientY];
    }, { passive: true });
    canvas.addEventListener("touchmove", (e) => {
        if (!touch) return;
        const t = e.changedTouches[0];
        const dx = t.clientX - touch[0];
        const dy = t.clientY - touch[1];
        if (Math.max(Math.abs(dx), Math.abs(dy)) < SWIPE_MIN) return;
        turn(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up"));
        touch = [t.clientX, t.clientY];   // parmağı kaldırmadan art arda dönülebilsin
    }, { passive: true });
    canvas.addEventListener("touchend", () => { touch = null; });
    canvas.addEventListener("touchcancel", () => { touch = null; });

    ui.pad.querySelectorAll("[data-dir]").forEach((btn) => {
        btn.addEventListener("pointerdown", (e) => {
            e.preventDefault();
            turn(btn.dataset.dir);
        });
    });

    ui.startBtn.addEventListener("click", start);
    ui.again.addEventListener("click", start);

    document.addEventListener("visibilitychange", () => {
        if (document.hidden && game && !game.over) end(true);
    });

    if ("ResizeObserver" in window) {
        new ResizeObserver(resize).observe(canvas);
    } else {
        window.addEventListener("resize", resize);
    }
    resize();
})();
```

- [ ] **Step 2: Lokal sunucu + açık yarışma**

```bash
venv/Scripts/python.exe manage.py migrate
venv/Scripts/python.exe manage.py shell -c "from datetime import timedelta; from django.utils import timezone; from arcade.models import Competition; n=timezone.now(); Competition.objects.create(name='Yerel Test', starts_at=n-timedelta(hours=1), ends_at=n+timedelta(days=7), is_visible=True)"
```

Sunucuyu `preview_start` ile başlat (`.claude/launch.json`: `venv/Scripts/python.exe manage.py runserver 8000`; bu dosya commit'lenmez).

- [ ] **Step 3: Tarayıcıda masaüstü kontrolü**

- `/` yükle → `#oyun` bölümü Etkinlikler ile Hakkımızda arasında, navbar'da "Oyun".
- Konsolda hata yok (`read_console_messages`, `onlyErrors`).
- "Başla" → ok tuşlarıyla birkaç yem ye → duvara çarp → bitiş katmanı, "Kaydediliyor…" yerini mesaja bırakıyor; ağ sekmesinde `basla` 200, `bitir` 200.
- Oyun sürerken ok tuşları sayfayı kaydırmıyor (`window.scrollY` sabit).
- Anonim bitişte "Tabloya girmek için üye ol" görünüyor → tıkla → kayıt ol → `/#oyun`'a dönüyor, bant görünüyor, skor tabloda.

- [ ] **Step 4: Telefon görünümü kontrolü**

`resize_window` preset `mobile` → sayfayı yeniden yükle → yön tuşları görünür, tuval ekrana sığıyor, yatay kaydırma yok. Kontrol bitince preset `desktop`.

- [ ] **Step 5: Commit**

```bash
git add static/js/snake.js
git commit -m "Yilan oyunu istemcisi (canvas, klavye, kaydirma, yon tuslari)"
```

---

### Task 12: Veri saklama — eski oyun skorlarının temizlenmesi

**Files:**
- Modify: `pages/management/commands/purge_expired_data.py`
- Test: `arcade/tests.py`

**Interfaces:**
- Consumes: `UNCLAIMED_TTL`, `GameRun` (Task 6); komutun mevcut `GENEL_GUN = 365`.

- [ ] **Step 1: Başarısız testleri yaz**

`arcade/tests.py` import'larına ekle:

```python
from io import StringIO

from django.core.management import call_command
```

Dosyanın sonuna ekle:

```python
class PurgeGameRunsTests(TestCase):
    def test_purges_old_unclaimed_and_year_old_runs(self):
        simdi = timezone.now()
        ali = oyuncu("ali@example.com")
        kosu(None, 5, at=simdi - timedelta(hours=25))       # silinir
        yeni_sahipsiz = kosu(None, 5, at=simdi - timedelta(hours=1))
        kosu(ali, 9, at=simdi - timedelta(days=366))        # silinir
        guncel = kosu(ali, 9)

        call_command("purge_expired_data", stdout=StringIO())

        self.assertEqual(set(GameRun.objects.values_list("pk", flat=True)), {yeni_sahipsiz.pk, guncel.pk})

    def test_dry_run_deletes_nothing(self):
        kosu(None, 5, at=timezone.now() - timedelta(hours=25))
        call_command("purge_expired_data", "--dry-run", stdout=StringIO())
        self.assertEqual(GameRun.objects.count(), 1)
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `venv/Scripts/python.exe manage.py test arcade.tests.PurgeGameRunsTests -v 2`
Expected: ilk test FAIL (4 kayıt duruyor).

- [ ] **Step 3: Uygula**

`pages/management/commands/purge_expired_data.py`:

`handle()` içinde `self._suresi_dolan_basvurulari_sil(simdi, kuru)` satırının altına:

```python
        self._eski_oyun_skorlarini_sil(simdi, kuru)
```

Dosyanın sonuna:

```python

    def _eski_oyun_skorlarini_sil(self, simdi, kuru):
        """Sahiplenilmemiş oyun skorları 24 saatte, tüm skorlar 1 yılda silinir."""
        from django.db.models import Q

        from arcade.models import UNCLAIMED_TTL, GameRun

        hedef = GameRun.objects.filter(
            Q(user__isnull=True, created_at__lt=simdi - UNCLAIMED_TTL)
            | Q(created_at__lt=simdi - timedelta(days=GENEL_GUN))
        )
        adet = hedef.count()
        self.stdout.write(f"Oyun skorları (sahipsiz 24 saat / tümü {GENEL_GUN} gün): {adet} kayıt")
        if not kuru:
            hedef.delete()
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `venv/Scripts/python.exe manage.py test arcade events.tests.PurgeExpiredDataTests -v 1`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add pages/management/commands/purge_expired_data.py arcade/tests.py
git commit -m "Temizlik komutuna eski oyun skorlari adimi"
```

---

### Task 13: Dokümantasyon ve son doğrulama

**Files:**
- Modify: `README.md`, `docs/ARCHITECTURE.md`

- [ ] **Step 1: README**

`README.md`:
- `- **OTP'li üyelik** — ...` maddesini şununla değiştir:
  `- **Anında üyelik** — Kayıt olan hemen giriş yapar; e-posta 3 gün geçerli bir linkle doğrulanır. Doğrulama hiçbir işlemi kilitlemez, her sayfadaki bir bantla hatırlatılır. Şifre sıfırlama Django'nun yerleşik token sistemiyle.`
- Aynı listeye, `QR çekilişi` maddesinin altına:
  `- **Yılan oyunu** — Ana sayfada liderlik tablolu yarışma; üye olmadan oynanır, skor üyelikle tabloya girer. Yarışma penceresi ve aç/kapa anahtarı admin'den yönetilir.`
- Mermaid diyagramında `U["users<br/>OTP kayıt · profil"]` → `U["users<br/>kayıt · e-posta doğrulama · profil"]`; aynı alt grafiğe `A["arcade<br/>yılan oyunu · liderlik tablosu"]` satırı; `P & E & J & U & D --> C` → `P & E & J & U & D & A --> C`.
- Dizin yapısında `├── users/                # CustomUser (e-posta ile giriş), OTP akışı` → `├── users/                # CustomUser (e-posta ile giriş), doğrulama linki` ve `dashboard/` satırının altına `├── arcade/               # Yılan oyunu: yarışma, skor API'si, liderlik tablosu`.

- [ ] **Step 2: ARCHITECTURE**

`docs/ARCHITECTURE.md`:
- `- **`users/`**: Custom user model and authentication (OTP-based email verification).` → `- **`users/`**: Custom user model and authentication (optional email verification via a 3-day link).` ve altına `- **`arcade/`**: Stand-week snake game — competition window, signed-ticket score API, leaderboard.`
- 3.2'deki `Auth Flow` satırını şununla değiştir: `- **Auth Flow:** Registration requires Name, Surname, Email, Password. The user is logged in immediately and a verification link (users/tokens.py, valid PASSWORD_RESET_TIMEOUT = 3 days) is emailed. Verification locks nothing; unverified users see a reminder banner. verification_code / code_expires_at are legacy fields kept for rollback compatibility.`

- [ ] **Step 3: Tam doğrulama (CI'ın lokal karşılığı)**

```bash
venv/Scripts/python.exe -m pip install "ruff>=0.14,<1.0"
venv/Scripts/python.exe -m ruff check .
venv/Scripts/python.exe manage.py check
venv/Scripts/python.exe manage.py makemigrations --check --dry-run
venv/Scripts/python.exe manage.py test -v 1
```
Expected: ruff `All checks passed!`; check temiz; `No changes detected`; tüm testler OK (96'dan fazla).

`check --deploy` production bağımlılıkları (psycopg, redis) ister; CI'da çalışır → kullanıcı dalı push'layıp `main`'e PR açınca görülür.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/ARCHITECTURE.md
git commit -m "Dokumantasyon: istege bagli dogrulama ve yilan oyunu"
```

- [ ] **Step 5: Kullanıcıya teslim notu**

Kullanıcıya ilet (komutlar ayrı `bash` bloklarında):
1. Push ve PR: `git push -u origin oyun-ve-dogrulama` → GitHub'da `main`'e PR (CI çalışır).
2. Ekip testi: spec §6 madde 2'deki kontrol listesi.
3. Yayın gecesi: spec §6 madde 3 (önce `pg_dump`), sunucu komutları; admin'de yarışma oluşturma.
4. Not: `createsuperuser` ile açılmış yönetim hesaplarında `is_verified` False olabilir → bandı görürler; admin'den kutuyu işaretlemek ya da bir kez "Tekrar gönder" yeterli.
5. Stand haftası sonrası: admin'de "Ana sayfada göster" kapatılır.
