"""
Kullanıcı Kayıt API'si
=======================

Akış: register → kullanıcı oluştur → anında oturum aç → doğrulama linkini maille.
E-posta doğrulaması hiçbir işlemi kilitlemez; doğrulanmamış hesap yalnızca
hatırlatma bandını görür (templates/components/verify_banner.html).

Mail gönderilemezse kayıt yine başarılıdır: hata loglanır, kullanıcı banttaki
"Tekrar gönder" ile yeni link ister. (Eskiden 15 dk'lık OTP kodu vardı; mail
geç gelince ya da spam'e düşünce kişi hesabına hiç giremiyordu.)
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from core.http import get_client_ip, safe_redirect_url
from dashboard.models import SecurityLog

from .verification import send_verification_email

logger = logging.getLogger(__name__)

User = get_user_model()


def _log_rate_limited(request, action=None):
    SecurityLog.objects.create(
        ip_address=get_client_ip(request),
        action=action or SecurityLog.ActionType.OTP_ABUSE,
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )


@ratelimit(key='ip', rate='3/h', block=False)
@require_POST
def register_api_view(request):
    if getattr(request, 'limited', False):
        _log_rate_limited(request, SecurityLog.ActionType.REGISTER_SPAM)
        return JsonResponse(
            {'error': 'Kısa sürede çok fazla istek gönderdiniz. Lütfen 1 saat sonra tekrar deneyiniz.'},
            status=429,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON verisi.'}, status=400)

    if not all([data.get('email'), data.get('password'), data.get('first_name'), data.get('last_name')]):
        return JsonResponse({'error': 'Eksik bilgi girdiniz.'}, status=400)

    email = data['email'].strip().lower()

    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Bu e-posta adresi zaten kullanılıyor.'}, status=400)

    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            is_verified=False,
        )
    except Exception:
        logger.exception("Kayıt sırasında kullanıcı oluşturulamadı (email=%s)", email)
        return JsonResponse({'error': 'Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.'}, status=500)

    # Tek kimlik doğrulama backend'i (ModelBackend) olduğu için backend argümanı gerekmez.
    # login(), oturumdaki veriyi korur: üye olmadan oynanan oyun skorları
    # (arcade) bu sayede yeni hesaba bağlanır.
    login(request, user)
    messages.success(request, f"Hoş geldin {user.first_name}! Hesabın oluşturuldu.")

    try:
        send_verification_email(request, user)
    except Exception:
        # Kayıt başarısız sayılmaz: kullanıcı uyarı bandından yeni link isteyebilir.
        logger.exception("Doğrulama maili gönderilemedi (email=%s)", email)

    return JsonResponse({
        'success': True,
        'redirect': safe_redirect_url(request, data.get('next')),
    })
