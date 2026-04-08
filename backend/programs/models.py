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
        FOR_REVIEW = "for_review", "For Review"
        APPROVED = "approved", "Approved"
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
    submitted_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    educational_data = models.JSONField(default=dict, blank=True)
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
    file = models.FileField(upload_to="application_docs/%Y/%m/", blank=True, null=True)
    issue_notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "programs_applicationdocument"
        unique_together = [["application", "requirement"]]

    def __str__(self):
        return f"{self.application} – {self.requirement.name}: {self.status}"


class ProgramRule(models.Model):
    """Predefined rule for screening applications (eligibility, conflict, completeness)."""

    class RuleType(models.TextChoices):
        ELIGIBILITY = "eligibility", "Eligibility"
        CONFLICT = "conflict", "Conflict"
        COMPLETENESS = "completeness", "Completeness"

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    name = models.CharField(max_length=128)
    rule_type = models.CharField(
        max_length=32,
        choices=RuleType.choices,
    )
    definition = models.JSONField(
        default=dict,
        blank=True,
        help_text="Rule parameters, e.g. {\"check_prior_assistance\": true}",
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
