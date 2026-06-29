from django.views.generic import DetailView, TemplateView
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from .models import Event

class EventDetailView(DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

class EventApplyWizardView(TemplateView):
    template_name = "events/event_apply.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = get_object_or_404(Event, slug=self.kwargs['slug'])
        return context

    def post(self, request, *args, **kwargs):
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        
        # Etkinliğe bağlı GameJam objesini al, yoksa form submit edilemez
        # (Sadece Game Jam etkinlikleri için application açtık şu anlık)
        if not hasattr(event, 'jam'):
            return self.render_to_response(self.get_context_data(error="Bu etkinlik bir Game Jam değil veya başvurulara kapalı."))
            
        jam = event.jam
        
        # Formdan gelen verileri al
        from jams.models import JamApplication
        
        email = request.POST.get('email')
        national_id = request.POST.get('national_id')
        
        # Mükerrer başvuru kontrolleri (E-posta ve T.C. Kimlik)
        if JamApplication.objects.filter(jam=jam, email=email).exists():
            error_msg = "Bu e-posta adresiyle daha önce bir başvuru yapılmış. Başvurunuzda bir değişiklik yapmak istiyorsanız veya bir sorun olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
            return self.render_to_response(self.get_context_data(error=error_msg))
            
        if JamApplication.objects.filter(jam=jam, national_id=national_id).exists():
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
                kvkk_accepted=request.POST.get('kvkk_accepted') == 'on'
            )
            return self.render_to_response(self.get_context_data(success=True))
        except IntegrityError:
            error_msg = "Sisteme kaydınız sırasında veritabanı kısıtlamasına takıldınız (Zaten kayıtlısınız). Bir sorun olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
            return self.render_to_response(self.get_context_data(error=error_msg))
        except Exception as e:
            # Diğer beklenmeyen hatalar için
            error_msg = "Başvurunuz alınırken beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
            return self.render_to_response(self.get_context_data(error=error_msg))
