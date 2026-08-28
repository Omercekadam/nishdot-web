"""
Etkinlik / çekiliş / kişisel veri güvenlik testleri.
"""
import json
from datetime import timedelta

from django.core.cache import cache
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


class MediaConsentOptionalTests(TestCase):
    """KVKK: açık rıza özgür irade ile verilmelidir — fotoğraf/video rızası
    katılımın ŞARTI OLAMAZ. Rıza vermeyen katılımcı da başvurabilmeli."""

    def setUp(self):
        from jams.models import GameJam

        # Başvuru ucu IP başına 5/saat ile sınırlı. Rate limit sayacı cache'te
        # tutulur ve test transaction'ı ile geri alınmaz — testler arası sızmasın.
        cache.clear()

        self.event = make_event(
            Event.Status.PUBLISHED, slug="rizasiz-jam",
            event_type=Event.EventType.GAME_JAM,
        )
        self.jam = GameJam.objects.create(
            event=self.event,
            application_deadline=timezone.now() + timedelta(days=5),
            max_team_size=5,
        )
        self.url = reverse("events:apply", kwargs={"slug": self.event.slug})

    def _payload(self, **extra):
        data = {
            "kvkk_accepted": "on",
            "full_name": "Rıza Vermeyen Katılımcı",
            "national_id": "12345678950",
            "email": "rizasiz@example.com",
            "phone_number": "05001112233",
            "birth_date": "2002-01-01",
            "university": "İstanbul Nişantaşı Üniversitesi",
            "department": "Dijital Oyun Tasarımı",
            "grade": "3",
            "emergency_contact": "Veli Kişi - 05009998877",
            "team_status": "solo",
            "jam_role": "Developer",
            "experience_level": "Intermediate",
            "motivation": "Katılmak istiyorum.",
        }
        data.update(extra)
        return data

    def test_application_succeeds_without_media_consent(self):
        from jams.models import JamApplication

        resp = self.client.post(self.url, data=self._payload())
        self.assertEqual(resp.status_code, 200)

        app = JamApplication.objects.get(jam=self.jam, email="rizasiz@example.com")
        self.assertFalse(app.media_consent)   # rıza verilmedi
        self.assertTrue(app.kvkk_accepted)    # aydınlatma metni okundu

    def test_media_consent_saved_when_given(self):
        from jams.models import JamApplication

        resp = self.client.post(self.url, data=self._payload(media_consent="on"))
        self.assertEqual(resp.status_code, 200)

        app = JamApplication.objects.get(jam=self.jam, email="rizasiz@example.com")
        self.assertTrue(app.media_consent)

    def test_kvkk_still_required(self):
        """Aydınlatma metni onayı zorunlu kalmalı (rıza değil, bilgilendirmedir)."""
        from jams.models import JamApplication

        data = self._payload()
        del data["kvkk_accepted"]
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(JamApplication.objects.filter(jam=self.jam).count(), 0)


class HealthConsentTests(TestCase):
    """Sağlık verisi özel nitelikli (KVKK m.6): açık rıza yoksa hiç kaydedilmemeli."""

    def setUp(self):
        from jams.models import GameJam

        cache.clear()   # bkz. MediaConsentOptionalTests — rate limit sızıntısı

        self.event = make_event(
            Event.Status.PUBLISHED, slug="saglik-jam",
            event_type=Event.EventType.GAME_JAM,
        )
        self.jam = GameJam.objects.create(
            event=self.event,
            application_deadline=timezone.now() + timedelta(days=5),
            max_team_size=5,
        )
        self.url = reverse("events:apply", kwargs={"slug": self.event.slug})

    def _payload(self, **extra):
        data = {
            "kvkk_accepted": "on",
            "full_name": "Sağlık Testi",
            "national_id": "12345678950",
            "email": "saglik@example.com",
            "phone_number": "05001112233",
            "birth_date": "2002-01-01",
            "university": "İstanbul Nişantaşı Üniversitesi",
            "department": "Dijital Oyun Tasarımı",
            "grade": "3",
            "emergency_contact": "Veli Kişi - 05009998877",
            "team_status": "solo",
            "jam_role": "Developer",
            "experience_level": "Intermediate",
            "motivation": "Katılmak istiyorum.",
            "health_notes": "Polen alerjisi",
        }
        data.update(extra)
        return data

    def test_health_notes_discarded_without_consent(self):
        from jams.models import JamApplication

        self.client.post(self.url, data=self._payload())
        app = JamApplication.objects.get(jam=self.jam)
        self.assertEqual(app.health_notes, "")   # yazılmış olsa bile kaydedilmez
        self.assertFalse(app.health_consent)

    def test_health_notes_saved_with_consent(self):
        from jams.models import JamApplication

        self.client.post(self.url, data=self._payload(health_consent="on"))
        app = JamApplication.objects.get(jam=self.jam)
        self.assertEqual(app.health_notes, "Polen alerjisi")
        self.assertTrue(app.health_consent)

    def test_marketing_consent_recorded(self):
        from jams.models import JamApplication

        self.client.post(self.url, data=self._payload(marketing_consent="on"))
        app = JamApplication.objects.get(jam=self.jam)
        self.assertTrue(app.marketing_consent)


class NonJamConsentTests(TestCase):
    """Jam dışı etkinliklerde de rızalar kaydedilmeli (eskiden hiç yazılmıyordu)."""

    def setUp(self):
        cache.clear()
        self.event = make_event(Event.Status.PUBLISHED, slug="atolye-riza")
        self.url = reverse("events:apply", kwargs={"slug": self.event.slug})

    def _payload(self, **extra):
        data = {
            "kvkk_accepted": "on",
            "full_name": "Atölye Katılımcısı",
            "email": "atolye@example.com",
            "university": "İstanbul Nişantaşı Üniversitesi",
            "department": "Dijital Oyun Tasarımı",
            "grade": "2",
            "is_nisantasi_student": "yes",
        }
        data.update(extra)
        return data

    def test_consents_recorded(self):
        self.client.post(self.url, data=self._payload(
            media_consent="on", marketing_consent="on",
        ))
        app = EventApplication.objects.get(event=self.event)
        self.assertTrue(app.kvkk_accepted)
        self.assertTrue(app.media_consent)
        self.assertTrue(app.marketing_consent)

    def test_consents_default_false(self):
        self.client.post(self.url, data=self._payload())
        app = EventApplication.objects.get(event=self.event)
        self.assertTrue(app.kvkk_accepted)      # zorunlu, işaretlendi
        self.assertFalse(app.media_consent)     # isteğe bağlı, verilmedi
        self.assertFalse(app.marketing_consent)


class BroadcastConsentFilterTests(TestCase):
    """Genel duyuru yalnızca ticari ileti onayı verenlere gidebilmeli (6563)."""

    def test_only_consented_emails_returned(self):
        from dashboard.views import marketing_consented_emails

        event = make_event(Event.Status.PUBLISHED, slug="duyuru-etkinlik")
        EventApplication.objects.create(
            event=event, full_name="Onaylı", email="Onayli@Example.com",
            university="X", department="Y", grade="1",
            is_nisantasi_student=True, marketing_consent=True,
        )
        EventApplication.objects.create(
            event=event, full_name="Onaysız", email="onaysiz@example.com",
            university="X", department="Y", grade="1",
            is_nisantasi_student=True, marketing_consent=False,
        )

        epostalar = marketing_consented_emails()
        self.assertIn("onayli@example.com", epostalar)   # küçük harfe normalize
        self.assertNotIn("onaysiz@example.com", epostalar)


class PurgeExpiredDataTests(TestCase):
    """Saklama süresi dolan veriler otomatik silinmeli (KVKK m.7)."""

    def test_health_notes_purged_after_retention_period(self):
        from io import StringIO

        from django.core.management import call_command

        from jams.models import GameJam, JamApplication

        gecmis = timezone.now() - timedelta(days=60)
        event = Event.objects.create(
            title="Biten Jam", slug="biten-jam", description="x",
            event_type=Event.EventType.GAME_JAM, status=Event.Status.COMPLETED,
            start_date=gecmis, end_date=gecmis + timedelta(days=2), location="Kampüs",
        )
        jam = GameJam.objects.create(
            event=event, application_deadline=gecmis, max_team_size=5,
        )
        app = JamApplication.objects.create(
            jam=jam, full_name="Test", email="p@example.com",
            national_id="12345678950", jam_role="Developer", team_status="solo",
            health_notes="Astım", health_consent=True, kvkk_accepted=True,
        )

        call_command("purge_expired_data", stdout=StringIO())

        app.refresh_from_db()
        self.assertEqual(app.health_notes, "")
        self.assertFalse(app.health_consent)
        self.assertIsNotNone(app.health_purged_at)

    def test_recent_health_notes_not_purged(self):
        """Süresi dolmamış kayda dokunulmamalı."""
        from io import StringIO

        from django.core.management import call_command

        from jams.models import GameJam, JamApplication

        simdi = timezone.now()
        event = Event.objects.create(
            title="Yeni Jam", slug="yeni-jam", description="x",
            event_type=Event.EventType.GAME_JAM, status=Event.Status.PUBLISHED,
            start_date=simdi, end_date=simdi + timedelta(days=1), location="Kampüs",
        )
        jam = GameJam.objects.create(
            event=event, application_deadline=simdi, max_team_size=5,
        )
        app = JamApplication.objects.create(
            jam=jam, full_name="Test", email="y@example.com",
            national_id="12345678950", jam_role="Developer", team_status="solo",
            health_notes="Alerji", health_consent=True, kvkk_accepted=True,
        )

        call_command("purge_expired_data", stdout=StringIO())

        app.refresh_from_db()
        self.assertEqual(app.health_notes, "Alerji")


class JamApplicantLinkTests(TestCase):
    """Giriş yapmış kullanıcının jam başvurusu hesabına bağlanmalı."""

    def setUp(self):
        from jams.models import GameJam

        cache.clear()   # bkz. MediaConsentOptionalTests — rate limit sızıntısı

        self.event = make_event(
            Event.Status.PUBLISHED, slug="baglanti-jam",
            event_type=Event.EventType.GAME_JAM,
        )
        self.jam = GameJam.objects.create(
            event=self.event,
            application_deadline=timezone.now() + timedelta(days=5),
            max_team_size=5,
        )
        self.url = reverse("events:apply", kwargs={"slug": self.event.slug})
        self.user = User.objects.create_user(
            username="basvuran", email="basvuran@example.com",
            password="x", is_verified=True,
        )

    def _payload(self, **extra):
        data = {
            "kvkk_accepted": "on",
            "full_name": "Bağlantı Testi",
            "national_id": "12345678950",
            "email": "basvuran@example.com",
            "phone_number": "05001112233",
            "birth_date": "2002-01-01",
            "university": "İstanbul Nişantaşı Üniversitesi",
            "department": "Dijital Oyun Tasarımı",
            "grade": "3",
            "emergency_contact": "Veli Kişi - 05009998877",
            "team_status": "solo",
            "jam_role": "Developer",
            "experience_level": "Intermediate",
            "motivation": "Katılmak istiyorum.",
        }
        data.update(extra)
        return data

    def test_logged_in_applicant_is_linked(self):
        from jams.models import JamApplication

        self.client.force_login(self.user)
        self.client.post(self.url, data=self._payload())

        app = JamApplication.objects.get(jam=self.jam)
        self.assertEqual(app.applicant, self.user)

    def test_anonymous_applicant_stays_null(self):
        from jams.models import JamApplication

        self.client.post(self.url, data=self._payload())

        app = JamApplication.objects.get(jam=self.jam)
        self.assertIsNone(app.applicant)

    def test_dashboard_finds_application_after_email_change(self):
        """REGRESYON: e-posta değişse bile başvuru panelde görünmeli."""
        self.client.force_login(self.user)
        self.client.post(self.url, data=self._payload())

        self.user.email = "yeni-adres@example.com"
        self.user.save(update_fields=["email"])

        resp = self.client.get(reverse("users:dashboard"))
        self.assertEqual(len(resp.context["applications"]), 1)

    def test_dashboard_still_finds_application_by_email(self):
        """Hesap açılmadan yapılmış eski başvurular e-postayla eşleşmeye devam etmeli."""
        from jams.models import JamApplication

        self.client.post(self.url, data=self._payload())   # anonim başvuru
        self.client.force_login(self.user)

        resp = self.client.get(reverse("users:dashboard"))
        self.assertEqual(len(resp.context["applications"]), 1)
        self.assertIsNone(JamApplication.objects.get(jam=self.jam).applicant)


class ApplicationUniquenessTests(TestCase):
    """Tekillik view'da değil, veritabanı kısıtıyla garanti edilmeli."""

    def setUp(self):
        cache.clear()
        self.event = make_event(Event.Status.PUBLISHED, slug="tekillik-etkinlik")

    def _basvuru(self, email, national_id="", **extra):
        return EventApplication.objects.create(
            event=self.event, full_name="Test Kişi", email=email,
            university="X", department="Y", grade="1",
            is_nisantasi_student=not national_id,
            national_id=national_id, **extra,
        )

    def test_duplicate_email_rejected_by_database(self):
        from django.db import IntegrityError, transaction

        self._basvuru("ayni@example.com")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._basvuru("ayni@example.com")

    def test_duplicate_national_id_rejected_by_database(self):
        from django.db import IntegrityError, transaction

        self._basvuru("bir@example.com", national_id="12345678950")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._basvuru("iki@example.com", national_id="12345678950")

    def test_multiple_applicants_without_national_id_allowed(self):
        """REGRESYON: T.C. kimliği alınmayan öğrencilerin hash'i '' olur —
        koşullu kısıt olmazsa ikinci öğrenci kaydedilemez."""
        self._basvuru("ogrenci1@example.com")
        self._basvuru("ogrenci2@example.com")
        self.assertEqual(EventApplication.objects.filter(event=self.event).count(), 2)

    def test_same_email_allowed_on_different_events(self):
        digeri = make_event(Event.Status.PUBLISHED, slug="baska-etkinlik")
        self._basvuru("ayni@example.com")
        EventApplication.objects.create(
            event=digeri, full_name="Test Kişi", email="ayni@example.com",
            university="X", department="Y", grade="1", is_nisantasi_student=True,
        )
        self.assertEqual(EventApplication.objects.count(), 2)


class JamApplicationEmptyHashTests(TestCase):
    """REGRESYON: T.C. kimliği olmayan iki jam başvurusu çakışmamalı."""

    def setUp(self):
        from jams.models import GameJam

        self.event = make_event(
            Event.Status.PUBLISHED, slug="bos-hash-jam",
            event_type=Event.EventType.GAME_JAM,
        )
        self.jam = GameJam.objects.create(
            event=self.event,
            application_deadline=timezone.now() + timedelta(days=5),
            max_team_size=5,
        )

    def test_two_applications_without_national_id_allowed(self):
        from jams.models import JamApplication

        JamApplication.objects.create(
            jam=self.jam, full_name="Bir", email="bir@example.com",
            jam_role="Developer", team_status="solo", kvkk_accepted=True,
        )
        JamApplication.objects.create(
            jam=self.jam, full_name="İki", email="iki@example.com",
            jam_role="Artist", team_status="solo", kvkk_accepted=True,
        )
        self.assertEqual(JamApplication.objects.filter(jam=self.jam).count(), 2)


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
