from django.views.generic import DetailView, TemplateView
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from .models import Event

class EventDetailView(DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from dashboard.models import SecurityLog

@method_decorator(ratelimit(key='ip', rate='5/h', block=False), name='post')
class EventApplyWizardView(TemplateView):
    template_name = "events/event_apply.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = get_object_or_404(Event, slug=self.kwargs['slug'])
        return context

    def get(self, request, *args, **kwargs):
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        if not event.is_applications_open:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Bu etkinliğin başvuruları şu an kapalıdır.")
            return redirect('events:detail', slug=event.slug)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if getattr(request, 'limited', False):
            SecurityLog.objects.create(
                ip_address=request.META.get('REMOTE_ADDR', ''),
                action=SecurityLog.ActionType.APPLY_SPAM,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return self.render_to_response(self.get_context_data(error="Kısa sürede çok fazla istek gönderdiniz. Lütfen 1 saat sonra tekrar deneyiniz."))

        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        
        if not event.is_applications_open:
            return self.render_to_response(self.get_context_data(error="Bu etkinliğin başvuruları şu an kapalıdır."))
            
        email = request.POST.get('email')
        
        # KVKK Kontrolü (Her iki form türü için de ortak)
        if request.POST.get('kvkk_accepted') != 'on':
            return self.render_to_response(self.get_context_data(error="KVKK Aydınlatma Metni'ni okuyup onaylamanız zorunludur."))

        if event.event_type == Event.EventType.GAME_JAM:
            if not hasattr(event, 'jam'):
                return self.render_to_response(self.get_context_data(error="Bu etkinlik bir Game Jam değil."))
                
            jam = event.jam
            from jams.models import JamApplication
            national_id = request.POST.get('national_id')
            
            if request.POST.get('media_consent') != 'on':
                return self.render_to_response(self.get_context_data(error="Etkinlik kuralları gereği fotoğraf ve video kullanım izni (Açık Rıza) vermeniz zorunludur."))
            
            if JamApplication.objects.filter(jam=jam, email=email).exists():
                error_msg = "Bu e-posta adresiyle daha önce bir başvuru yapılmış. Başvurunuzda bir değişiklik yapmak istiyorsanız veya bir sorun olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
                return self.render_to_response(self.get_context_data(error=error_msg))
                
            import hashlib
            national_id_hash = hashlib.sha256(national_id.encode('utf-8')).hexdigest()
            if JamApplication.objects.filter(jam=jam, national_id_hash=national_id_hash).exists():
                error_msg = "Bu T.C. Kimlik numarasıyla daha önce bir başvuru yapılmış. Bir hata olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
                return self.render_to_response(self.get_context_data(error=error_msg))
            
            try:
                JamApplication.objects.create(
                    jam=jam,
                    full_name=request.POST.get('full_name'),
                    national_id=national_id,
                    email=email,
                    phone_number=request.POST.get('phone_number'),
                    birth_date=request.POST.get('birth_date'),
                    university=request.POST.get('university'),
                    department=request.POST.get('department'),
                    grade=request.POST.get('grade'),
                    emergency_contact=request.POST.get('emergency_contact'),
                    health_notes=request.POST.get('health_notes', ''),
                    
                    team_status=request.POST.get('team_status'),
                    team_name=request.POST.get('team_name', ''),
                    jam_role=request.POST.get('jam_role'),
                    experience_level=request.POST.get('experience_level'),
                    portfolio_url=request.POST.get('portfolio_url', ''),
                    previous_jams=request.POST.get('previous_jams', ''),
                    
                    motivation=request.POST.get('motivation', ''),
                    additional_notes=request.POST.get('additional_notes', ''),
                    kvkk_accepted=True,
                    media_consent=True
                )
                return self.render_to_response(self.get_context_data(success=True))
            except IntegrityError:
                error_msg = "Sisteme kaydınız sırasında veritabanı kısıtlamasına takıldınız (Zaten kayıtlısınız). Bir sorun olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
                return self.render_to_response(self.get_context_data(error=error_msg))
            except Exception as e:
                error_msg = "Başvurunuz alınırken beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
                return self.render_to_response(self.get_context_data(error=error_msg))
                
        else:
            # Game Jam HARİCİ Etkinlikler (Workshop, Konuşma vb.)
            from .models import EventApplication
            
            if EventApplication.objects.filter(event=event, email=email).exists():
                error_msg = "Bu e-posta adresiyle bu etkinliğe daha önce kayıt oldunuz."
                return self.render_to_response(self.get_context_data(error=error_msg))
                
            is_nisantasi_student = request.POST.get('is_nisantasi_student') == 'yes'
            national_id = request.POST.get('national_id', '') if not is_nisantasi_student else ''
            
            if not is_nisantasi_student and not national_id:
                return self.render_to_response(self.get_context_data(error="Nişantaşı Üniversitesi dışından katılan misafirlerimiz kampüs güvenliği için T.C. Kimlik numarasını girmek zorundadır."))
                
            import hashlib
            national_id_hash = ''
            if national_id:
                national_id_hash = hashlib.sha256(national_id.encode('utf-8')).hexdigest()
                if EventApplication.objects.filter(event=event, national_id_hash=national_id_hash).exists():
                    return self.render_to_response(self.get_context_data(error="Bu T.C. Kimlik numarasıyla daha önce bir başvuru yapılmış."))

            try:
                applicant = request.user if request.user.is_authenticated else None
                EventApplication.objects.create(
                    event=event,
                    applicant=applicant,
                    full_name=request.POST.get('full_name'),
                    email=email,
                    university=request.POST.get('university', ''),
                    department=request.POST.get('department', ''),
                    grade=request.POST.get('grade', ''),
                    is_nisantasi_student=is_nisantasi_student,
                    national_id=national_id,
                    national_id_hash=national_id_hash
                )
                return self.render_to_response(self.get_context_data(success=True))
            except Exception as e:
                error_msg = "Başvurunuz alınırken beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
                return self.render_to_response(self.get_context_data(error=error_msg))

from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Raffle, RaffleParticipant

class RaffleJoinView(LoginRequiredMixin, TemplateView):
    template_name = "events/raffle_join.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        raffle = get_object_or_404(Raffle, secret_id=self.kwargs['secret_id'])
        context['raffle'] = raffle
        
        if not raffle.is_active:
            context['status'] = "closed"
            return context

        # Çekilişe katılımcı olarak ekle
        participant, created = RaffleParticipant.objects.get_or_create(
            raffle=raffle,
            user=self.request.user
        )
        
        if created:
            context['status'] = "success"
        else:
            context['status'] = "already_joined"
            
        return context
