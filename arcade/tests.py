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
