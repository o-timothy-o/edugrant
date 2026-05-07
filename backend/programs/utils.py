from django.core.mail import send_mail
from django.conf import settings


def _send(subject, body, recipient_email):
    if not recipient_email:
        return
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=True,
    )


def _applicant_name(application):
    profile = getattr(application.applicant, 'applicant_profile', None)
    return profile.full_name if profile and profile.full_name else application.applicant.username


def _program_name(application):
    return application.program.short_name or application.program.name


STATUS_EMAILS = {
    'submitted': (
        "We received your application – EduGrant",
        (
            "Hi {name},\n\n"
            "We have received your application for the {program} program. "
            "Our team will review it and get back to you soon.\n\n"
            "Thank you for applying!\n\n"
            "– EduGrant / CAYDO Carmona"
        ),
    ),
    'for_review': (
        "Your application is now in review – EduGrant",
        (
            "Hi {name},\n\n"
            "Your application for the {program} program is now in review by our team. "
            "We will notify you once a decision has been made.\n\n"
            "– EduGrant / CAYDO Carmona"
        ),
    ),
    'awaiting_physical': (
        "Action required: Submit your physical documents – EduGrant",
        (
            "Hi {name},\n\n"
            "Great news! Your online application for the {program} program has been approved. "
            "To complete the process, please visit the CAYDO office at Carmona Municipal Hall "
            "to submit your physical document requirements.\n\n"
            "To coordinate your visit, please reach out to us on Facebook:\n"
            "https://www.facebook.com/CAYDOCarmona\n\n"
            "– EduGrant / CAYDO Carmona"
        ),
    ),
    'approved': (
        "Congratulations! Your application is approved – EduGrant",
        (
            "Hi {name},\n\n"
            "Congratulations! Your application for the {program} program has been fully approved. "
            "We will be in touch with the next steps.\n\n"
            "– EduGrant / CAYDO Carmona"
        ),
    ),
    'rejected': (
        "Update on your EduGrant application",
        (
            "Hi {name},\n\n"
            "Thank you for applying for the {program} program. "
            "Unfortunately, your application was not approved for this cycle. "
            "We encourage you to apply again in the future.\n\n"
            "– EduGrant / CAYDO Carmona"
        ),
    ),
}


def send_status_notification(application, new_status):
    entry = STATUS_EMAILS.get(new_status)
    if not entry:
        return
    subject, body_template = entry
    name = _applicant_name(application)
    program = _program_name(application)
    _send(subject, body_template.format(name=name, program=program), application.applicant.email)


def send_welcome_email(user):
    _send(
        subject="Welcome to EduGrant!",
        body=(
            f"Hi {user.username},\n\n"
            "Welcome to EduGrant! Your account has been successfully created.\n\n"
            "You can now log in and apply for available scholarship and grant programs "
            "offered by CAYDO Carmona.\n\n"
            "If you have any questions, feel free to reach out to us on Facebook:\n"
            "https://www.facebook.com/CAYDOCarmona\n\n"
            "– EduGrant / CAYDO Carmona"
        ),
        recipient_email=user.email,
    )


def send_document_invalid_notification(application, requirement_name, issue_notes):
    name = _applicant_name(application)
    program = _program_name(application)
    note_line = f"\nReason: {issue_notes}\n" if issue_notes else ""
    _send(
        subject="Action required: Document issue on your application – EduGrant",
        body=(
            f"Hi {name},\n\n"
            f"There is an issue with a document you submitted for the {program} program.\n\n"
            f"Document: {requirement_name}\n"
            f"Status: Invalid{note_line}\n"
            "Please log in to your EduGrant account to review the issue and re-upload "
            "a corrected copy if needed.\n\n"
            "– EduGrant / CAYDO Carmona"
        ),
        recipient_email=application.applicant.email,
    )
