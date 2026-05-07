from django.urls import path
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("verify/", views.verify_otp_view, name="verify_otp"),
    path("verify/resend/", views.resend_otp_view, name="resend_otp"),
    path("change-email/", views.change_email_view, name="change_email"),
    path("change-email/verify/", views.verify_email_change_view, name="verify_email_change"),
    path("change-email/resend/", views.resend_email_change_otp_view, name="resend_email_change_otp"),
    path("login/", views.ApplicantLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("password-reset/", PasswordResetView.as_view(
        template_name="registration/password_reset.html",
        email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt",
    ), name="password_reset"),
    path("password-reset/done/", PasswordResetDoneView.as_view(
        template_name="registration/password_reset_done.html",
    ), name="password_reset_done"),
    path("password-reset/confirm/<uidb64>/<token>/", PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html",
    ), name="password_reset_confirm"),
    path("password-reset/complete/", PasswordResetCompleteView.as_view(
        template_name="registration/password_reset_complete.html",
    ), name="password_reset_complete"),
]