"""
Kayıt / OTP güvenlik testleri.

En kritik regresyon: e-posta doğrulama bypass'ının (eski form POST'unun)
tekrar açılmadığını garanti eder.
"""
import json
import re
from unittest import mock

from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.messages import get_messages
from django.core import mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from dashboard.models import SecurityLog
from users.tokens import email_verification_token
from users.views import INVALID_LINK_MESSAGE

User = get_user_model()


class RegisterBypassTests(TestCase):
    def test_register_page_get_ok(self):
        resp = self.client.get(reverse("users:register"))
        self.assertEqual(resp.status_code, 200)

    def test_register_form_post_does_not_create_user(self):
        """
        REGRESYON: /auth/register/'a doğrudan form POST'u ATILAMAMALI.
        Eskiden bu, OTP'siz doğrulanmış oturum açıyordu.
        """
        resp = self.client.post(reverse("users:register"), {
            "first_name": "Ali", "last_name": "Veli",
            "email": "bypass@example.com",
            "password": "SuperGizli123", "password_confirm": "SuperGizli123",
        })
        self.assertEqual(resp.status_code, 405)  # Method Not Allowed
        self.assertFalse(User.objects.filter(email="bypass@example.com").exists())
        # Oturum açılmamış olmalı
        self.assertNotIn("_auth_user_id", self.client.session)


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


class AnnouncementVisibilityTests(TestCase):
    """Site içi duyurular yalnızca published_to_site=True ise görünmeli."""

    def setUp(self):
        self.uye = User.objects.create_user(
            username="uye", email="uye@example.com", password="x", is_verified=True
        )
        self.yonetim = User.objects.create_user(
            username="yk", email="yk@example.com", password="x",
            is_verified=True, is_staff=True, role=User.Role.BOARD,
        )

    def _duyuru(self, baslik, hedef, yayinda):
        from dashboard.models import Announcement
        return Announcement.objects.create(
            title=baslik, content="icerik",
            target_audience=hedef, published_to_site=yayinda,
        )

    def _panel_duyurulari(self, kullanici):
        self.client.force_login(kullanici)
        resp = self.client.get(reverse("users:dashboard"))
        self.assertEqual(resp.status_code, 200)
        return {d.title for d in resp.context["announcements"]}

    def test_email_only_board_announcement_hidden_from_site(self):
        """REGRESYON: published_to_site=False olan 'board' duyurusu sızmamalı."""
        self._duyuru("sadece-mail-board", "board", yayinda=False)
        self.assertNotIn("sadece-mail-board", self._panel_duyurulari(self.yonetim))

    def test_email_only_members_announcement_hidden_from_site(self):
        """REGRESYON: published_to_site=False olan 'members' duyurusu sızmamalı."""
        self._duyuru("sadece-mail-uye", "members", yayinda=False)
        self.assertNotIn("sadece-mail-uye", self._panel_duyurulari(self.uye))

    def test_published_board_announcement_visible_to_board(self):
        self._duyuru("yayinda-board", "board", yayinda=True)
        self.assertIn("yayinda-board", self._panel_duyurulari(self.yonetim))

    def test_board_announcement_hidden_from_regular_member(self):
        self._duyuru("yayinda-board", "board", yayinda=True)
        self.assertNotIn("yayinda-board", self._panel_duyurulari(self.uye))

    def test_published_all_announcement_visible_to_everyone(self):
        self._duyuru("herkese", "all", yayinda=True)
        self.assertIn("herkese", self._panel_duyurulari(self.uye))
        self.assertIn("herkese", self._panel_duyurulari(self.yonetim))

    def test_consented_announcement_visible_when_published(self):
        """6563 sayılı Kanun e-posta/SMS gönderimini düzenler; kullanıcının
        kendi isteğiyle girdiği panelde içerik göstermek ticari elektronik
        ileti değildir. 'consented' hedefi site içinde 'all' gibi davranır."""
        self._duyuru("onaylilara", "consented", yayinda=True)
        self.assertIn("onaylilara", self._panel_duyurulari(self.uye))


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
