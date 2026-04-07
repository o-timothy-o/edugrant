"""Services for programs app: completeness, screening, etc."""

from programs.models import (
    Application,
    ApplicationDocument,
    ProgramRule,
    ScreeningResult,
)


def get_application_completeness(application):
    """
    Check if an application meets all document requirements.

    Returns a dict:
        - complete: bool
        - missing: list of DocumentRequirement (required but not submitted/valid)
        - invalid: list of ApplicationDocument with status invalid
    """
    program = application.program
    requirements = program.document_requirements.filter(required=True).order_by(
        "display_order", "name"
    )

    # Build lookup of requirement -> ApplicationDocument for this application
    app_docs = {
        ad.requirement_id: ad
        for ad in application.application_documents.select_related("requirement")
    }

    missing = []
    invalid = []

    for req in requirements:
        ad = app_docs.get(req.id)
        if ad is None:
            missing.append(req)
        elif ad.status == ApplicationDocument.DocStatus.INVALID:
            invalid.append(ad)
        elif ad.status == ApplicationDocument.DocStatus.MISSING:
            missing.append(req)

    return {
        "complete": len(missing) == 0 and len(invalid) == 0,
        "missing": missing,
        "invalid": invalid,
    }


def run_rule_evaluation(application):
    """
    Run rule evaluation: eligibility -> conflict -> completeness.
    Creates or updates ScreeningResult. Returns the ScreeningResult.
    """
    reasons = []
    outcome = ScreeningResult.Outcome.PASS

    # 1. Eligibility rules (for now: pass if no rules, or run simple checks)
    for rule in application.program.rules.filter(rule_type=ProgramRule.RuleType.ELIGIBILITY):
        if rule.definition.get("check_profile"):
            from accounts.models import ApplicantProfile

            if not ApplicantProfile.objects.filter(user=application.applicant).exists():
                reasons.append(f"{rule.name}: Applicant profile missing")
                outcome = ScreeningResult.Outcome.FLAG

    # 2. Conflict: applicant must not have prior approved assistance
    prior_approved = Application.objects.filter(
        applicant=application.applicant,
        status=Application.ApplicationStatus.APPROVED,
    ).exclude(id=application.id)

    if prior_approved.exists():
        reasons.append("Applicant has existing or prior approved scholarship/grant assistance")
        outcome = ScreeningResult.Outcome.FLAG

    # 3. Completeness: all required documents submitted and valid
    completeness = get_application_completeness(application)
    if not completeness["complete"]:
        missing_names = [r.name for r in completeness["missing"]]
        invalid_names = [ad.requirement.name for ad in completeness["invalid"]]
        if missing_names:
            reasons.append(f"Missing documents: {', '.join(missing_names)}")
        if invalid_names:
            reasons.append(f"Invalid documents: {', '.join(invalid_names)}")
        outcome = ScreeningResult.Outcome.FLAG

    result, _ = ScreeningResult.objects.update_or_create(
        application=application,
        defaults={"outcome": outcome, "reasons": reasons},
    )
    return result
