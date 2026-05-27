"""Services for programs app: completeness, screening, etc."""

from datetime import datetime

from programs.models import (
    Application,
    ApplicationDocument,
    ProgramRule,
    ScreeningResult,
)


def get_application_completeness(application):
    program = application.program
    requirements = program.document_requirements.filter(required=True).order_by(
        "display_order", "name"
    )

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


def _parse_number(value):
    """Parse a string number, stripping currency symbols and commas. Returns float or None."""
    try:
        return float(str(value).replace(",", "").replace("₱", "").replace("PHP", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_date(value):
    """Parse a date string in common formats. Returns date or None."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _normalize_list(value):
    """Ensure value is a list of lowercase strings for comparison."""
    if isinstance(value, str):
        value = [value]
    return [str(v).strip().lower() for v in value]


def run_rule_evaluation(application):
    """
    Run rule evaluation: eligibility -> conflict -> completeness.
    Creates or updates ScreeningResult. Returns the ScreeningResult.
    """
    from accounts.models import ApplicantProfile

    reasons = []
    outcome = ScreeningResult.Outcome.PASS

    profile = ApplicantProfile.objects.filter(user=application.applicant).first()
    edu = application.educational_data or {}

    # 1. Eligibility rules
    for rule in application.program.rules.filter(rule_type=ProgramRule.RuleType.ELIGIBILITY):
        defn = rule.definition

        # Profile existence
        if defn.get("check_profile"):
            if not profile:
                reasons.append(f"{rule.name}: Applicant profile is missing")
                outcome = ScreeningResult.Outcome.FLAG

        if profile:
            # Maximum monthly income
            if "max_income" in defn:
                income = _parse_number(profile.monthly_income)
                max_val = _parse_number(defn["max_income"])
                if income is not None and max_val is not None and income > max_val:
                    reasons.append(
                        f"{rule.name}: Monthly income ₱{income:,.2f} exceeds maximum of ₱{max_val:,.2f}"
                    )
                    outcome = ScreeningResult.Outcome.FLAG

            # Minimum residency years
            if "min_residency_years" in defn:
                years = _parse_number(profile.residency_years)
                min_val = _parse_number(defn["min_residency_years"])
                if years is not None and min_val is not None and years < min_val:
                    reasons.append(
                        f"{rule.name}: Residency of {years:.0f} year(s) is below the minimum of {min_val:.0f} year(s)"
                    )
                    outcome = ScreeningResult.Outcome.FLAG

            # Required barangay (string or list)
            if "required_barangay" in defn:
                allowed = _normalize_list(defn["required_barangay"])
                if profile.barangay.strip().lower() not in allowed:
                    reasons.append(
                        f"{rule.name}: Barangay '{profile.barangay}' is not in the list of eligible barangays"
                    )
                    outcome = ScreeningResult.Outcome.FLAG

            # Required citizenship
            if "required_citizenship" in defn:
                required = str(defn["required_citizenship"]).strip().lower()
                if profile.citizenship.strip().lower() != required:
                    reasons.append(
                        f"{rule.name}: Citizenship '{profile.citizenship}' does not meet the requirement"
                    )
                    outcome = ScreeningResult.Outcome.FLAG

            # Required civil status (string or list)
            if "required_civil_status" in defn:
                allowed = _normalize_list(defn["required_civil_status"])
                if profile.civil_status.strip().lower() not in allowed:
                    reasons.append(
                        f"{rule.name}: Civil status '{profile.civil_status}' does not meet the requirement"
                    )
                    outcome = ScreeningResult.Outcome.FLAG

            # Employment — must not be currently working
            if defn.get("must_not_be_working"):
                if profile.currently_working.strip().lower() in ("yes", "true", "1"):
                    reasons.append(f"{rule.name}: Applicant must not be currently employed")
                    outcome = ScreeningResult.Outcome.FLAG

            # Required gender (string or list)
            if "required_gender" in defn:
                allowed = _normalize_list(defn["required_gender"])
                if profile.gender.strip().lower() not in allowed:
                    reasons.append(
                        f"{rule.name}: Gender '{profile.gender}' does not meet the requirement"
                    )
                    outcome = ScreeningResult.Outcome.FLAG

        # Educational data checks
        if "required_course" in defn:
            allowed = _normalize_list(defn["required_course"])
            course = edu.get("course", "").strip().lower()
            if not course or course not in allowed:
                reasons.append(
                    f"{rule.name}: Course '{edu.get('course', '')}' is not an eligible course"
                )
                outcome = ScreeningResult.Outcome.FLAG

        if "required_school" in defn:
            allowed = _normalize_list(defn["required_school"])
            school = edu.get("school", "").strip().lower()
            if not school or school not in allowed:
                reasons.append(
                    f"{rule.name}: School '{edu.get('school', '')}' is not an eligible school"
                )
                outcome = ScreeningResult.Outcome.FLAG

        if "graduation_date_after" in defn or "graduation_date_before" in defn:
            grad_date = _parse_date(edu.get("graduation_date", ""))
            if grad_date:
                if "graduation_date_after" in defn:
                    after = _parse_date(defn["graduation_date_after"])
                    if after and grad_date < after:
                        reasons.append(
                            f"{rule.name}: Graduation date is before the required date {defn['graduation_date_after']}"
                        )
                        outcome = ScreeningResult.Outcome.FLAG
                if "graduation_date_before" in defn:
                    before = _parse_date(defn["graduation_date_before"])
                    if before and grad_date > before:
                        reasons.append(
                            f"{rule.name}: Graduation date is after the required date {defn['graduation_date_before']}"
                        )
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
