"""
Yılan oyunu: model, liderlik tablosu, API, sahiplenme ve temizlik testleri.
"""
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from arcade.models import Competition, GameRun
from arcade.services import display_name, leaderboard

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
