"""
Sahipsiz Skorların Sahiplenilmesi
==================================

Üye olmadan oynanan skorların kimlikleri oturumda (PENDING_SESSION_KEY)
tutulur. Aynı tarayıcıdan giriş ya da kayıt yapılınca (kayıt da login()
çağırır) son 24 saatteki sahipsiz skorlar hesaba bağlanır.

Django'nun login()'i anonim oturumdan girişte oturum anahtarını yeniler
(cycle_key) ama verisini korur; liste girişten sonra da okunabilir.
"""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

from .models import PENDING_SESSION_KEY, UNCLAIMED_TTL, GameRun


@receiver(user_logged_in, dispatch_uid="arcade_claim_pending_runs")
def claim_pending_runs(sender, request, user, **kwargs):
    session = getattr(request, "session", None)
    if session is None:
        return
    bekleyen = session.pop(PENDING_SESSION_KEY, None)
    if not bekleyen:
        return
    # user__isnull: oturuma başkasının kaydı yazılmış olsa bile yalnızca sahipsizler bağlanır.
    GameRun.objects.filter(
        pk__in=bekleyen,
        user__isnull=True,
        created_at__gte=timezone.now() - UNCLAIMED_TTL,
    ).update(user=user)
