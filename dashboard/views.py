from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from jams.models import GameJam, JamApplication
from dashboard.models import MeetingNote, BoardTask, ClubAsset, Announcement
import json
import csv
from django.http import JsonResponse, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST

class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

class EventBuilderView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/placeholder.html"

class MeetingNotesView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/placeholder.html"

class KanbanView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/placeholder.html"

class AssetsView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/placeholder.html"

class MembersDirectoryView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/placeholder.html"

class BroadcastCenterView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/placeholder.html"

class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
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
