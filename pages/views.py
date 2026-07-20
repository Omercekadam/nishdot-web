from django.views.generic import TemplateView, DetailView
from events.models import Event
from .models import LegalDocument

class HomePageView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['events'] = Event.objects.filter(status__in=['published', 'completed']).order_by('-is_pinned', '-start_date')
        return context

class LegalDocumentDetailView(DetailView):
    model = LegalDocument
    template_name = "pages/legal_document.html"
    context_object_name = "document"
