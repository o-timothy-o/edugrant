from django.conf import settings
from django.db import models


class Program(models.Model):
    """Scholarship or grant program (e.g. SINAG, SPARK)."""

    class ProgramType(models.TextChoices):
        SCHOLARSHIP = "scholarship", "Scholarship"
        GRANT = "grant", "Grant"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=128)
    short_name = models.CharField(
        max_length=32,
        blank=True,
        help_text="Short label used on buttons, pills, and dashboards (e.g. SINAG, SPARK).",
    )
    program_type = models.CharField(
        max_length=32,
        choices=ProgramType.choices,
        default=ProgramType.SCHOLARSHIP,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    application_frequency = models.CharField(
        max_length=64,
        blank=True,
        help_text="e.g. once per year, per batch",
    )
    description = models.TextField(
        blank=True,
        help_text="Short description shown to applicants on the programs list.",
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "programs_program"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Application(models.Model):
    """A single application by an applicant to a program."""

    class ApplicationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        FOR_REVIEW = "for_review", "In Review"
        APPROVED = "approved", "Approved"
        AWAITING_PHYSICAL = "awaiting_physical", "Approved – Awaiting Physical Submission"
        REJECTED = "rejected", "Rejected"

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    status = models.CharField(
        max_length=32,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.DRAFT,
    )
    class RejectionReason(models.TextChoices):
        INCOME       = "income",        "Income exceeds program limit"
        RESIDENCY    = "residency",     "Does not meet residency requirement"
        NOT_ENROLLED = "not_enrolled",  "Not currently enrolled"
        EMPLOYMENT   = "employment",    "Does not meet employment status requirement"
        INCOMPLETE   = "incomplete",    "Incomplete or invalid documents"
        OTHER        = "other",         "Other"

    submitted_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    educational_data = models.JSONField(default=dict, blank=True)
    is_archived = models.BooleanField(default=False)
    rejection_reason = models.JSONField(default=list, blank=True)
    rejection_reason_other = models.CharField(max_length=255, blank=True, default='')

    @property
    def rejection_reason_labels(self):
        labels = dict(self.RejectionReason.choices)
        return [labels.get(r, r) for r in (self.rejection_reason or [])]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "programs_application"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.applicant.username} – {self.program.name} ({self.status})"


class DocumentRequirement(models.Model):
    """Document required or optional for a program."""

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="document_requirements",
    )
    name = models.CharField(max_length=128)
    required = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "programs_documentrequirement"
        ordering = ["program", "display_order", "name"]

    def __str__(self):
        req = "required" if self.required else "optional"
        return f"{self.program.name}: {self.name} ({req})"


class ApplicationDocument(models.Model):
    """Tracks submission status of a document requirement for an application."""

    class DocStatus(models.TextChoices):
        MISSING = "missing", "Missing"
        SUBMITTED = "submitted", "Submitted"
        INVALID = "invalid", "Invalid"

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="application_documents",
    )
    requirement = models.ForeignKey(
        DocumentRequirement,
        on_delete=models.CASCADE,
        related_name="application_documents",
    )
    status = models.CharField(
        max_length=32,
        choices=DocStatus.choices,
        default=DocStatus.MISSING,
    )
    file = models.FileField(upload_to="application_docs/%Y/%m/", blank=True, null=True, max_length=500)
    issue_notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "programs_applicationdocument"
        unique_together = [["application", "requirement"]]

    def __str__(self):
        return f"{self.application} – {self.requirement.name}: {self.status}"


class ProgramRule(models.Model):
    """Predefined rule for screening applications."""

    class RuleType(models.TextChoices):
        ELIGIBILITY = "eligibility", "Eligibility"
        CONFLICT = "conflict", "Conflict"
        COMPLETENESS = "completeness", "Completeness"

    class RuleField(models.TextChoices):
        MONTHLY_INCOME   = "monthly_income",   "Monthly Income"
        RESIDENCY_YEARS  = "residency_years",  "Years of Residency"
        BARANGAY         = "barangay",         "Barangay"
        CITIZENSHIP      = "citizenship",      "Citizenship"
        CIVIL_STATUS     = "civil_status",     "Civil Status"
        CURRENTLY_WORKING = "currently_working", "Employment Status"
        GENDER           = "gender",           "Gender"
        COURSE           = "course",           "Course / Degree"
        SCHOOL           = "school",           "School"
        GRADUATION_DATE  = "graduation_date",  "Graduation Date"

    class Condition(models.TextChoices):
        LTE          = "lte",          "Must not exceed"
        GTE          = "gte",          "Must be at least"
        EQUALS       = "equals",       "Must be equal to"
        NOT_EQUALS   = "not_equals",   "Must not be"
        IN_LIST      = "in_list",      "Must be one of (comma-separated)"
        DATE_AFTER   = "date_after",   "Must be on or after (YYYY-MM-DD)"
        DATE_BEFORE  = "date_before",  "Must be on or before (YYYY-MM-DD)"

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    name = models.CharField(max_length=128)
    rule_type = models.CharField(max_length=32, choices=RuleType.choices)
    rule_field = models.CharField(max_length=64, choices=RuleField.choices, blank=True)
    condition = models.CharField(max_length=32, choices=Condition.choices, blank=True)
    value = models.CharField(
        max_length=255,
        blank=True,
        help_text='The value to compare against. For "Must be one of", separate values with commas. For dates, use YYYY-MM-DD format.',
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "programs_programrule"
        ordering = ["program", "display_order", "name"]

    def __str__(self):
        return f"{self.program.name}: {self.name} ({self.rule_type})"


class ScreeningResult(models.Model):
    """Result of rule evaluation for an application."""

    class Outcome(models.TextChoices):
        PASS = "pass", "Pass"
        FLAG = "flag", "Flag"

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="screening_result",
    )
    outcome = models.CharField(max_length=32, choices=Outcome.choices)
    reasons = models.JSONField(
        default=list,
        help_text="List of rule names or reasons that triggered a Flag",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "programs_screeningresult"

    def __str__(self):
        return f"{self.application}: {self.outcome}"


class ApplicationStatusLog(models.Model):
    """Records every status change on an application with a timestamp and actor."""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    status = models.CharField(max_length=50)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="status_log_entries",
    )

    class Meta:
        db_table = "programs_applicationstatuslog"
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.application} → {self.status}"
