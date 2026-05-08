from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import ApplicantProfile

User = get_user_model()


class ApplicantRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.is_staff = False
        if commit:
            user.save()
            ApplicantProfile.objects.get_or_create(user=user)
        return user


class ChangeEmailForm(forms.Form):
    email = forms.EmailField(label="New Email Address")

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user

    def clean_email(self):
        email = self.cleaned_data["email"]
        if self.current_user and email == self.current_user.email:
            raise forms.ValidationError("This is already your current email address.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email