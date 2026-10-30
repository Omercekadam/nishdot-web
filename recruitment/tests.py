"""
Yönetim kurulu alımı: üye başvuru formu, ana sayfa duyurusu, karargah sayfası ve temizlik.
"""
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from arcade.models import Competition
from recruitment.models import BoardApplication, RecruitmentRound

User = get_user_model()


def uye(email="aday@example.com", **kw):
    kw.setdefault("first_name", "Ayşe")
    kw.setdefault("last_name", "Kaya")
    return User.objects.create_user(username=email, email=email, password="SuperGizli123", **kw)


def donem(acik=True, title="2026-2027 Yönetim Kurulu"):
    return RecruitmentRound.objects.create(title=title, is_open=acik)


def gecerli_form(**degisen):
    veri = {
        "department": "Dijital Oyun Tasarımı",
        "grade": "2",
        "phone": "0555 111 22 33",
        "motivation": "Kulübe katkı vermek istiyorum.",
        "club_opinion": "Etkinlikler güzel, duyurular daha erken yapılabilir.",
        "project_idea": "",
        "positions": ["etkinlik", "teknik"],
        "experience": "",
        "weekly_hours": "5-10",
        "portfolio": "",
        "extra": "",
    }
    veri.update(degisen)
    return veri


def basvuru(round_, user, **kw):
    alanlar = gecerli_form()
    alanlar["positions"] = ",".join(alanlar["positions"])
    alanlar.update(kw)
    return BoardApplication.objects.create(round=round_, user=user, **alanlar)


class ApplyViewTests(TestCase):
    def setUp(self):
        self.url = reverse("recruitment:apply")

    def test_anonymous_redirected_to_login_and_back(self):
        donem()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("users:login"), resp["Location"])
        self.assertIn("next=/basvuru/", resp["Location"])

    def test_closed_when_no_open_round(self):
        donem(acik=False)
        self.client.force_login(uye())
        resp = self.client.get(self.url)
        self.assertContains(resp, "Başvurular şu an kapalı")
        self.assertNotContains(resp, 'name="motivation"')

    def test_form_shows_questions_and_prefills_profile(self):
        donem()
        self.client.force_login(uye(phone_number="0532 000 00 00", department="Yazılım Mühendisliği"))
        resp = self.client.get(self.url)
        self.assertContains(resp, "Neden ekibimize katılmak istiyorsun?")
        self.assertContains(resp, "Kulübe haftada kaç saat ayırabilirsin?")
        self.assertContains(resp, "Teknik Ekip / Proje Geliştirme")
        self.assertContains(resp, 'value="0532 000 00 00"')
        self.assertContains(resp, 'value="Yazılım Mühendisliği"')
        self.assertContains(resp, "aday@example.com")  # e-posta hesaptan, yeniden sorulmaz
        self.assertNotContains(resp, "---------")         # tek seçimli sorularda boş seçenek yok

    def test_valid_submission_saved_once(self):
        r = donem()
        kisi = uye()
        self.client.force_login(kisi)
        resp = self.client.post(self.url, gecerli_form())
        self.assertRedirects(resp, self.url, fetch_redirect_response=False)
        app = BoardApplication.objects.get()
        self.assertEqual((app.round, app.user, app.positions), (r, kisi, "etkinlik,teknik"))
        self.assertEqual(app.status, BoardApplication.Status.PENDING)

        self.assertContains(self.client.get(self.url), "Başvurun alındı")
        self.client.post(self.url, gecerli_form(motivation="ikinci deneme"))
        self.assertEqual(BoardApplication.objects.count(), 1)

    def test_position_required(self):
        donem()
        self.client.force_login(uye())
        resp = self.client.post(self.url, gecerli_form(positions=[]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "En az bir pozisyon seç.")
        self.assertFalse(BoardApplication.objects.exists())

    def test_invalid_phone_rejected(self):
        donem()
        self.client.force_login(uye())
        resp = self.client.post(self.url, gecerli_form(phone="123"))
        self.assertContains(resp, "Geçerli bir telefon numarası yaz.")
        self.assertFalse(BoardApplication.objects.exists())

    def test_cannot_apply_after_round_closed(self):
        r = donem()
        self.client.force_login(uye())
        r.is_open = False
        r.save()
        self.client.post(self.url, gecerli_form())
        self.assertFalse(BoardApplication.objects.exists())


class HomeAnnouncementTests(TestCase):
    def test_open_round_announced_in_hero(self):
        donem()
        resp = self.client.get(reverse("pages:home"))
        self.assertContains(resp, 'href="/basvuru/"')
        self.assertContains(resp, "2026-2027 Yönetim Kurulu")

    def test_no_announcement_when_closed(self):
        donem(acik=False)
        self.assertNotContains(self.client.get(reverse("pages:home")), 'href="/basvuru/"')

    def test_ended_tournament_leaves_hero_but_game_stays(self):
        simdi = timezone.now()
        Competition.objects.create(
            name="Yılan Turnuvası", starts_at=simdi - timedelta(days=10),
            ends_at=simdi - timedelta(days=5), is_visible=True,
        )
        resp = self.client.get(reverse("pages:home"))
        self.assertNotContains(resp, 'href="#oyun"')  # hero duyurusu kalktı
        self.assertContains(resp, 'id="oyun"')         # oyun bölümü yerinde


class ManagePageTests(TestCase):
    def setUp(self):
        self.yonetici = uye("yk@example.com", is_staff=True, first_name="Ömer", last_name="S")
        self.url = reverse("dashboard:recruitment")

    def test_requires_staff(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)  # anonim → giriş
        self.client.force_login(uye())
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_create_round_then_toggle(self):
        self.client.force_login(self.yonetici)
        self.assertContains(self.client.get(self.url), 'name="title"')
        self.client.post(reverse("dashboard:recruitment_create"), {"title": "2026-2027 Yönetim Kurulu"})
        r = RecruitmentRound.objects.get()
        self.assertFalse(r.is_open)
        self.client.post(reverse("dashboard:recruitment_toggle"))
        r.refresh_from_db()
        self.assertTrue(r.is_open)
        self.client.post(reverse("dashboard:recruitment_toggle"))
        r.refresh_from_db()
        self.assertFalse(r.is_open)

    def test_post_endpoints_reject_get(self):
        self.client.force_login(self.yonetici)
        for ad in ("recruitment_create", "recruitment_toggle", "recruitment_status"):
            self.assertEqual(self.client.get(reverse(f"dashboard:{ad}")).status_code, 405)

    def test_list_shows_answers_and_filters_by_position(self):
        r = donem()
        basvuru(r, uye("a@example.com", first_name="Teknikçi"), positions="teknik", motivation="Kod yazmayı seviyorum")
        basvuru(r, uye("b@example.com", first_name="Tasarımcı"), positions="tasarim")
        self.client.force_login(self.yonetici)
        resp = self.client.get(self.url)
        self.assertContains(resp, "Teknikçi")
        self.assertContains(resp, "Tasarımcı")
        self.assertContains(resp, "Kod yazmayı seviyorum")
        resp = self.client.get(self.url, {"pozisyon": "teknik"})
        self.assertContains(resp, "Teknikçi")
        self.assertNotContains(resp, "Tasarımcı")

    def test_status_update_returns_to_filtered_list(self):
        app = basvuru(donem(), uye())
        self.client.force_login(self.yonetici)
        geri = self.url + "?pozisyon=teknik"
        resp = self.client.post(reverse("dashboard:recruitment_status"),
                                {"app_id": app.pk, "status": "mulakat", "next": geri})
        self.assertRedirects(resp, geri, fetch_redirect_response=False)
        app.refresh_from_db()
        self.assertEqual(app.status, BoardApplication.Status.INTERVIEW)

    def test_invalid_status_ignored(self):
        app = basvuru(donem(), uye())
        self.client.force_login(self.yonetici)
        self.client.post(reverse("dashboard:recruitment_status"), {"app_id": app.pk, "status": "hacked"})
        app.refresh_from_db()
        self.assertEqual(app.status, BoardApplication.Status.PENDING)

    def test_csv_export_neutralizes_formulas(self):
        basvuru(donem(), uye(), motivation="=HYPERLINK(\"http://kotu.example\")")
        self.client.force_login(self.yonetici)
        resp = self.client.get(reverse("dashboard:recruitment_csv"))
        icerik = resp.content.decode("utf-8-sig")
        self.assertIn("Ad Soyad", icerik)
        self.assertIn("Ayşe Kaya", icerik)
        self.assertIn("'=HYPERLINK", icerik)


class PurgeBoardApplicationsTests(TestCase):
    def test_year_old_applications_purged(self):
        r = donem()
        eski = basvuru(r, uye("eski@example.com"))
        BoardApplication.objects.filter(pk=eski.pk).update(created_at=timezone.now() - timedelta(days=366))
        yeni = basvuru(r, uye("yeni@example.com"))
        call_command("purge_expired_data", stdout=StringIO())
        self.assertEqual(list(BoardApplication.objects.values_list("pk", flat=True)), [yeni.pk])
