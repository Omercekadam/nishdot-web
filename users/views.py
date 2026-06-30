from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import UserRegisterForm, UserLoginForm, UserProfileUpdateForm
from jams.models import JamApplication

User = get_user_model()

class UserRegisterView(CreateView):
    template_name = "users/register.html"
    form_class = UserRegisterForm
    success_url = reverse_lazy("users:dashboard")

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("users:dashboard")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f"Aramıza hoş geldin, {user.first_name}!")
        return redirect(self.success_url)

class UserLoginView(LoginView):
    template_name = "users/login.html"
    form_class = UserLoginForm
    redirect_authenticated_user = True


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "users/dashboard.html"
    login_url = "users:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Kullanıcının e-posta adresiyle eşleşen Game Jam başvurularını çekiyoruz
        user_email = self.request.user.email
        applications = JamApplication.objects.filter(email=user_email).order_by("-created_at")
        
        # Siteye yayınlanmış duyuruları çekiyoruz (Hedef kitleye göre filtreleyerek)
        from dashboard.models import Announcement
        from django.db.models import Q
        user = self.request.user
        
        query = Q(published_to_site=True) & (
            Q(target_audience='all') |
            Q(custom_users=user)
        )
        
        if user.is_staff or user.role in ['admin', 'board']:
            query |= Q(target_audience='board')
        else:
            query |= Q(target_audience='members')
            
        announcements = Announcement.objects.filter(query).exclude(dismissed_by=user).distinct().order_by("-created_at")
        
        context["applications"] = applications
        context["announcements"] = announcements
        if "form" not in context:
            context["form"] = UserProfileUpdateForm(instance=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        form = UserProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil bilgilerin başarıyla güncellendi.")
            return redirect("users:dashboard")
        
        context = self.get_context_data(form=form)
        return self.render_to_response(context)
