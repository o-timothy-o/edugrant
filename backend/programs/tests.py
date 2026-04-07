from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from programs.models import (
    Application,
    ApplicationDocument,
    DocumentRequirement,
    Program,
    ScreeningResult,
)
from programs.services import get_application_completeness, run_rule_evaluation

User = get_user_model()


class CompletenessServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="test")
        self.program = Program.objects.create(name="Test Program")
        self.req1 = DocumentRequirement.objects.create(
            program=self.program, name="ID", required=True, display_order=1
        )
        self.req2 = DocumentRequirement.objects.create(
            program=self.program, name="Clearance", required=True, display_order=2
        )
        self.app = Application.objects.create(
            applicant=self.user, program=self.program, status="draft"
        )

    def test_complete_when_all_submitted(self):
        for ad in self.app.application_documents.all():
            ad.status = ApplicationDocument.DocStatus.SUBMITTED
            ad.save()
        result = get_application_completeness(self.app)
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["missing"]), 0)
        self.assertEqual(len(result["invalid"]), 0)

    def test_incomplete_when_missing(self):
        result = get_application_completeness(self.app)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["missing"]), 2)

    def test_incomplete_when_invalid(self):
        ad = self.app.application_documents.get(requirement=self.req1)
        ad.status = ApplicationDocument.DocStatus.INVALID
        ad.issue_notes = "Blurry"
        ad.save()
        result = get_application_completeness(self.app)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["invalid"]), 1)


class RuleEvaluationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="test")
        self.program = Program.objects.create(name="Test Program")
        self.req1 = DocumentRequirement.objects.create(
            program=self.program, name="ID", required=True, display_order=1
        )
        self.app = Application.objects.create(
            applicant=self.user, program=self.program, status="submitted"
        )

    def test_pass_when_complete_and_no_prior(self):
        for ad in self.app.application_documents.all():
            ad.status = ApplicationDocument.DocStatus.SUBMITTED
            ad.save()
        result = run_rule_evaluation(self.app)
        self.assertEqual(result.outcome, ScreeningResult.Outcome.PASS)
        self.assertEqual(len(result.reasons), 0)

    def test_flag_when_prior_approved(self):
        Application.objects.create(
            applicant=self.user,
            program=self.program,
            status=Application.ApplicationStatus.APPROVED,
        )
        for ad in self.app.application_documents.all():
            ad.status = ApplicationDocument.DocStatus.SUBMITTED
            ad.save()
        result = run_rule_evaluation(self.app)
        self.assertEqual(result.outcome, ScreeningResult.Outcome.FLAG)
        self.assertTrue(any("prior" in r.lower() for r in result.reasons))

    def test_flag_when_incomplete(self):
        result = run_rule_evaluation(self.app)
        self.assertEqual(result.outcome, ScreeningResult.Outcome.FLAG)
        self.assertTrue(any("missing" in r.lower() for r in result.reasons))


# ── View tests ──────────────────────────────────────────────────────────────

class SparkResubmissionGuardTest(TestCase):
    """SPARK is one-time only: a submitted app must redirect to detail, not show form."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="applicant", password="pass")
        self.spark = Program.objects.create(name="SPARK", program_type="grant")
        self.client.login(username="applicant", password="pass")

    def test_can_access_spark_step1_when_no_prior_app(self):
        response = self.client.get(reverse("programs:spark_application"))
        self.assertEqual(response.status_code, 200)

    def test_spark_step1_shows_modal_if_submitted_app_exists(self):
        Application.objects.create(
            applicant=self.user, program=self.spark, status="submitted"
        )
        response = self.client.get(reverse("programs:spark_application"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "programs/existing_application.html")

    def test_spark_step1_shows_modal_if_approved_app_exists(self):
        Application.objects.create(
            applicant=self.user, program=self.spark, status="approved"
        )
        response = self.client.get(reverse("programs:spark_application"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "programs/existing_application.html")

    def test_spark_step1_does_not_redirect_for_draft(self):
        Application.objects.create(
            applicant=self.user, program=self.spark, status="draft"
        )
        response = self.client.get(reverse("programs:spark_application"))
        self.assertEqual(response.status_code, 200)


class SinagResubmissionGuardTest(TestCase):
    """SINAG blocks a new application if one is already submitted/under review."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="applicant2", password="pass")
        self.sinag = Program.objects.create(name="SINAG", program_type="scholarship")
        self.client.login(username="applicant2", password="pass")

    def test_can_access_sinag_step1_when_no_prior_app(self):
        response = self.client.get(reverse("programs:sinag_application"))
        self.assertEqual(response.status_code, 200)

    def test_sinag_step1_shows_modal_if_submitted_app_pending(self):
        Application.objects.create(
            applicant=self.user, program=self.sinag, status="submitted"
        )
        response = self.client.get(reverse("programs:sinag_application"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "programs/existing_application.html")

    def test_sinag_step1_allows_new_app_after_approval(self):
        Application.objects.create(
            applicant=self.user, program=self.sinag, status="approved"
        )
        response = self.client.get(reverse("programs:sinag_application"))
        self.assertEqual(response.status_code, 200)


class Step2ResubmissionGuardTest(TestCase):
    """Step 2 must redirect to detail if the application is already submitted."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="applicant3", password="pass")
        self.spark = Program.objects.create(name="SPARK", program_type="grant")
        self.client.login(username="applicant3", password="pass")

    def test_spark_step2_redirects_if_already_submitted(self):
        app = Application.objects.create(
            applicant=self.user, program=self.spark, status="submitted"
        )
        url = reverse("programs:spark_application_step2", kwargs={"application_id": app.id})
        response = self.client.get(url)
        self.assertRedirects(
            response,
            reverse("programs:application_detail", kwargs={"application_id": app.id}),
        )

    def test_spark_step2_accessible_for_draft(self):
        app = Application.objects.create(
            applicant=self.user, program=self.spark, status="draft"
        )
        url = reverse("programs:spark_application_step2", kwargs={"application_id": app.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ReportsViewTest(TestCase):
    """Reports page is staff-only and returns 200."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.applicant = User.objects.create_user(username="user", password="pass")

    def test_reports_accessible_by_staff(self):
        self.client.login(username="staff", password="pass")
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, 200)

    def test_reports_blocked_for_non_staff(self):
        self.client.login(username="user", password="pass")
        response = self.client.get(reverse("reports"))
        self.assertNotEqual(response.status_code, 200)

    def test_reports_blocked_for_anonymous(self):
        response = self.client.get(reverse("reports"))
        self.assertNotEqual(response.status_code, 200)
