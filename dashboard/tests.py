"""
Yönetim paneli testleri: etkinlik oluşturucu doğrulaması, Matchmaker ve
tüm panel uçlarının yetkilendirme kontrolü.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from events.models import Event

User = get_user_model()


class EventBuilderValidationTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="builder", email="builder@example.com", password="x", is_staff=True
        )
        self.client.force_login(self.staff)
        self.url = reverse("dashboard:api_save_event")

    def _payload(self, **extra):
        data = {
            "title": "Test Atölyesi",
            "description": "<p>Açıklama</p>",
            "event_type": Event.EventType.WORKSHOP,
            "start_date": "2026-09-01T10:00",
            "end_date": "2026-09-01T18:00",
            "location": "Kampüs",
            "is_applications_open": "true",
        }
        data.update(extra)
        return data

    def test_valid_event_is_created_as_published_by_default(self):
        resp = self.client.post(self.url, data=self._payload())
        self.assertEqual(resp.status_code, 200)
        etkinlik = Event.objects.get(title="Test Atölyesi")
        self.assertEqual(etkinlik.status, Event.Status.PUBLISHED)

    def test_draft_status_is_honoured(self):
        resp = self.client.post(self.url, data=self._payload(status=Event.Status.DRAFT))
        self.assertEqual(resp.status_code, 200)
        etkinlik = Event.objects.get(title="Test Atölyesi")
        self.assertEqual(etkinlik.status, Event.Status.DRAFT)

    def test_invalid_event_type_rejected(self):
        resp = self.client.post(self.url, data=self._payload(event_type="hacker"))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Event.objects.filter(title="Test Atölyesi").exists())

    def test_invalid_status_rejected(self):
        resp = self.client.post(self.url, data=self._payload(status="yayinda-degil"))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Event.objects.filter(title="Test Atölyesi").exists())

    def test_status_can_be_changed_on_existing_event(self):
        resp = self.client.post(self.url, data=self._payload())
        etkinlik_id = json.loads(resp.content)["event_id"]

        self.client.post(self.url, data=self._payload(
            event_id=etkinlik_id, status=Event.Status.COMPLETED,
        ))
        etkinlik = Event.objects.get(id=etkinlik_id)
        self.assertEqual(etkinlik.status, Event.Status.COMPLETED)

    def test_non_staff_cannot_save_event(self):
        self.client.logout()
        resp = self.client.post(self.url, data=self._payload())
        self.assertNotEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(title="Test Atölyesi").exists())


class MatchmakerPanelTests(TestCase):
    def setUp(self):
        from datetime import timedelta

        from django.utils import timezone

        from jams.models import GameJam, JamApplication

        self.staff = User.objects.create_user(
            username="mm", email="mm@example.com", password="x", is_staff=True
        )
        simdi = timezone.now()
        self.event = Event.objects.create(
            title="Panel Jam", slug="panel-jam", description="x",
            event_type=Event.EventType.GAME_JAM, status=Event.Status.PUBLISHED,
            start_date=simdi, end_date=simdi + timedelta(days=2), location="Kampüs",
        )
        self.jam = GameJam.objects.create(
            event=self.event, application_deadline=simdi, max_team_size=4,
        )
        for ad, rol in [("Ali", "Developer"), ("Veli", "2D Artist")]:
            JamApplication.objects.create(
                jam=self.jam, full_name=ad, email=f"{ad.lower()}@example.com",
                jam_role=rol, team_status=JamApplication.TeamStatus.LOOKING,
                kvkk_accepted=True,
            )

    def test_page_requires_staff(self):
        resp = self.client.get(reverse("dashboard:matchmaker"))
        self.assertNotEqual(resp.status_code, 200)

    def test_staff_can_open_page(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("dashboard:matchmaker"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["jam"], self.jam)

    def test_run_creates_teams(self):
        from jams.models import SuggestedTeam

        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["created"], 1)
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 1)

    def test_non_staff_cannot_run(self):
        from jams.models import SuggestedTeam

        resp = self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 0)

    def test_team_status_can_be_approved(self):
        from jams.models import SuggestedTeam

        self.client.force_login(self.staff)
        self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        takim = SuggestedTeam.objects.get(jam=self.jam)

        resp = self.client.post(
            reverse("dashboard:api_update_team_status"),
            data=json.dumps({"team_id": takim.id, "status": "approved"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        takim.refresh_from_db()
        self.assertEqual(takim.status, SuggestedTeam.Status.APPROVED)
        self.assertEqual(takim.reviewed_by, self.staff)
        self.assertIsNotNone(takim.reviewed_at)

    def test_invalid_team_status_rejected(self):
        from jams.models import SuggestedTeam

        self.client.force_login(self.staff)
        self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        takim = SuggestedTeam.objects.get(jam=self.jam)

        resp = self.client.post(
            reverse("dashboard:api_update_team_status"),
            data=json.dumps({"team_id": takim.id, "status": "hacker"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        takim.refresh_from_db()
        self.assertEqual(takim.status, SuggestedTeam.Status.PENDING)

    def test_reset_removes_teams(self):
        from jams.models import SuggestedTeam

        self.client.force_login(self.staff)
        self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )

        resp = self.client.post(
            reverse("dashboard:api_reset_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 0)


class DashboardAuthorizationTests(TestCase):
    """
    Panelin TÜM uçları staff yetkisi istemeli.

    Bu test URL tablosunu gezerek çalışır — yeni bir uç eklendiğinde ayrıca
    test yazmak gerekmez, dekoratör unutulursa burada patlar.
    """

    # Bilerek tüm GİRİŞ YAPMIŞ kullanıcılara açık olan uçlar. Üye kendi
    # panelindeki duyuruyu gizleyebilmelidir; bu yüzden üye testinden muaftır.
    # Anonim testten muaf DEĞİLDİR (@login_required korumalı).
    UYEYE_ACIK = {"api_dismiss_announcement"}

    def setUp(self):
        self.uye = User.objects.create_user(
            username="sirandan", email="sirandan@example.com", password="x"
        )

    def _rotalar(self):
        """dashboard/urls.py içindeki her rotayı (ad, url) olarak üretir."""
        from django.urls import NoReverseMatch

        from dashboard import urls as dashboard_urls

        # Parametre alan rotalar için sahte değer yeterli: yetki kontrolü
        # get_object_or_404'ten ÖNCE çalışır, nesnenin var olması gerekmez.
        aday_kwargs = ({}, {"pk": 1}, {"announcement_id": 1})

        for pattern in dashboard_urls.urlpatterns:
            ad = pattern.name
            url = None
            for kwargs in aday_kwargs:
                try:
                    url = reverse(f"dashboard:{ad}", kwargs=kwargs)
                    break
                except NoReverseMatch:
                    continue
            self.assertIsNotNone(url, f"{ad} için URL üretilemedi — aday_kwargs'a ekleyin")
            yield ad, url

    def _erisilemez_olmali(self, ad, url, kim):
        get = self.client.get(url)
        post = self.client.post(url, data="{}", content_type="application/json")
        self.assertNotEqual(get.status_code, 200, f"{ad}: {kim} GET ile 200 aldı")
        self.assertNotEqual(post.status_code, 200, f"{ad}: {kim} POST ile 200 aldı")

    def test_anonymous_cannot_reach_any_endpoint(self):
        for ad, url in self._rotalar():
            with self.subTest(uc=ad):
                self._erisilemez_olmali(ad, url, "anonim")

    def test_regular_member_cannot_reach_any_endpoint(self):
        self.client.force_login(self.uye)
        for ad, url in self._rotalar():
            if ad in self.UYEYE_ACIK:
                continue
            with self.subTest(uc=ad):
                self._erisilemez_olmali(ad, url, "üye")


class StorageManagerAuthorizationTests(TestCase):
    """Depolama yöneticisi staff değil, SUPERUSER ister (dosya siler)."""

    def setUp(self):
        self.staff = User.objects.create_user(
            username="sadecestaff", email="s@example.com", password="x", is_staff=True
        )

    def test_staff_without_superuser_cannot_open_storage_manager(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("dashboard:storage_manager"))
        self.assertNotEqual(resp.status_code, 200)

    def test_staff_without_superuser_cannot_delete_files(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse("dashboard:api_storage_delete"),
            data=json.dumps({"path": "events/covers/x.webp"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
