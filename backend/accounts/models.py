from django.conf import settings
from django.db import models


class ApplicantProfile(models.Model):
    """Applicant-specific profile (personal/demographic). One per user who is an applicant."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applicant_profile",
    )
    # Personal information (from Step 1 form)
    full_name = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    barangay = models.CharField(max_length=128, blank=True)
    residency_years = models.CharField(max_length=64, blank=True)
    gender = models.CharField(max_length=64, blank=True)
    civil_status = models.CharField(max_length=64, blank=True)
    citizenship = models.CharField(max_length=64, blank=True)
    contact_number = models.CharField(max_length=32, blank=True)
    currently_working = models.CharField(max_length=64, blank=True)
    religion = models.CharField(max_length=128, blank=True)
    monthly_income = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "accounts_applicantprofile"

    def __str__(self):
        return f"Profile: {self.user.username}"
