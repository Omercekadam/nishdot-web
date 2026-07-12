from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import get_user_model
from django.db import models
from jams.models import GameJam, JamApplication
from events.models import Event
from dashboard.models import MeetingNote, BoardTask, ClubAsset, Announcement
import json
import csv
from django.http import JsonResponse, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

from django.views.generic import TemplateView, View
from django.utils.text import slugify
from django.db import transaction

class EventBuilderView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/events.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Bütün etkinlikleri (Jam, Workshop, Meetup vb.) getir
        context['events'] = Event.objects.prefetch_related('jam').all().order_by('-start_date')
        return context

@staff_member_required
@require_POST
def api_save_event(request):
    try:
        # Base Event Data
        data = request.POST
        event_id = data.get('event_id')
        title = data.get('title')
        description = data.get('description', '')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        location = data.get('location', 'Belirtilmemiş')
        event_type = data.get('event_type', Event.EventType.GAME_JAM)
        
        # Jam Specific (Only valid if event_type is GAME_JAM)
        deadline = data.get('application_deadline') or start_date
        max_team = data.get('max_team_size', 5)
        is_open = data.get('is_applications_open') == 'true'
        roles_str = data.get('available_roles', '')
        roles = [r.strip() for r in roles_str.split(',')] if roles_str else []
        
        # File upload
        cover_image = request.FILES.get('cover_image')
        thumbnail = request.FILES.get('thumbnail')
        
        with transaction.atomic():
            if event_id:
                event = get_object_or_404(Event, id=event_id)
                event.title = title
                event.description = description
                event.start_date = start_date
                event.end_date = end_date
                event.location = location
                event.event_type = event_type
                event.is_applications_open = is_open
                if cover_image:
                    event.cover_image = cover_image
                if thumbnail:
                    event.thumbnail = thumbnail
                event.save()
                
                if event_type == Event.EventType.GAME_JAM:
                    if hasattr(event, 'jam'):
                        jam = event.jam
                        jam.application_deadline = deadline
                        jam.max_team_size = max_team
                        jam.available_roles = roles
                        jam.save()
                    else:
                        GameJam.objects.create(
                            event=event,
                            application_deadline=deadline,
                            max_team_size=max_team,
                            available_roles=roles
                        )
            else:
                event = Event.objects.create(
                    title=title,
                    slug=slugify(title) + f"-{Event.objects.count()}",
                    description=description,
                    event_type=event_type,
                    status=Event.Status.PUBLISHED,
                    start_date=start_date,
                    end_date=end_date,
                    location=location,
                    is_applications_open=is_open
                )
                if cover_image:
                    event.cover_image = cover_image
                if thumbnail:
                    event.thumbnail = thumbnail
                if cover_image or thumbnail:
                    event.save()
                
                if event_type == Event.EventType.GAME_JAM:
                    GameJam.objects.create(
                        event=event,
                        application_deadline=deadline,
                        max_team_size=max_team,
                        available_roles=roles
                    )
            
        return JsonResponse({'success': True, 'event_id': event.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
def api_event_games_list(request, pk):
    from events.models import Event, EventGame
    event = get_object_or_404(Event, pk=pk)
    games = event.games.all()
    
    games_data = []
    for g in games:
        games_data.append({
            'id': g.id,
            'title': g.title,
            'url': g.url,
            'cover_url': g.cover_image.url if g.cover_image else ''
        })
    return JsonResponse({'games': games_data})

@staff_member_required
@require_POST
def api_add_event_game(request):
    from events.models import Event, EventGame
    try:
        event_id = request.POST.get('event_id')
        title = request.POST.get('title')
        url = request.POST.get('url')
        cover_image = request.FILES.get('cover_image')
        
        event = get_object_or_404(Event, id=event_id)
        
        EventGame.objects.create(
            event=event,
            title=title,
            url=url,
            cover_image=cover_image
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
@require_POST
def api_delete_event_game(request, pk):
    from events.models import EventGame
    try:
        game = get_object_or_404(EventGame, pk=pk)
        game.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
@require_POST
def api_toggle_jam_status(request):
    from events.models import Event
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        
        if event_id:
            event = get_object_or_404(Event, id=event_id)
        else:
            # Fallback for old requests passing jam_id
            jam_id = data.get('jam_id')
            jam = get_object_or_404(GameJam, id=jam_id)
            event = jam.event
            
        event.is_applications_open = not event.is_applications_open
        event.save()
        
        return JsonResponse({'success': True, 'is_open': event.is_applications_open})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

class MeetingNotesView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/notes.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notes'] = MeetingNote.objects.select_related('author').prefetch_related('attendees').all().order_by('-created_at')
        
        User = get_user_model()
        all_users = User.objects.all().order_by('first_name', 'username')
        board_members = [u for u in all_users if u.role in ['admin', 'board'] or u.is_staff]
        context['board_members'] = board_members
        
        return context

@staff_member_required
@require_POST
def api_save_note(request):
    try:
        data = json.loads(request.body)
        note_id = data.get('note_id')
        title = data.get('title')
        content = data.get('content')
        attendee_ids = data.get('attendees', [])
        
        if note_id:
            note = get_object_or_404(MeetingNote, id=note_id)
            note.title = title
            note.content = content
            note.save()
        else:
            note = MeetingNote.objects.create(
                title=title,
                content=content,
                author=request.user
            )
            
        if attendee_ids:
            note.attendees.set(attendee_ids)
        else:
            note.attendees.clear()
            
        return JsonResponse({'success': True, 'note_id': note.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
@require_POST
def api_delete_note(request):
    try:
        data = json.loads(request.body)
        note_id = data.get('note_id')
        note = get_object_or_404(MeetingNote, id=note_id)
        note.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

class KanbanView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/tasks.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        context['staff_users'] = User.objects.filter(is_staff=True).order_by('first_name', 'username')
        
        all_tasks = BoardTask.objects.select_related('assignee', 'creator').all()
        context['todo_tasks'] = [t for t in all_tasks if t.status == 'todo']
        context['in_progress_tasks'] = [t for t in all_tasks if t.status == 'in_progress']
        context['done_tasks'] = [t for t in all_tasks if t.status == 'done']
        
        return context

@staff_member_required
@require_POST
def api_save_task(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        
        title = data.get('title')
        description = data.get('description', '')
        assignee_id = data.get('assignee_id')
        status = data.get('status', 'todo')
        priority = data.get('priority', 'medium')
        category = data.get('category', 'admin')
        deadline = data.get('deadline')
        
        User = get_user_model()
        assignee = None
        if assignee_id:
            assignee = User.objects.filter(id=assignee_id).first()
            
        if task_id:
            task = get_object_or_404(BoardTask, id=task_id)
            task.title = title
            task.description = description
            task.assignee = assignee
            task.status = status
            task.priority = priority
            task.category = category
            if deadline:
                task.deadline = deadline
            else:
                task.deadline = None
            task.save()
        else:
            task = BoardTask.objects.create(
                title=title,
                description=description,
                assignee=assignee,
                creator=request.user,
                status=status,
                priority=priority,
                category=category,
                deadline=deadline if deadline else None
            )
            
        return JsonResponse({'success': True, 'task_id': task.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
@require_POST
def api_update_task_status(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        new_status = data.get('status')
        
        task = get_object_or_404(BoardTask, id=task_id)
        task.status = new_status
        task.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
@require_POST
def api_delete_task(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        task = get_object_or_404(BoardTask, id=task_id)
        task.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

class AssetsView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/assets.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        context['staff_users'] = User.objects.filter(is_staff=True).order_by('first_name', 'username')
        
        assets = ClubAsset.objects.select_related('assignee').all()
        
        incomes = [a for a in assets if a.type == 'income']
        expenses = [a for a in assets if a.type == 'expense']
        equipments = [a for a in assets if a.type == 'equipment']
        finances = [a for a in assets if a.type in ['income', 'expense']]
        
        total_income = sum(a.amount for a in incomes if a.amount)
        total_expense = sum(a.amount for a in expenses if a.amount)
        
        context['finances'] = finances
        context['equipments'] = equipments
        
        context['total_income'] = total_income
        context['total_expense'] = total_expense
        context['total_balance'] = total_income - total_expense
        
        return context

@staff_member_required
@require_POST
def api_save_asset(request):
    try:
        data = json.loads(request.body)
        asset_id = data.get('asset_id')
        
        asset_type = data.get('type')
        title = data.get('title')
        amount = data.get('amount')
        quantity = data.get('quantity', 1)
        notes = data.get('notes', '')
        assignee_id = data.get('assignee_id')
        
        # Validate amount for finances
        if asset_type in ['income', 'expense']:
            if not amount:
                return JsonResponse({'success': False, 'error': 'Tutar girilmesi zorunludur.'}, status=400)
            try:
                amount = float(amount)
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Geçersiz tutar.'}, status=400)
        else:
            amount = None
            
        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                quantity = 1
        except ValueError:
            quantity = 1
            
        User = get_user_model()
        assignee = None
        if assignee_id and asset_type == 'equipment':
            assignee = User.objects.filter(id=assignee_id).first()
            
        if asset_id:
            asset = get_object_or_404(ClubAsset, id=asset_id)
            asset.type = asset_type
            asset.title = title
            asset.amount = amount
            asset.quantity = quantity
            asset.notes = notes
            asset.assignee = assignee
            asset.save()
        else:
            asset = ClubAsset.objects.create(
                type=asset_type,
                title=title,
                amount=amount,
                quantity=quantity,
                notes=notes,
                assignee=assignee
            )
            
        return JsonResponse({'success': True, 'asset_id': asset.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
@require_POST
def api_delete_asset(request):
    try:
        data = json.loads(request.body)
        asset_id = data.get('asset_id')
        asset = get_object_or_404(ClubAsset, id=asset_id)
        asset.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

class MembersDirectoryView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/members.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        all_members = User.objects.all().order_by('first_name', 'username')
        
        board_members = [m for m in all_members if m.role in ['admin', 'board'] or m.is_staff]
        regular_members = [m for m in all_members if m not in board_members]
        
        # Calculate attendance rate for board members
        total_meetings = MeetingNote.objects.count()
        for member in board_members:
            if total_meetings > 0:
                attended = member.attended_meetings.count()
                member.attendance_rate = int((attended / total_meetings) * 100)
            else:
                member.attendance_rate = 0
                
        context['board_members'] = board_members
        context['regular_members'] = regular_members
        context['total_members'] = len(all_members)
        return context

@staff_member_required
@require_POST
def api_update_user_profile(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Bu işlem için yetkiniz yok.'}, status=403)
        
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        role = data.get('role')
        job_title = data.get('job_title', '')
        is_staff = data.get('is_staff')
        
        User = get_user_model()
        user = get_object_or_404(User, id=user_id)
        
        if role in dict(User.Role.choices):
            user.role = role
        user.job_title = job_title
        if is_staff is not None:
            user.is_staff = bool(is_staff)
            
        user.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

from django.core.mail import get_connection, EmailMultiAlternatives
import threading
from decouple import config

def send_broadcast_email_async(subject, message, recipient_list, smtp_account='smtp1'):
    def send():
        try:
            if smtp_account == 'smtp2':
                conn = get_connection(
                    host=config('SMTP2_SERVER', default='smtp.gmail.com'),
                    port=config('SMTP2_PORT', default=587, cast=int),
                    username=config('SMTP2_USERNAME', default=''),
                    password=config('SMTP2_PASSWORD', default=''),
                    use_tls=True
                )
                from_email = config('SMTP2_USERNAME', default='')
            else:
                # Default SMTP1
                conn = get_connection(
                    host=config('SMTP_SERVER', default='smtp.gmail.com'),
                    port=config('SMTP_PORT', default=587, cast=int),
                    username=config('SMTP_USERNAME', default=''),
                    password=config('SMTP_PASSWORD', default=''),
                    use_tls=True
                )
                from_email = config('SMTP_USERNAME', default='')
                
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 10px; overflow: hidden;">
                <div style="background-color: #eb596d; padding: 20px; text-align: center;">
                    <h2 style="color: white; margin: 0;">Nishdot Duyuru</h2>
                </div>
                <div style="padding: 30px; color: #333; line-height: 1.6;">
                    <h3 style="color: #1f2937; margin-top: 0;">{subject}</h3>
                    <div style="font-size: 15px;">
                        {message.replace(chr(10), '<br>')}
                    </div>
                    <br><br>
                    <hr style="border: 0; border-top: 1px solid #eee;">
                    <p style="font-size: 12px; color: #999; text-align: center; margin-bottom: 0;">Bu e-posta İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü (Nishdot) tarafından gönderilmiştir.</p>
                </div>
            </div>
            """
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list,
                connection=conn
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
        except Exception as e:
            print(f"Mail gönderme hatası: {e}")
            
    thread = threading.Thread(target=send)
    thread.start()

class BroadcastCenterView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/broadcast.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['announcements'] = Announcement.objects.all().order_by('-created_at')
        User = get_user_model()
        context['all_users'] = User.objects.filter(is_active=True).order_by('first_name', 'username')
        return context

@staff_member_required
@require_POST
def api_create_broadcast(request):
    try:
        data = json.loads(request.body)
        title = data.get('title')
        content = data.get('content')
        publish_site = data.get('publish_site', False)
        send_email = data.get('send_email', False)
        # send_discord = data.get('send_discord', False) # Şimdilik devre dışı
        smtp_account = data.get('smtp_account', 'smtp1')
        target_audience = data.get('target_audience', 'all')
        
        if not title or not content:
            return JsonResponse({'success': False, 'error': 'Başlık ve içerik zorunludur.'}, status=400)
            
        announcement = Announcement.objects.create(
            title=title,
            content=content,
            published_to_site=publish_site,
            sent_via_email=send_email,
            published_to_discord=False, # Şimdilik False
            target_audience=target_audience,
            author=request.user
        )
        
        if target_audience == 'custom':
            custom_user_ids = data.get('custom_users', [])
            if custom_user_ids:
                announcement.custom_users.add(*custom_user_ids)
        
        if send_email:
            User = get_user_model()
            if target_audience == 'board':
                users = User.objects.filter(models.Q(role__in=['admin', 'board']) | models.Q(is_staff=True))
            elif target_audience == 'members':
                users = User.objects.filter(role='member', is_staff=False)
            elif target_audience == 'custom':
                custom_user_ids = data.get('custom_users', [])
                users = User.objects.filter(id__in=custom_user_ids)
            else:
                users = User.objects.all()
                
            email_list = [u.email for u in users if u.email]
            if email_list:
                send_broadcast_email_async(
                    subject=title,
                    message=content,
                    recipient_list=email_list,
                    smtp_account=smtp_account
                )
                
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

from dashboard.models import SecurityLog

class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Security Logs
        context['security_logs'] = SecurityLog.objects.filter(resolved=False).order_by('-timestamp')[:10]
        
        all_jams = GameJam.objects.select_related('event').order_by("-created_at")
        jam_id = self.request.GET.get('jam')
        
        if jam_id:
            current_jam = all_jams.filter(id=jam_id).first()
        else:
            current_jam = all_jams.first()
            
        if current_jam:
            applications = current_jam.applications.all()
            
            # İstatistikler
            total_apps = applications.count()
            solo_apps = applications.filter(team_status=JamApplication.TeamStatus.SOLO).count()
            looking_team = applications.filter(team_status=JamApplication.TeamStatus.LOOKING).count()
            has_team = applications.filter(team_status=JamApplication.TeamStatus.HAS_TEAM).count()
            
            # Rol bazlı istatistik
            role_stats = {}
            for app in applications:
                role = app.jam_role
                if role:
                    role_stats[role] = role_stats.get(role, 0) + 1
                    
            context.update({
                "jam": current_jam,
                "all_jams": all_jams,
                "applications": applications,
                "stats": {
                    "total": total_apps,
                    "solo": solo_apps,
                    "looking": looking_team,
                    "has_team": has_team,
                },
                "role_stats": role_stats,
            })
            
        return context

@staff_member_required
@require_POST
def update_application_status(request):
    try:
        data = json.loads(request.body)
        app_id = data.get('app_id')
        new_status = data.get('status')
        
        application = get_object_or_404(JamApplication, id=app_id)
        
        if new_status in [choice[0] for choice in JamApplication.ApplicationStatus.choices]:
            application.status = new_status
            application.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Geçersiz durum.'}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required
@require_POST
def api_dismiss_announcement(request, announcement_id):
    from dashboard.models import Announcement
    try:
        announcement = Announcement.objects.get(id=announcement_id)
        announcement.dismissed_by.add(request.user)
        return JsonResponse({"status": "success", "message": "Duyuru gizlendi."})
    except Announcement.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Duyuru bulunamadı."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@staff_member_required
@require_POST
def api_send_bulk_emails(request):
    """Toplu onay/red mailleri gönderir. Spam'e düşmemek için araya gecikme koyar."""
    import time
    import threading
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.conf import settings as django_settings

    try:
        data = json.loads(request.body)
        jam_id = data.get('jam_id')
        whatsapp_link = data.get('whatsapp_link', '')

        if not jam_id:
            return JsonResponse({'success': False, 'error': 'Jam ID gerekli.'}, status=400)
        if not whatsapp_link:
            return JsonResponse({'success': False, 'error': 'WhatsApp davet linki gerekli.'}, status=400)

        jam = get_object_or_404(GameJam, id=jam_id)
        jam_title = jam.event.title

        approved_apps = jam.applications.filter(status=JamApplication.ApplicationStatus.APPROVED)
        rejected_apps = jam.applications.filter(status=JamApplication.ApplicationStatus.REJECTED)

        approved_count = approved_apps.count()
        rejected_count = rejected_apps.count()

        if approved_count == 0 and rejected_count == 0:
            return JsonResponse({'success': False, 'error': 'Gönderilecek onaylanmış veya reddedilmiş başvuru bulunamadı.'}, status=400)

        # Gönderilecek mail listesini hazırla
        emails_to_send = []

        for app in approved_apps:
            html_content = render_to_string('emails/jam_approved.html', {
                'full_name': app.full_name,
                'jam_title': jam_title,
                'whatsapp_link': whatsapp_link,
            })
            emails_to_send.append({
                'subject': f'Başvurunuz Onaylandı — {jam_title}',
                'html': html_content,
                'to': app.email,
            })

        for app in rejected_apps:
            html_content = render_to_string('emails/jam_rejected.html', {
                'full_name': app.full_name,
                'jam_title': jam_title,
            })
            emails_to_send.append({
                'subject': f'Başvuru Sonucunuz — {jam_title}',
                'html': html_content,
                'to': app.email,
            })

        # Asenkron gönderim — her mail arasında 1.5 saniye bekle
        def send_emails_async(email_list):
            for i, email_data in enumerate(email_list):
                try:
                    text_content = strip_tags(email_data['html'])
                    msg = EmailMultiAlternatives(
                        subject=email_data['subject'],
                        body=text_content,
                        from_email=f"Nishdot Game Jam <{django_settings.EMAIL_HOST_USER}>",
                        to=[email_data['to']],
                    )
                    msg.attach_alternative(email_data['html'], "text/html")
                    msg.send(fail_silently=False)
                except Exception as e:
                    print(f"[BULK MAIL HATA] {email_data['to']}: {e}")

                # Spam'e düşmemek için bekleme (son mailden sonra bekleme)
                if i < len(email_list) - 1:
                    time.sleep(1.5)

        thread = threading.Thread(target=send_emails_async, args=(emails_to_send,))
        thread.daemon = True
        thread.start()

        return JsonResponse({
            'success': True,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'total': approved_count + rejected_count,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@staff_member_required
def export_applications_csv(request):
    jam_id = request.GET.get('jam')
    if jam_id:
        current_jam = get_object_or_404(GameJam, id=jam_id)
    else:
        current_jam = GameJam.objects.order_by("-created_at").first()
        
    if not current_jam:
        return HttpResponse("Etkinlik bulunamadı.", status=404)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="jam_applications_{current_jam.id}.csv"'
    
    # BOM for Excel utf-8 recognition
    response.write('\ufeff'.encode('utf8'))
    
    # Türkçe Excel sistemleri varsayılan olarak noktalı virgül (;) ile ayırır
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Ad Soyad', 'E-Posta', 'Telefon', 'TC Kimlik', 'Üniversite', 'Bölüm', 'Sınıf', 'Rol', 'Deneyim', 'Takım Durumu', 'Takım Adı', 'Durum', 'Başvuru Tarihi'])
    
    applications = current_jam.applications.all()
    
    for app in applications:
        team_status_display = app.get_team_status_display()
        status_display = app.get_status_display()
        created_at_str = app.created_at.strftime('%Y-%m-%d %H:%M')
        
        writer.writerow([
            app.full_name,
            app.email,
            app.phone_number,
            app.national_id,
            app.university,
            app.department,
            app.grade,
            app.jam_role,
            app.experience_level,
            team_status_display,
            app.team_name,
            status_display,
            created_at_str
        ])
        
    return response

@staff_member_required
@require_POST
def api_resolve_log(request):
    try:
        data = json.loads(request.body)
        log_id = data.get('log_id')
        log = get_object_or_404(SecurityLog, id=log_id)
        log.resolved = True
        log.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
@require_POST
def api_delete_log(request):
    try:
        data = json.loads(request.body)
        log_id = data.get('log_id')
        log = get_object_or_404(SecurityLog, id=log_id)
        log.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

from events.models import Raffle, RaffleParticipant
import random

class RaffleListView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/raffles_list.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['raffles'] = Raffle.objects.all()
        context['events'] = Event.objects.filter(status__in=[Event.Status.PUBLISHED, Event.Status.DRAFT])
        return context

@staff_member_required
@require_POST
def api_create_raffle(request):
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        title = data.get('title')
        
        event = get_object_or_404(Event, id=event_id)
        Raffle.objects.create(event=event, title=title)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

from django.views.generic import DetailView

class RaffleQRView(StaffRequiredMixin, DetailView):
    model = Raffle
    template_name = "dashboard/raffle_qr.html"
    context_object_name = "raffle"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Construct full URL for QR code
        context['join_url'] = self.request.build_absolute_uri(
            f"/events/raffle/join/{self.object.secret_id}/"
        )
        return context

class RaffleDrawView(StaffRequiredMixin, DetailView):
    model = Raffle
    template_name = "dashboard/raffle_draw.html"
    context_object_name = "raffle"

@staff_member_required
def api_raffle_participants(request, pk):
    raffle = get_object_or_404(Raffle, pk=pk)
    participants = list(raffle.participants.values('id', 'user__first_name', 'user__last_name', 'user__username'))
    
    formatted_participants = []
    for p in participants:
        name = f"{p['user__first_name']} {p['user__last_name']}".strip()
        if not name:
            name = p['user__username']
        formatted_participants.append({
            'id': p['id'],
            'name': name
        })
        
    return JsonResponse({
        'count': len(formatted_participants),
        'participants': formatted_participants
    })

@staff_member_required
@require_POST
def api_raffle_remove_participant(request, pk):
    raffle = get_object_or_404(Raffle, pk=pk)
    try:
        data = json.loads(request.body)
        participant_id = data.get('participant_id')
        participant = get_object_or_404(RaffleParticipant, id=participant_id, raffle=raffle)
        participant.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
@require_POST
def api_raffle_pick_winner(request, pk):
    raffle = get_object_or_404(Raffle, pk=pk)
        
    participants = list(raffle.participants.all())
    if not participants:
        return JsonResponse({'success': False, 'error': 'Henüz katılımcı yok.'})
        
    winner = random.choice(participants)
    return JsonResponse({
        'success': True,
        'winner': winner.user.get_full_name() or winner.user.username
    })

@staff_member_required
@require_POST
def api_raffle_toggle(request, pk):
    raffle = get_object_or_404(Raffle, pk=pk)
    data = json.loads(request.body)
    raffle.is_active = data.get('is_active', False)
    raffle.save()
    return JsonResponse({'success': True})
