"""
Yılan oyunu: model, liderlik tablosu, API, sahiplenme ve temizlik testleri.
"""
import json
import secrets
import time
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from arcade.models import Competition, GameRun
from arcade.services import display_name, leaderboard
from dashboard.models import SecurityLog

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
