"""
İletişim Formu API
==================

İletişim formu gönderimini alır, yöneticilere iletir ve gönderene otomatik
geri bildirim maili atar. Mail gönderimi request döngüsünü BLOKE ETMEZ —
arka planda daemon thread'de yapılır (eski kod async_to_sync ile senkron
çalışıp Gunicorn worker'ını iki SMTP el sıkışması boyunca kilitliyordu).

Not: Gönderim garantisi gerekiyorsa kalıcı bir kuyruk (django-rq — Redis
zaten mevcut) tercih edilmelidir. Thread'ler süreç yeniden başlarsa kaybolur.
"""

import json
import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from core.http import get_client_ip
from dashboard.models import SecurityLog

logger = logging.getLogger(__name__)

CONTACT_TARGET_EMAIL = "dijitaloyuntasarimkulubu@nisantasi.edu.tr"


def send_contact_email(full_name, sender_email, subject, message):
    """İletişim formundan gelen mesajı yöneticilere iletir."""
    email_subject = f"Nishdot İletişim Formu: {subject}"

    html_content = render_to_string('emails/contact_email.html', {
        'full_name': full_name,
        'sender_email': sender_email,
        'subject': subject,
        'message': message,
    })
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        email_subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [CONTACT_TARGET_EMAIL],
        reply_to=[sender_email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)


def send_contact_feedback_email(full_name, sender_email):
    """Kullanıcıya talebinin alındığına dair geri bildirim maili atar (2. SMTP hesabı)."""
    connection = get_connection(
        host=settings.EMAIL2_HOST,
        port=settings.EMAIL2_PORT,
        username=settings.EMAIL2_HOST_USER,
        password=settings.EMAIL2_HOST_PASSWORD,
        use_tls=True,
    )

    subject = "İletişim Talebiniz Alındı | Nishdot"
    text_content = (
        f"Merhaba {full_name},\n\n"
        "İletişim formunuz tarafımıza başarıyla ulaştı. Talebinizi inceliyor "
        "olacağız, en kısa sürede size dönüş yapacağız.\n\n"
        "İyi günler dileriz,\nNishdot Yönetim Ekibi"
    )

    html_content = render_to_string('emails/contact_feedback.html', {
        'full_name': full_name,
    })

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.EMAIL2_HOST_USER,
        [sender_email],
        connection=connection,
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)


def _dispatch_contact_emails(full_name, sender_email, subject, message):
    """İki maili de arka planda gönderir; hataları log'lar, sessizce yutmaz."""
    def worker():
        try:
            send_contact_email(full_name, sender_email, subject, message)
        except Exception:
            logger.exception("İletişim formu yönetici maili gönderilemedi")
        try:
            send_contact_feedback_email(full_name, sender_email)
        except Exception:
            logger.exception("İletişim formu geri bildirim maili gönderilemedi")

    threading.Thread(target=worker, daemon=True).start()


@ratelimit(key='ip', rate='3/h', block=False)
@require_POST
def contact_api_view(request):
    if getattr(request, 'limited', False):
        SecurityLog.objects.create(
            ip_address=get_client_ip(request),
            action=SecurityLog.ActionType.CONTACT_SPAM,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        return JsonResponse(
            {"error": "Kısa sürede çok fazla istek gönderdiniz. Lütfen 1 saat sonra tekrar deneyiniz."},
            status=429,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Geçersiz veri formatı."}, status=400)

    full_name = data.get("full_name")
    sender_email = data.get("email")
    subject = data.get("subject")
    message = data.get("message")

    if not all([full_name, sender_email, subject, message]):
        return JsonResponse({"error": "Lütfen tüm alanları doldurun."}, status=400)

    # Mail gönderimi arka planda — istek anında worker bloke olmaz.
    _dispatch_contact_emails(full_name, sender_email, subject, message)

    return JsonResponse({"message": "Mesajınız başarıyla iletildi!"})
