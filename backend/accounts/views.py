from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy, reverse
from django.views import View

from .forms import ApplicantRegistrationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = ApplicantRegistrationForm()
    return render(request, "registration/register.html", {"form": form})


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
            return redirect(reverse('staff_login'))
        return redirect(reverse('home'))


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