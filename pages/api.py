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

@require_POST
async def contact_api_view(request):
    try:
        data = json.loads(request.body)
        
        full_name = data.get("full_name")
        sender_email = data.get("email")
        subject = data.get("subject")
        message = data.get("message")
        
        if not all([full_name, sender_email, subject, message]):
            return JsonResponse({"error": "Lütfen tüm alanları doldurun."}, status=400)
            
        # Arka planda asenkron mail gönderimi
        await send_contact_email(full_name, sender_email, subject, message)
        
        return JsonResponse({"message": "Mesajınız başarıyla iletildi!"})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Geçersiz veri formatı."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
