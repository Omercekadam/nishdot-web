from django.views.generic import TemplateView
from events.models import Event

class HomePageView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['events'] = Event.objects.filter(status='published').order_by('-start_date')[:3]
        return context
