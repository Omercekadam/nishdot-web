import json
from django.http import JsonResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.views.decorators.http import require_POST
from asgiref.sync import sync_to_async

@sync_to_async
def send_contact_email(full_name, sender_email, subject, message):
    """İletişim formundan gelen mesajı yöneticilere iletir."""
    email_subject = f"Nishdot İletişim Formu: {subject}"
    target_email = "dijitaloyuntasarimkulubu@nisantasi.edu.tr"
    
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
        [target_email],
        reply_to=[sender_email]
    )
    msg.attach_alternative(html_content, "text/html")
    
    try:
        msg.send(fail_silently=False)
        print(f"İletişim formu e-postası {target_email} adresine başarıyla gönderildi!")
    except Exception as e:
        print(f"İLETİŞİM FORMU MAİL GÖNDERME HATASI: {e}")

import os
from django.core.mail import get_connection

@sync_to_async
def send_contact_feedback_email(full_name, sender_email):
    """Kullanıcıya talebinin alındığına dair geri bildirim maili atar."""
    try:
        connection = get_connection(
            host=os.getenv('SMTP2_SERVER', 'smtp.gmail.com'),
            port=int(os.getenv('SMTP2_PORT', 587)),
            username=os.getenv('SMTP2_USERNAME'),
            password=os.getenv('SMTP2_PASSWORD'),
            use_tls=True
        )
        
        subject = "İletişim Talebiniz Alındı | Nishdot"
        text_content = f"Merhaba {full_name},\n\nİletişim formunuz tarafımıza başarıyla ulaştı. Talebinizi inceliyor olacağız, en kısa sürede size dönüş yapacağız.\n\nİyi günler dileriz,\nNishdot Yönetim Ekibi"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 10px; overflow: hidden;">
            <div style="background-color: #eb596d; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">Talebiniz Alındı</h2>
            </div>
            <div style="padding: 20px; color: #333; line-height: 1.6;">
                <p>Merhaba <strong>{full_name}</strong>,</p>
                <p>Web sitemiz üzerinden gönderdiğiniz iletişim formu tarafımıza başarıyla ulaşmıştır. Talebinizi inceliyoruz, en kısa sürede sizinle iletişime geçeceğiz.</p>
                <p>İlginiz için teşekkür ederiz.</p>
                <br>
                <p>Sevgilerle,<br><strong>Nishdot Yönetim Ekibi</strong></p>
            </div>
        </div>
        """
        
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            os.getenv('SMTP2_USERNAME'),
            [sender_email],
            connection=connection
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        print(f"Geri bildirim e-postası {sender_email} adresine başarıyla gönderildi!")
    except Exception as e:
        print(f"GERİ BİLDİRİM MAİL GÖNDERME HATASI: {e}")

from django_ratelimit.decorators import ratelimit
from dashboard.models import SecurityLog

from asgiref.sync import async_to_sync

@ratelimit(key='ip', rate='3/h', block=False)
@require_POST
def contact_api_view(request):
    if getattr(request, 'limited', False):
        def create_log():
            SecurityLog.objects.create(
                ip_address=request.META.get('REMOTE_ADDR', ''),
                action=SecurityLog.ActionType.CONTACT_SPAM,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        create_log()
        return JsonResponse({"error": "Kısa sürede çok fazla istek gönderdiniz. Lütfen 1 saat sonra tekrar deneyiniz."}, status=429)

    try:
        data = json.loads(request.body)
        
        full_name = data.get("full_name")
        sender_email = data.get("email")
        subject = data.get("subject")
        message = data.get("message")
        
        if not all([full_name, sender_email, subject, message]):
            return JsonResponse({"error": "Lütfen tüm alanları doldurun."}, status=400)
            
        # Arka planda mail gönderimi (sync_to_async wrapper olan fonksiyonu async_to_sync ile çağırıyoruz)
        async_to_sync(send_contact_email)(full_name, sender_email, subject, message)
        
        # Kullanıcıya otomatik geri bildirim maili gönderimi
        async_to_sync(send_contact_feedback_email)(full_name, sender_email)
        
        return JsonResponse({"message": "Mesajınız başarıyla iletildi!"})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Geçersiz veri formatı."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
