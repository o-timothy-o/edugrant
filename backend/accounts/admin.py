from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ApplicantProfile


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "barangay", "contact_number")
    search_fields = ("user__username", "user__email")
