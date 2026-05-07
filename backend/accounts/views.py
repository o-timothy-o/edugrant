import random
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View

from .forms import ApplicantRegistrationForm, ProfileEditForm, ChangeEmailForm
from .models import ApplicantProfile, EmailVerification
from programs.utils import send_welcome_email


def _generate_otp():
    return f"{random.randint(0, 999999):06d}"


def _send_otp_email(email, otp_code):
    send_mail(
        subject="Your EduGrant verification code",
        message=(
            f"Your EduGrant verification code is: {otp_code}\n\n"
            f"This code expires in 10 minutes. Do not share it with anyone.\n\n"
            f"If you did not request this, you can ignore this email.\n\n"
            f"– EduGrant / CAYDO Carmona"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            email = form.cleaned_data["email"]

            # Store pending registration in session (password is already hashed)
            request.session["pending_username"] = user.username
            request.session["pending_email"] = email
            request.session["pending_password"] = user.password

            # Invalidate any previous unused OTPs for this email
            EmailVerification.objects.filter(email=email, is_used=False).update(is_used=True)

            otp_code = _generate_otp()
            EmailVerification.objects.create(
                email=email,
                otp_code=otp_code,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            _send_otp_email(email, otp_code)

            return redirect("accounts:verify_otp")
    else:
        form = ApplicantRegistrationForm()
    return render(request, "registration/register.html", {"form": form})


def verify_otp_view(request):
    pending_email = request.session.get("pending_email")
    if not pending_email:
        return redirect("accounts:register")

    error = None
    if request.method == "POST":
        entered_code = request.POST.get("otp_code", "").strip()
        verification = (
            EmailVerification.objects.filter(
                email=pending_email,
                otp_code=entered_code,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not verification:
            error = "Invalid code. Please check your email and try again."
        elif verification.is_expired:
            error = "This code has expired. Please request a new one below."
        else:
            verification.is_used = True
            verification.save()

            User = get_user_model()
            user = User.objects.create(
                username=request.session["pending_username"],
                email=request.session["pending_email"],
                password=request.session["pending_password"],
                is_staff=False,
            )
            ApplicantProfile.objects.get_or_create(user=user)
            send_welcome_email(user)

            del request.session["pending_username"]
            del request.session["pending_email"]
            del request.session["pending_password"]

            login(request, user)
            return redirect("home")

    return render(request, "registration/verify_otp.html", {
        "email": pending_email,
        "error": error,
    })


def resend_otp_view(request):
    pending_email = request.session.get("pending_email")
    if not pending_email:
        return redirect("accounts:register")

    EmailVerification.objects.filter(email=pending_email, is_used=False).update(is_used=True)

    otp_code = _generate_otp()
    EmailVerification.objects.create(
        email=pending_email,
        otp_code=otp_code,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    _send_otp_email(pending_email, otp_code)

    messages.success(request, "A new verification code has been sent to your email.")
    return redirect("accounts:verify_otp")


class ApplicantLoginView(LoginView):
    """Login for applicants only. Staff are blocked with an error message."""
    template_name = "registration/login.html"

    def form_valid(self, form):
        user = form.get_user()
        if user.is_staff:
            form.add_error(None, "This portal is for applicants only.")
            return self.form_invalid(form)
        return super().form_valid(form)


class CustomLogoutView(View):
    """Logs out the user and redirects staff to the staff login page."""
    def post(self, request):
        is_staff = request.user.is_staff
        logout(request)
        if is_staff:
            return redirect(reverse("staff_login"))
        return redirect(reverse("home"))


@login_required
def profile_view(request):
    profile_form = ProfileEditForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_profile":
            profile_form = ProfileEditForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your account details have been updated.")
                return redirect("accounts:profile")
        elif action == "change_password":
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, "Your password has been changed.")
                return redirect("accounts:profile")

    return render(request, "registration/profile.html", {
        "profile_form": profile_form,
        "password_form": password_form,
    })


@login_required
def change_email_view(request):
    form = ChangeEmailForm(current_user=request.user)
    if request.method == "POST":
        form = ChangeEmailForm(request.POST, current_user=request.user)
        if form.is_valid():
            new_email = form.cleaned_data["email"]
            request.session["pending_new_email"] = new_email

            EmailVerification.objects.filter(email=new_email, is_used=False).update(is_used=True)
            otp_code = _generate_otp()
            EmailVerification.objects.create(
                email=new_email,
                otp_code=otp_code,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            _send_otp_email(new_email, otp_code)
            return redirect("accounts:verify_email_change")

    return render(request, "registration/change_email.html", {"form": form})


@login_required
def verify_email_change_view(request):
    pending_email = request.session.get("pending_new_email")
    if not pending_email:
        return redirect("accounts:change_email")

    error = None
    if request.method == "POST":
        entered_code = request.POST.get("otp_code", "").strip()
        verification = (
            EmailVerification.objects.filter(
                email=pending_email,
                otp_code=entered_code,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not verification:
            error = "Invalid code. Please check your email and try again."
        elif verification.is_expired:
            error = "This code has expired. Please request a new one below."
        else:
            verification.is_used = True
            verification.save()

            request.user.email = pending_email
            request.user.save()
            del request.session["pending_new_email"]

            messages.success(request, "Your email address has been updated.")
            return redirect("accounts:profile")

    return render(request, "registration/verify_email_change.html", {
        "email": pending_email,
        "error": error,
    })


@login_required
def resend_email_change_otp_view(request):
    pending_email = request.session.get("pending_new_email")
    if not pending_email:
        return redirect("accounts:change_email")

    EmailVerification.objects.filter(email=pending_email, is_used=False).update(is_used=True)
    otp_code = _generate_otp()
    EmailVerification.objects.create(
        email=pending_email,
        otp_code=otp_code,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    _send_otp_email(pending_email, otp_code)

    messages.success(request, "A new verification code has been sent to your new email address.")
    return redirect("accounts:verify_email_change")


class StaffLoginView(LoginView):
    """Login for staff only. Non-staff are blocked with a generic error."""
    template_name = "registration/staff_login.html"

    def get_success_url(self):
        return reverse_lazy("admin_dashboard")

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_staff:
            form.add_error(None, "Invalid credentials.")
            return self.form_invalid(form)
        return super().form_valid(form)
