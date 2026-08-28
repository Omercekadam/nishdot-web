from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, TemplateView
from django_ratelimit.decorators import ratelimit

from core.crypto import hash_national_id, is_valid_national_id
from core.http import get_client_ip
from dashboard.models import SecurityLog
from .models import Event, Raffle, RaffleParticipant


def visible_events_for(user):
    """
    Herkese açık sayfalarda gösterilebilecek etkinlikler.
    Taslak/iptal edilmiş etkinlikleri yalnızca staff görebilir —
    slug tahmin eden anonim ziyaretçilere sızmaz.
    """
    qs = Event.objects.all()
    if user.is_authenticated and user.is_staff:
        return qs
    return qs.filter(status__in=[Event.Status.PUBLISHED, Event.Status.COMPLETED])


class EventDetailView(DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return visible_events_for(self.request.user)


@method_decorator(ratelimit(key='ip', rate='5/h', block=False), name='post')
class EventApplyWizardView(TemplateView):
    template_name = "events/event_apply.html"

    def get_event(self):
        return get_object_or_404(visible_events_for(self.request.user), slug=self.kwargs['slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.get_event()
        return context

    def get(self, request, *args, **kwargs):
        event = self.get_event()
        if not event.is_applications_open:
            messages.error(request, "Bu etkinliğin başvuruları şu an kapalıdır.")
            return redirect('events:detail', slug=event.slug)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if getattr(request, 'limited', False):
            SecurityLog.objects.create(
                ip_address=get_client_ip(request),
                action=SecurityLog.ActionType.APPLY_SPAM,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return self.render_to_response(self.get_context_data(error="Kısa sürede çok fazla istek gönderdiniz. Lütfen 1 saat sonra tekrar deneyiniz."))

        event = self.get_event()

        if not event.is_applications_open:
            return self.render_to_response(self.get_context_data(error="Bu etkinliğin başvuruları şu an kapalıdır."))

        email = (request.POST.get('email') or '').strip().lower()

        # KVKK Kontrolü (Her iki form türü için de ortak)
        if request.POST.get('kvkk_accepted') != 'on':
            return self.render_to_response(self.get_context_data(error="KVKK Aydınlatma Metni'ni okuyup onaylamanız zorunludur."))

        if event.event_type == Event.EventType.GAME_JAM:
            if not hasattr(event, 'jam'):
                return self.render_to_response(self.get_context_data(error="Bu etkinlik bir Game Jam değil."))

            jam = event.jam
            from jams.models import JamApplication
            national_id = (request.POST.get('national_id') or '').strip()

            # Eksik/biçimsiz TC numarası eskiden 500 hatasına yol açıyordu —
            # hash'lemeden ÖNCE doğrulanmalı.
            if not is_valid_national_id(national_id):
                return self.render_to_response(self.get_context_data(error="Geçerli bir T.C. Kimlik Numarası girmeniz zorunludur (11 haneli)."))

            # Açık rızalar ZORUNLU DEĞİLDİR. KVKK'da açık rıza "özgür irade" ile
            # verilmelidir; katılımı rızaya bağlamak rızayı sakatlar.
            media_consent = request.POST.get('media_consent') == 'on'
            health_consent = request.POST.get('health_consent') == 'on'
            marketing_consent = request.POST.get('marketing_consent') == 'on'

            # Sağlık verisi özel nitelikli veridir (KVKK m.6): açık rıza yoksa
            # kullanıcı forma bir şey yazmış olsa bile KAYDEDİLMEZ.
            health_notes = request.POST.get('health_notes', '') if health_consent else ''

            if JamApplication.objects.filter(jam=jam, email=email).exists():
                error_msg = "Bu e-posta adresiyle daha önce bir başvuru yapılmış. Başvurunuzda bir değişiklik yapmak istiyorsanız veya bir sorun olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
                return self.render_to_response(self.get_context_data(error=error_msg))

            national_id_hash = hash_national_id(national_id)
            if JamApplication.objects.filter(jam=jam, national_id_hash=national_id_hash).exists():
                error_msg = "Bu T.C. Kimlik numarasıyla daha önce bir başvuru yapılmış. Bir hata olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
                return self.render_to_response(self.get_context_data(error=error_msg))

            try:
                JamApplication.objects.create(
                    jam=jam,
                    applicant=request.user if request.user.is_authenticated else None,
                    full_name=request.POST.get('full_name'),
                    national_id=national_id,
                    email=email,
                    phone_number=request.POST.get('phone_number'),
                    birth_date=request.POST.get('birth_date'),
                    university=request.POST.get('university'),
                    department=request.POST.get('department'),
                    grade=request.POST.get('grade'),
                    emergency_contact=request.POST.get('emergency_contact'),
                    health_notes=health_notes,

                    team_status=request.POST.get('team_status'),
                    team_name=request.POST.get('team_name', ''),
                    jam_role=request.POST.get('jam_role'),
                    experience_level=request.POST.get('experience_level'),
                    portfolio_url=request.POST.get('portfolio_url', ''),
                    previous_jams=request.POST.get('previous_jams', ''),

                    motivation=request.POST.get('motivation', ''),
                    additional_notes=request.POST.get('additional_notes', ''),
                    kvkk_accepted=True,
                    media_consent=media_consent,
                    health_consent=health_consent,
                    marketing_consent=marketing_consent,
                )
                return self.render_to_response(self.get_context_data(success=True))
            except IntegrityError:
                error_msg = "Sisteme kaydınız sırasında veritabanı kısıtlamasına takıldınız (Zaten kayıtlısınız). Bir sorun olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
                return self.render_to_response(self.get_context_data(error=error_msg))
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Jam başvurusu kaydedilemedi (jam=%s)", jam.pk)
                error_msg = "Başvurunuz alınırken beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
                return self.render_to_response(self.get_context_data(error=error_msg))

        else:
            # Game Jam HARİCİ Etkinlikler (Workshop, Konuşma vb.)
            from .models import EventApplication

            if EventApplication.objects.filter(event=event, email=email).exists():
                error_msg = "Bu e-posta adresiyle bu etkinliğe daha önce kayıt oldunuz."
                return self.render_to_response(self.get_context_data(error=error_msg))

            is_nisantasi_student = request.POST.get('is_nisantasi_student') == 'yes'
            national_id = (request.POST.get('national_id') or '').strip() if not is_nisantasi_student else ''

            if not is_nisantasi_student:
                if not national_id:
                    return self.render_to_response(self.get_context_data(error="Nişantaşı Üniversitesi dışından katılan misafirlerimiz kampüs güvenliği için T.C. Kimlik numarasını girmek zorundadır."))
                if not is_valid_national_id(national_id):
                    return self.render_to_response(self.get_context_data(error="Geçerli bir T.C. Kimlik Numarası giriniz (11 haneli)."))

            national_id_hash = ''
            if national_id:
                national_id_hash = hash_national_id(national_id)
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
                    national_id_hash=national_id_hash,
                    # Aydınlatma onayı yukarıda zorunlu tutuldu; diğerleri açık rıza.
                    kvkk_accepted=True,
                    media_consent=request.POST.get('media_consent') == 'on',
                    marketing_consent=request.POST.get('marketing_consent') == 'on',
                )
                return self.render_to_response(self.get_context_data(success=True))
            except IntegrityError:
                # Kullanıcı gönder tuşuna iki kez bastıysa view'daki exists()
                # kontrolü ile INSERT arasında yarış oluşur; DB kısıtı yakalar.
                error_msg = "Bu etkinliğe zaten kayıtlısınız. Bir sorun olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
                return self.render_to_response(self.get_context_data(error=error_msg))
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Etkinlik başvurusu kaydedilemedi (event=%s)", event.pk)
                error_msg = "Başvurunuz alınırken beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
                return self.render_to_response(self.get_context_data(error=error_msg))


class RaffleJoinView(LoginRequiredMixin, TemplateView):
    """
    QR ile çekiliş katılım sayfası.

    GÜVENLİK: Katılım (DB yazma) yalnızca POST ile yapılır. Eskiden GET'te
    get_or_create çalışıyordu — WhatsApp/Discord link önizlemeleri ve
    tarayıcı prefetch'leri bile kullanıcıyı çekilişe "katılmış" sayabiliyordu.
    """
    template_name = "events/raffle_join.html"
    login_url = "/auth/login/"

    def get_raffle(self):
        return get_object_or_404(Raffle, secret_id=self.kwargs['secret_id'])

    def get(self, request, *args, **kwargs):
        raffle = self.get_raffle()
        context = {'raffle': raffle}

        if not raffle.is_active:
            context['status'] = "closed"
        elif RaffleParticipant.objects.filter(raffle=raffle, user=request.user).exists():
            context['status'] = "already_joined"
        else:
            # Katılım onayı iste — GET hiçbir şey yazmaz.
            context['status'] = "confirm"

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        raffle = self.get_raffle()
        context = {'raffle': raffle}

        if not raffle.is_active:
            context['status'] = "closed"
        else:
            participant, created = RaffleParticipant.objects.get_or_create(
                raffle=raffle,
                user=request.user
            )
            context['status'] = "success" if created else "already_joined"

        return self.render_to_response(context)
