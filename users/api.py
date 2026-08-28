"""
Kullanıcı Kayıt & OTP Doğrulama API'leri
==========================================

Kayıt akışı: register (kullanıcı oluştur + OTP maili) → verify (kodu doğrula).
Tüm uçlar rate limit'lidir; verify ucunda ayrıca e-posta başına deneme
sayacı ve geçici kilit vardır (6 haneli kod brute-force edilemesin diye).

Güvenlik notları:
    - OTP karşılaştırması sabit zamanlı yapılır (hmac.compare_digest).
    - resend ucu, hesabın var olup olmadığını SIZDIRMAZ (uniform yanıt).
    - Hata detayları istemciye değil log'a yazılır.
"""

import hmac
import json
import logging
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from core.http import get_client_ip
from dashboard.models import SecurityLog

logger = logging.getLogger(__name__)

User = get_user_model()

OTP_VALIDITY_MINUTES = 15
OTP_MAX_ATTEMPTS = 5
OTP_LOCK_SECONDS = 15 * 60

GENERIC_VERIFY_ERROR = "Kod geçersiz veya süresi dolmuş. Lütfen tekrar deneyin."


def _generate_otp():
    """Kriptografik olarak güvenli 6 haneli kod üretir."""
    return f"{secrets.randbelow(900000) + 100000}"


def _log_rate_limited(request, action=None):
    SecurityLog.objects.create(
        ip_address=get_client_ip(request),
        action=action or SecurityLog.ActionType.OTP_ABUSE,
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )


def send_otp_email(user_email, otp_code, first_name):
    """OTP mailini gönderir. Başarısızlıkta exception fırlatır (çağıran karar verir)."""
    subject = 'Nishdot Web - Doğrulama Kodunuz'
    html_content = render_to_string('emails/otp_verification.html', {
        'otp_code': otp_code,
        'first_name': first_name,
    })
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)


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

    otp = _generate_otp()
    expires = timezone.now() + timedelta(minutes=OTP_VALIDITY_MINUTES)

    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            is_verified=False,
            verification_code=otp,
            code_expires_at=expires,
        )
    except Exception:
        logger.exception("Kayıt sırasında kullanıcı oluşturulamadı (email=%s)", email)
        return JsonResponse({'error': 'Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.'}, status=500)

    try:
        send_otp_email(user.email, otp, user.first_name)
    except Exception:
        logger.exception("OTP maili gönderilemedi (email=%s)", email)
        return JsonResponse(
            {'error': "Hesabınız oluşturuldu ancak doğrulama kodu gönderilemedi. "
                      "Lütfen 'Tekrar Gönder' ile yeni kod isteyin."},
            status=502,
        )

    return JsonResponse({'success': True, 'message': 'Kayıt başarılı, doğrulama kodu gönderildi.'})


@ratelimit(key='ip', rate='10/15m', block=False)
@require_POST
def verify_otp_api_view(request):
    if getattr(request, 'limited', False):
        _log_rate_limited(request)
        return JsonResponse(
            {'error': 'Çok fazla deneme yaptınız. Lütfen 15 dakika sonra tekrar deneyin.'},
            status=429,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON verisi.'}, status=400)

    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()

    if not email or not code:
        return JsonResponse({'error': 'E-posta veya kod eksik.'}, status=400)

    # E-posta başına deneme kilidi: 5 hatalı denemeden sonra 15 dakika blok.
    lock_key = f"otp_lock:{email}"
    attempts_key = f"otp_attempts:{email}"

    if cache.get(lock_key):
        return JsonResponse(
            {'error': 'Çok fazla hatalı deneme yaptınız. Lütfen 15 dakika sonra tekrar deneyin.'},
            status=429,
        )

    def _register_failed_attempt():
        attempts = (cache.get(attempts_key) or 0) + 1
        cache.set(attempts_key, attempts, timeout=OTP_LOCK_SECONDS)
        if attempts >= OTP_MAX_ATTEMPTS:
            cache.set(lock_key, True, timeout=OTP_LOCK_SECONDS)
            _log_rate_limited(request)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Hesap var/yok bilgisi sızdırılmaz — hatalı kodla aynı yanıt döner.
        _register_failed_attempt()
        return JsonResponse({'error': GENERIC_VERIFY_ERROR}, status=400)

    if user.is_verified:
        return JsonResponse({'success': True, 'message': 'Hesabınız zaten doğrulanmış. Giriş yapabilirsiniz.'})

    code_valid = (
        user.verification_code
        and hmac.compare_digest(str(user.verification_code), code)
        and user.code_expires_at
        and user.code_expires_at >= timezone.now()
    )

    if not code_valid:
        _register_failed_attempt()
        return JsonResponse({'error': GENERIC_VERIFY_ERROR}, status=400)

    user.is_verified = True
    user.verification_code = None
    user.code_expires_at = None
    user.save(update_fields=['is_verified', 'verification_code', 'code_expires_at'])

    cache.delete(lock_key)
    cache.delete(attempts_key)

    return JsonResponse({'success': True, 'message': 'Doğrulama başarılı.'})


@ratelimit(key='ip', rate='3/10m', block=False)
@require_POST
def resend_otp_api_view(request):
    if getattr(request, 'limited', False):
        _log_rate_limited(request)
        return JsonResponse(
            {'error': 'Kısa sürede çok fazla kod istediniz. Lütfen 10 dakika sonra tekrar deneyin.'},
            status=429,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON verisi.'}, status=400)

    email = (data.get('email') or '').strip().lower()
    if not email:
        return JsonResponse({'error': 'E-posta adresi gerekli.'}, status=400)

    # Uniform yanıt: hesabın var olup olmadığı bu uçtan öğrenilemez
    # (mail bombing + kullanıcı enumeration engeli).
    uniform_response = JsonResponse({
        'success': True,
        'message': 'Eğer bu e-posta ile doğrulanmamış bir hesap varsa yeni kod gönderildi.',
    })

    try:
        user = User.objects.get(email=email, is_verified=False)
    except User.DoesNotExist:
        return uniform_response

    otp = _generate_otp()
    user.verification_code = otp
    user.code_expires_at = timezone.now() + timedelta(minutes=OTP_VALIDITY_MINUTES)
    user.save(update_fields=['verification_code', 'code_expires_at'])

    try:
        send_otp_email(user.email, otp, user.first_name)
    except Exception:
        logger.exception("OTP yeniden gönderimi başarısız (email=%s)", email)

    return uniform_response
