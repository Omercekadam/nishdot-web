import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nishdot.settings.development')
django.setup()

from events.models import Event
from jams.models import GameJam
from django.utils import timezone
from datetime import timedelta

now = timezone.now()

event, created = Event.objects.get_or_create(
    slug='nishyear-jam-2025',
    defaults={
        'title': 'NishYear Jam 2025',
        'description': 'Yeni yıla oyun geliştirerek giriyoruz! 48 saatlik maratona hazır mısınız? Bu eşsiz deneyimde sen de yerini al.',
        'event_type': 'game_jam',
        'status': 'published',
        'start_date': now + timedelta(days=10),
        'end_date': now + timedelta(days=12),
        'location': 'Nişantaşı Üniversitesi, C Katı',
        'cover_image': 'events/covers/nishyearafis.png'
    }
)

GameJam.objects.get_or_create(
    event=event,
    defaults={
        'application_deadline': now + timedelta(days=5),
        'max_team_size': 5,
        'is_applications_open': True,
        'available_roles': ['Developer', '3D Artist', '2D Artist', 'Game Designer', 'Sound Designer']
    }
)
print('Seed complete!')
