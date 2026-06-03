"""Management command: dataset integrity testing across 5 dimensions."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from accounts.models import ApplicantProfile
from programs.models import Application, Program, ScreeningResult
from programs.services import _extract_number

User = get_user_model()

ACTIVE = [
    Application.ApplicationStatus.SUBMITTED,
    Application.ApplicationStatus.FOR_REVIEW,
    Application.ApplicationStatus.APPROVED,
    Application.ApplicationStatus.AWAITING_PHYSICAL,
    Application.ApplicationStatus.REJECTED,
]


class Command(BaseCommand):
    help = "Run dataset integrity checks: Completeness, Validity, Consistency, Uniqueness, Referential Integrity."

    def handle(self, *args, **options):
        checks = (
            self._completeness()
            + self._validity()
            + self._consistency()
            + self._uniqueness()
            + self._referential_integrity()
        )

        passed = sum(1 for c in checks if c["passed"])
        failed = len(checks) - passed

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("  DATASET INTEGRITY REPORT — EduGrant")
        self.stdout.write("=" * 65)

        current = None
        for c in checks:
            if c["dimension"] != current:
                current = c["dimension"]
                self.stdout.write(f"\n  [{current.upper()}]")
            tag = self.style.SUCCESS("PASS") if c["passed"] else self.style.ERROR("FAIL")
            self.stdout.write(f"  {tag}  {c['name']}")
            if not c["passed"]:
                self.stdout.write(f"        → {c['detail']}")

        self.stdout.write("\n" + "-" * 65)
        summary = f"  Result: {passed}/{len(checks)} checks passed"
        if failed == 0:
            self.stdout.write(self.style.SUCCESS(summary))
        else:
            self.stdout.write(self.style.ERROR(f"{summary}  ({failed} failed)"))
        self.stdout.write("=" * 65 + "\n")

    # ------------------------------------------------------------------
    # 1. Completeness — no missing records or required fields
    # ------------------------------------------------------------------
    def _completeness(self):
        dim = "Completeness"

        active_ids = set(
            Application.objects.filter(status__in=ACTIVE)
            .values_list("applicant_id", flat=True)
        )
        profile_ids = set(
            ApplicantProfile.objects.filter(user_id__in=active_ids)
            .values_list("user_id", flat=True)
        )
        no_profile = len(active_ids - profile_ids)

        blank_fields = ApplicantProfile.objects.filter(
            user_id__in=active_ids
        ).filter(
            Q(first_name="") | Q(last_name="") |
            Q(monthly_income="") | Q(residency_years="")
        ).count()

        no_date = Application.objects.filter(
            status__in=ACTIVE, submitted_at__isnull=True
        ).count()

        return [
            {
                "dimension": dim,
                "name": "All applicants have a profile record",
                "passed": no_profile == 0,
                "detail": f"{no_profile} applicant(s) missing an ApplicantProfile",
            },
            {
                "dimension": dim,
                "name": "No blank critical fields (name, income, residency)",
                "passed": blank_fields == 0,
                "detail": f"{blank_fields} profile(s) with blank required fields",
            },
            {
                "dimension": dim,
                "name": "All submitted applications have a submission date",
                "passed": no_date == 0,
                "detail": f"{no_date} application(s) missing submitted_at",
            },
        ]

    # ------------------------------------------------------------------
    # 2. Validity — values are in expected format and range
    # ------------------------------------------------------------------
    def _validity(self):
        dim = "Validity"

        active_ids = set(
            Application.objects.filter(status__in=ACTIVE)
            .values_list("applicant_id", flat=True)
        )
        profiles = list(
            ApplicantProfile.objects.filter(user_id__in=active_ids)
            .only("monthly_income", "residency_years")
        )

        bad_income = sum(
            1 for p in profiles
            if p.monthly_income and _extract_number(p.monthly_income) is None
        )
        bad_residency = sum(
            1 for p in profiles
            if p.residency_years and _extract_number(p.residency_years) is None
        )

        valid_statuses = {s for s, _ in Application.ApplicationStatus.choices}
        invalid_status = Application.objects.exclude(status__in=valid_statuses).count()

        return [
            {
                "dimension": dim,
                "name": "monthly_income is a parseable numeric value",
                "passed": bad_income == 0,
                "detail": f"{bad_income} profile(s) have unparseable income values",
            },
            {
                "dimension": dim,
                "name": "residency_years is a parseable numeric value",
                "passed": bad_residency == 0,
                "detail": f"{bad_residency} profile(s) have unparseable residency values",
            },
            {
                "dimension": dim,
                "name": "All application status values are valid choices",
                "passed": invalid_status == 0,
                "detail": f"{invalid_status} application(s) have unrecognised status values",
            },
        ]

    # ------------------------------------------------------------------
    # 3. Consistency — no contradictions across related records
    # ------------------------------------------------------------------
    def _consistency(self):
        dim = "Consistency"

        rejected_no_reason = sum(
            1 for app in Application.objects.filter(
                status=Application.ApplicationStatus.REJECTED
            ).only("rejection_reason")
            if not app.rejection_reason
        )

        total_active = Application.objects.filter(status__in=ACTIVE).count()
        has_result = Application.objects.filter(
            status__in=ACTIVE, screening_result__isnull=False
        ).count()
        missing_result = total_active - has_result

        duplicate_approved = (
            Application.objects.filter(status=Application.ApplicationStatus.APPROVED)
            .values("applicant_id", "program_id")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .count()
        )

        return [
            {
                "dimension": dim,
                "name": "All rejected applications have a recorded rejection reason",
                "passed": rejected_no_reason == 0,
                "detail": f"{rejected_no_reason} rejected application(s) have no rejection reason",
            },
            {
                "dimension": dim,
                "name": "All submitted applications have a screening result",
                "passed": missing_result == 0,
                "detail": f"{missing_result} application(s) missing a ScreeningResult",
            },
            {
                "dimension": dim,
                "name": "No applicant holds duplicate approvals for the same program",
                "passed": duplicate_approved == 0,
                "detail": f"{duplicate_approved} (applicant, program) pair(s) with multiple approvals",
            },
        ]

    # ------------------------------------------------------------------
    # 4. Uniqueness — no duplicate records
    # ------------------------------------------------------------------
    def _uniqueness(self):
        dim = "Uniqueness"

        dup_emails = (
            User.objects.values("email")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .count()
        )

        dup_submissions = (
            Application.objects.filter(status__in=ACTIVE)
            .values("applicant_id", "program_id")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .count()
        )

        return [
            {
                "dimension": dim,
                "name": "No duplicate user email addresses",
                "passed": dup_emails == 0,
                "detail": f"{dup_emails} email(s) shared by multiple accounts",
            },
            {
                "dimension": dim,
                "name": "No applicant has submitted more than once to the same program",
                "passed": dup_submissions == 0,
                "detail": f"{dup_submissions} (applicant, program) pair(s) with multiple submissions",
            },
        ]

    # ------------------------------------------------------------------
    # 5. Referential Integrity — no orphaned records
    # ------------------------------------------------------------------
    def _referential_integrity(self):
        dim = "Referential Integrity"

        valid_program_ids = set(Program.objects.values_list("id", flat=True))
        orphan_apps = Application.objects.exclude(
            program_id__in=valid_program_ids
        ).count()

        valid_app_ids = set(Application.objects.values_list("id", flat=True))
        orphan_results = ScreeningResult.objects.exclude(
            application_id__in=valid_app_ids
        ).count()

        return [
            {
                "dimension": dim,
                "name": "All applications reference an existing program",
                "passed": orphan_apps == 0,
                "detail": f"{orphan_apps} application(s) reference a deleted/non-existent program",
            },
            {
                "dimension": dim,
                "name": "All screening results reference an existing application",
                "passed": orphan_results == 0,
                "detail": f"{orphan_results} ScreeningResult(s) orphaned from their application",
            },
        ]
