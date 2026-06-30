import json
import random
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from asgiref.sync import sync_to_async

User = get_user_model()

@sync_to_async
def send_otp_email(user_email, otp_code, first_name):
    """Asenkron olarak OTP maili gönderen fonksiyon."""
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
        [user_email]
    )
    msg.attach_alternative(html_content, "text/html")
    try:
        msg.send(fail_silently=False)
        print(f"[{user_email}] adresine OTP maili başarıyla gönderildi!")
    except Exception as e:
        print(f"MAIL GÖNDERME HATASI: {e}")

@sync_to_async
def create_user(data):
    # Kullanıcı kontrolü
    if User.objects.filter(email=data['email']).exists():
        return None, "Bu e-posta adresi zaten kullanılıyor."
    
    otp = str(random.randint(100000, 999999))
    expires = timezone.now() + timedelta(minutes=15)
    
    # Yeni kullanıcı oluştur
    user = User.objects.create_user(
        username=data['email'], # Username olarak email kullanıyoruz
        email=data['email'],
        password=data['password'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        is_verified=False,
        verification_code=otp,
        code_expires_at=expires
    )
    return user, otp

async def register_api_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Yalnızca POST istekleri kabul edilir.'}, status=405)
    
    try:
        data = json.loads(request.body)
        if not all([data.get('email'), data.get('password'), data.get('first_name'), data.get('last_name')]):
            return JsonResponse({'error': 'Eksik bilgi girdiniz.'}, status=400)
            
        user, otp_or_error = await create_user(data)
        if not user:
            return JsonResponse({'error': otp_or_error}, status=400)
            
        # Asenkron olarak maili gönder
        await send_otp_email(user.email, otp_or_error, user.first_name)
        
        return JsonResponse({'success': True, 'message': 'Kayıt başarılı, doğrulama kodu gönderildi.'})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON verisi.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@sync_to_async
def verify_user(email, code):
    try:
        user = User.objects.get(email=email)
        if user.is_verified:
            return True, "Kullanıcı zaten doğrulanmış.", user
            
        if user.verification_code != code:
            return False, "Geçersiz doğrulama kodu.", None
            
        if user.code_expires_at < timezone.now():
            return False, "Doğrulama kodunun süresi dolmuş. Lütfen yeni kod isteyin.", None
            
        # Doğrulama başarılı
        user.is_verified = True
        user.verification_code = None
        user.code_expires_at = None
        user.save()
        return True, "Doğrulama başarılı.", user
    except User.DoesNotExist:
        return False, "Kullanıcı bulunamadı.", None

async def verify_otp_api_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Yalnızca POST istekleri kabul edilir.'}, status=405)
        
    try:
        data = json.loads(request.body)
        email = data.get('email')
        code = data.get('code')
        
        if not email or not code:
            return JsonResponse({'error': 'E-posta veya kod eksik.'}, status=400)
            
        is_success, message, user = await verify_user(email, code)
        
        if is_success:
            return JsonResponse({'success': True, 'message': message})
        else:
            return JsonResponse({'error': message}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON verisi.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
