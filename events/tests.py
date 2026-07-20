"""
Etkinlik / çekiliş / kişisel veri güvenlik testleri.
"""
import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from events.models import Event, EventApplication, Raffle, RaffleParticipant
from core.crypto import is_encrypted

User = get_user_model()


def make_event(status, slug="etkinlik", event_type=Event.EventType.WORKSHOP):
    now = timezone.now()
    return Event.objects.create(
        title="Test Etkinlik", slug=slug, description="Açıklama",
        event_type=event_type, status=status,
        start_date=now, end_date=now + timedelta(hours=2),
        location="Kampüs",
    )


class DraftVisibilityTests(TestCase):
    def test_draft_event_hidden_from_anonymous(self):
        make_event(Event.Status.DRAFT, slug="gizli-taslak")
        resp = self.client.get(reverse("events:detail", kwargs={"slug": "gizli-taslak"}))
        self.assertEqual(resp.status_code, 404)

    def test_published_event_visible(self):
        make_event(Event.Status.PUBLISHED, slug="acik-etkinlik")
        resp = self.client.get(reverse("events:detail", kwargs={"slug": "acik-etkinlik"}))
        self.assertEqual(resp.status_code, 200)

    def test_staff_can_see_draft(self):
        make_event(Event.Status.DRAFT, slug="taslak2")
        staff = User.objects.create_user(
            username="staff", email="staff@example.com", password="x", is_staff=True
        )
        self.client.force_login(staff)
        resp = self.client.get(reverse("events:detail", kwargs={"slug": "taslak2"}))
        self.assertEqual(resp.status_code, 200)


class RaffleJoinTests(TestCase):
    def setUp(self):
        self.event = make_event(Event.Status.PUBLISHED, slug="cekilis-etkinlik")
        self.raffle = Raffle.objects.create(event=self.event, title="Çekiliş", is_active=True)
        self.user = User.objects.create_user(
            username="katilimci", email="k@example.com", password="x"
        )
        self.url = reverse("events:raffle_join", kwargs={"secret_id": self.raffle.secret_id})

    def test_get_does_not_join(self):
        """REGRESYON: GET isteği çekilişe KATMAMALI (yan etkisiz)."""
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(RaffleParticipant.objects.filter(raffle=self.raffle).count(), 0)

    def test_post_joins(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(RaffleParticipant.objects.filter(raffle=self.raffle, user=self.user).count(), 1)

    def test_login_required(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)  # login'e yönlendirir


class NationalIdEncryptionTests(TestCase):
    def test_event_application_encrypts_national_id(self):
        event = make_event(Event.Status.PUBLISHED, slug="basvuru-etkinlik")
        app = EventApplication.objects.create(
            event=event, full_name="Misafir Kişi", email="m@example.com",
            university="X", department="Y", grade="1",
            is_nisantasi_student=False, national_id="12345678950",
        )
        app.refresh_from_db()
        # Ham değer veritabanında şifreli olmalı (düz metin DEĞİL)
        self.assertTrue(is_encrypted(app.national_id))
        self.assertNotIn("12345678950", app.national_id)
        # Çözülebilmeli ve hash üretilmiş olmalı
        self.assertEqual(app.decrypted_national_id, "12345678950")
        self.assertTrue(app.national_id_hash)

    def test_invalid_national_id_rejected(self):
        event = make_event(Event.Status.PUBLISHED, slug="gecersiz-tc")
        with self.assertRaises(ValueError):
            EventApplication.objects.create(
                event=event, full_name="X", email="z@example.com",
                university="X", department="Y", grade="1",
                is_nisantasi_student=False, national_id="123",  # geçersiz
            )


class PinnedEventOrderingTests(TestCase):
    """Ana sayfada sabitlenmiş etkinlikler tarihten bağımsız en üstte gösterilmeli."""

    def test_pinned_event_comes_first_even_if_older(self):
        from pages.views import HomePageView

        make_event(Event.Status.PUBLISHED, slug="yeni-etkinlik")  # daha yeni start_date (varsayılan: şimdi)
        old = Event.objects.create(
            title="Eski Sabitlenmiş", slug="eski-sabitlenmis",
            description="x", event_type=Event.EventType.WORKSHOP,
            status=Event.Status.PUBLISHED,
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now() - timedelta(days=30) + timedelta(hours=2),
            location="Kampüs", is_pinned=True,
        )

        events = list(HomePageView().get_context_data()['events'])
        self.assertEqual(events[0].id, old.id)


class DashboardPinToggleTests(TestCase):
    def setUp(self):
        self.event = make_event(Event.Status.PUBLISHED, slug="pin-testi")
        self.staff = User.objects.create_user(
            username="staff2", email="staff2@example.com", password="x", is_staff=True
        )
        self.url = reverse("dashboard:api_toggle_event_pin")

    def test_staff_can_toggle_pin(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            self.url,
            data=json.dumps({"event_id": self.event.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.event.refresh_from_db()
        self.assertTrue(self.event.is_pinned)

    def test_non_staff_cannot_toggle_pin(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"event_id": self.event.id}),
            content_type="application/json",
        )
        self.assertNotEqual(resp.status_code, 200)
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_pinned)


class ManualRaffleParticipantTests(TestCase):
    """Yönetici QR çekilişine elle (hesabı olmayan) misafir ekleyebilmeli."""

    def setUp(self):
        self.event = make_event(Event.Status.PUBLISHED, slug="misafir-cekilis")
        self.raffle = Raffle.objects.create(event=self.event, title="Çekiliş", is_active=True)
        self.staff = User.objects.create_user(
            username="staff3", email="staff3@example.com", password="x", is_staff=True
        )
        self.add_url = reverse("dashboard:api_raffle_add_participant", kwargs={"pk": self.raffle.id})

    def test_add_guest_participant(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            self.add_url,
            data=json.dumps({"name": "Misafir Ahmet"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        participant = RaffleParticipant.objects.get(raffle=self.raffle)
        self.assertIsNone(participant.user)
        self.assertEqual(participant.display_name, "Misafir Ahmet")

    def test_multiple_guests_allowed(self):
        """user=NULL olan iki misafir kaydı unique_together('raffle','user')'a takılmamalı."""
        self.client.force_login(self.staff)
        self.client.post(self.add_url, data=json.dumps({"name": "Misafir 1"}), content_type="application/json")
        resp2 = self.client.post(self.add_url, data=json.dumps({"name": "Misafir 2"}), content_type="application/json")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(RaffleParticipant.objects.filter(raffle=self.raffle).count(), 2)

    def test_empty_name_rejected(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            self.add_url,
            data=json.dumps({"name": "   "}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(RaffleParticipant.objects.filter(raffle=self.raffle).count(), 0)

    def test_pick_winner_shows_guest_name(self):
        RaffleParticipant.objects.create(raffle=self.raffle, guest_name="Tek Misafir")
        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse("dashboard:api_raffle_pick_winner", kwargs={"pk": self.raffle.id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["winner"], "Tek Misafir")
