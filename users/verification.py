"""
E-posta Doğrulama Maili
========================

Doğrulama zorunlu değildir — hiçbir işlemi kilitlemez, yalnızca uyarı bandı
gösterilir. Link 3 gün geçerlidir: mail geç gelse ya da spam'e düşse de çalışır.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def build_verification_url(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    return request.build_absolute_uri(reverse("users:verify_email", args=[uidb64, token]))


def send_verification_email(request, user):
    """Doğrulama linkini gönderir. Başarısızlıkta exception fırlatır (çağıran karar verir)."""
    context = {
        "first_name": user.first_name,
        "verify_url": build_verification_url(request, user),
    }
    subject = render_to_string("emails/verify_email_subject.txt").strip()
    text_body = render_to_string("emails/verify_email.txt", context)
    html_body = render_to_string("emails/verify_email.html", context)

    msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
