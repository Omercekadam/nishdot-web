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
