"""
Users URL Configuration
========================

Kullanıcı ile ilgili URL pattern'ları burada tanımlanacak.
Şimdilik boş — login/logout URL'leri beta aşamasında eklenecek.

Root urls.py'den şu şekilde include edilecek:
    path("hesap/", include("users.urls")),
"""

from django.urls import path, reverse_lazy
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from . import views
from . import api

app_name = "users"

urlpatterns = [
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("register/", views.UserRegisterView.as_view(), name="register"),
    path("logout/", LogoutView.as_view(next_page="pages:home"), name="logout"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    
    # Şifre Sıfırlama (Password Reset)
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="users/password_reset_form.html",
        email_template_name="emails/password_reset_email.html",
        html_email_template_name="emails/password_reset_email.html",
        subject_template_name="emails/password_reset_subject.txt",
        success_url=reverse_lazy("users:password_reset_done")
    ), name="password_reset"),
    
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="users/password_reset_done.html"
    ), name="password_reset_done"),
    
    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="users/password_reset_confirm.html",
        success_url=reverse_lazy("users:password_reset_complete")
    ), name="password_reset_confirm"),
    
    path("password-reset-complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="users/password_reset_complete.html"
    ), name="password_reset_complete"),

    # API Endpoints
    path("api/register/", api.register_api_view, name="api_register"),
    path("api/verify/", api.verify_otp_api_view, name="api_verify"),
    path("api/resend-otp/", api.resend_otp_api_view, name="api_resend_otp"),
]
