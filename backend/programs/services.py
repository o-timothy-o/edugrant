"""Services for programs app: completeness, screening, etc."""

import re
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


def _extract_number(text):
    """Extract the first number from a string, stripping currency symbols and commas."""
    cleaned = re.sub(r"[₱,\sPHP]", "", str(text))
    match = re.search(r"[\d.]+", cleaned)
    return float(match.group()) if match else None


def _parse_date(text):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(text).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _get_actual_value(rule_field, profile, edu):
    """Return the applicant's actual value for a given rule field."""
    profile_fields = {
        "monthly_income", "residency_years", "barangay",
        "citizenship", "civil_status", "currently_working", "gender",
    }
    if rule_field in profile_fields:
        return getattr(profile, rule_field, "").strip() if profile else None
    if rule_field in ("course", "school", "graduation_date"):
        return edu.get(rule_field, "").strip()
    return None


def _evaluate_condition(rule, actual):
    """
    Evaluate one rule against the actual value.
    Returns (flagged: bool, reason: str).
    """
    field = rule.rule_field
    condition = rule.condition
    rule_value = rule.value.strip()
    numeric_fields = {"monthly_income", "residency_years"}
    date_fields = {"graduation_date"}

    if not actual:
        return False, ""

    if field in numeric_fields:
        actual_num = _extract_number(actual)
        try:
            rule_num = float(rule_value.replace(",", "").replace("₱", "").strip())
        except ValueError:
            return False, ""
        if actual_num is None:
            return False, ""
        if condition == ProgramRule.Condition.LTE and actual_num > rule_num:
            return True, f"₱{actual_num:,.2f} exceeds the maximum of ₱{rule_num:,.2f}"
        if condition == ProgramRule.Condition.GTE and actual_num < rule_num:
            return True, f"{actual_num:.0f} is below the minimum of {rule_num:.0f}"

    elif field in date_fields:
        actual_date = _parse_date(actual)
        rule_date = _parse_date(rule_value)
        if actual_date and rule_date:
            if condition == ProgramRule.Condition.DATE_AFTER and actual_date < rule_date:
                return True, f"Graduation date {actual} is before the required date {rule_value}"
            if condition == ProgramRule.Condition.DATE_BEFORE and actual_date > rule_date:
                return True, f"Graduation date {actual} is after {rule_value}"

    else:
        actual_lower = actual.lower()
        if condition == ProgramRule.Condition.EQUALS:
            if actual_lower != rule_value.lower():
                return True, f"'{actual}' does not match the required value '{rule_value}'"
        elif condition == ProgramRule.Condition.NOT_EQUALS:
            if actual_lower == rule_value.lower():
                return True, f"'{actual}' is not allowed"
        elif condition == ProgramRule.Condition.IN_LIST:
            allowed = [v.strip().lower() for v in rule_value.split(",")]
            if actual_lower not in allowed:
                return True, f"'{actual}' is not in the list of allowed values"

    return False, ""


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
        if not rule.rule_field or not rule.condition:
            continue
        actual = _get_actual_value(rule.rule_field, profile, edu)
        flagged, reason = _evaluate_condition(rule, actual)
        if flagged:
            reasons.append(f"{rule.name}: {reason}")
            outcome = ScreeningResult.Outcome.FLAG

    # 2. Conflict: applicant must not have a prior approved application for the same program
    prior_approved = Application.objects.filter(
        applicant=application.applicant,
        program=application.program,
        status=Application.ApplicationStatus.APPROVED,
    ).exclude(id=application.id)

    if prior_approved.exists():
        reasons.append("Applicant already has an approved application for this program")
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
