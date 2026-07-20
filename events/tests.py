"""
Etkinlik / çekiliş / kişisel veri güvenlik testleri.
"""
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
