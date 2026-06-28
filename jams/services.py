from django.db import transaction
from collections import defaultdict
from .models import GameJam, JamApplication, SuggestedTeam

def run_matchmaker(jam: GameJam) -> list[SuggestedTeam]:
    """
    Matchmaker Algoritması: 'Ekip arıyorum' diyen başvurucuları rollere göre gruplar.
    Yeni kural: Şema doldurma değil, eksik rol tamamlama.
    """
    # 1. Bekleyen ve ekip arayan başvuruları al
    applications = JamApplication.objects.filter(
        jam=jam,
        team_status=JamApplication.TeamStatus.LOOKING,
        suggested_team__isnull=True,
    ).order_by("created_at")

    if not applications.exists():
        return []

    # 2. Rollere göre başvuruları grupla
    role_groups = defaultdict(list)
    for app in applications:
        role_groups[app.jam_role].append(app)

    suggested_teams = []
    
    # 3. Kaba eşleştirme algoritması (eksik rol tamamlama mantığı)
    # Bu basit bir greedy yaklaşımdır. Geliştirilebilir.
    
    with transaction.atomic():
        while True:
            # Hangi rollerde hala boşta insan var?
            available_roles = [role for role, apps in role_groups.items() if len(apps) > 0]
            if not available_roles:
                break # Kimse kalmadı

            # Yeni bir takım kur
            team_members = []
            
            # Mümkün olduğunca farklı rolleri bir araya getirmeye çalış
            for role in available_roles:
                if len(team_members) >= jam.max_team_size:
                    break
                # Bu rolden birini al
                app = role_groups[role].pop(0)
                team_members.append(app)
            
            # Eğer takım sadece 1 kişiden oluşuyorsa (başka eşleşecek kimse yoksa), döngüyü kır
            # Veya bu kişiyi başka bir takıma yedeğe atabiliriz.
            # Şimdilik en az 2 kişilik takımlar kurmaya çalışalım.
            if len(team_members) > 1:
                team_name = f"Takım {jam.suggested_teams.count() + len(suggested_teams) + 1}"
                team = SuggestedTeam.objects.create(jam=jam, name=team_name)
                
                for member in team_members:
                    member.suggested_team = team
                    member.save(update_fields=["suggested_team"])
                
                suggested_teams.append(team)
            else:
                # Eşleşemeyen tek kişiyi geri listeye ekle (bu döngüde sonsuz loop olmasın diye break)
                # İleride 'yalnız kalanlar' için farklı bir strateji uygulanabilir.
                role_groups[team_members[0].jam_role].insert(0, team_members[0])
                break

    return suggested_teams
