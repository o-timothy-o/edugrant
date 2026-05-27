from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Program, Application, DocumentRequirement, ApplicationDocument, ApplicationStatusLog
from .forms import ApplicationDocumentForm, FamilyCompositionForm
from .services import run_rule_evaluation
from .utils import send_status_notification, send_document_invalid_notification
from django.forms import formset_factory
from accounts.models import ApplicantProfile
import json

BARANGAY_CHOICES = [
    "Barangay 1 (Poblacion) - San Pablo",
    "Barangay 2 (Poblacion) - San Jose",
    "Barangay 3 (Poblacion) - San Jose",
    "Barangay 4 (Poblacion) - J.M. Loyola",
    "Barangay 5 (Poblacion) - J.M. Loyola",
    "Barangay 6 (Poblacion) - Magallanes",
    "Barangay 7 (Poblacion) - Magallanes",
    "Barangay 8 (Poblacion) - Rosario",
    "Bancal",
    "Cabilang Baybay",
    "Lantic",
    "Mabuhay",
    "Maduya",
    "Milagrosa",
]


def _save_step1_data(request, application):
    """Save Step 1 personal and educational data from POST."""
    profile, _ = ApplicantProfile.objects.get_or_create(user=request.user)
    profile.first_name = request.POST.get('first_name', '').strip()
    profile.middle_name = request.POST.get('middle_name', '').strip()
    profile.last_name = request.POST.get('last_name', '').strip()
    profile.address = request.POST.get('address', '').strip()
    profile.barangay = request.POST.get('barangay', '').strip()
    profile.residency_years = request.POST.get('residency', '').strip()
    profile.gender = request.POST.get('gender', '').strip()
    profile.civil_status = request.POST.get('civil_status', '').strip()
    profile.contact_number = request.POST.get('contact_number', '').strip()
    profile.currently_working = request.POST.get('working', '').strip()
    profile.religion = request.POST.get('religion', '').strip()
    profile.monthly_income = request.POST.get('monthly_income', '').strip()
    profile.save()

    max_rows = min(int(request.POST.get('school_row_max', '4')), 50)
    schools_attended = []
    for i in range(1, max_rows + 1):
        row = {
            'name': request.POST.get(f'school_name_{i}', '').strip(),
            'type': request.POST.get(f'school_type_{i}', '').strip(),
            'address': request.POST.get(f'school_address_{i}', '').strip(),
            'year': request.POST.get(f'school_year_{i}', '').strip(),
        }
        if any(row.values()):
            schools_attended.append(row)

    application.educational_data = {
        'course': request.POST.get('course', ''),
        'school': request.POST.get('school', ''),
        'school_address': request.POST.get('school_address', ''),
        'graduation_date': request.POST.get('graduation_date', ''),
        'exam_to_take': request.POST.get('exam_to_take', ''),
        'review_center_enrolled': request.POST.get('review_center_enrolled', ''),
        'review_center': request.POST.get('review_center', ''),
        'exam_date': request.POST.get('exam_date', ''),
        'schools_attended': schools_attended,
    }
    application.save()

@login_required
def spark_application_view(request):
    try:
        spark_program = Program.objects.get(name="SPARK")
        return redirect('programs:generic_application_step1', program_id=spark_program.id)
    except Program.DoesNotExist:
        return redirect('home')

@login_required
def spark_application_step2_view(request, application_id):
    try:
        spark_program = Program.objects.get(name="SPARK")
    except Program.DoesNotExist:
        # Handle case where SPARK program is not found
        return redirect('home')

    application = get_object_or_404(Application, id=application_id, applicant=request.user, program=spark_program)

    # Prevent re-submission of an already-submitted application
    if application.status != 'draft':
        return redirect('programs:application_detail', application_id=application.id)

    document_requirements = DocumentRequirement.objects.filter(program=spark_program)
    FamilyCompositionFormSet = formset_factory(FamilyCompositionForm, extra=2)

    if request.method == 'POST':
        family_formset = FamilyCompositionFormSet(request.POST)
        document_forms = [ApplicationDocumentForm(request.POST, request.FILES, prefix=str(req.id)) for req in document_requirements]

        if family_formset.is_valid():
            family_data = [form for form in family_formset.cleaned_data if form]
            application.remarks = json.dumps(family_data)
            application.save()

        for i, form in enumerate(document_forms):
            if form.is_valid() and 'file' in request.FILES:
                doc, created = ApplicationDocument.objects.get_or_create(application=application, requirement=document_requirements[i])
                doc.file = form.cleaned_data['file']
                doc.status = 'submitted'
                doc.save()

        application.status = 'for_review'
        application.save()
        ApplicationStatusLog.objects.create(application=application, status='for_review', changed_by=request.user)
        send_status_notification(application, 'for_review')
        run_rule_evaluation(application)

        # Render the same page with the success flag instead of redirecting
        context = {
            'program': spark_program,
            'document_requirements': document_requirements,
            'application': application,
            'family_composition_forms': family_formset,
            'document_forms': document_forms,
            'doc_forms_and_reqs': zip(document_forms, document_requirements),
            'application_submitted': True,
        }
        return render(request, 'programs/spark_application_step2.html', context)

    else:
        family_composition_forms = FamilyCompositionFormSet()
        document_forms = [ApplicationDocumentForm(prefix=str(req.id)) for req in document_requirements]


    context = {
        'program': spark_program,
        'document_requirements': document_requirements,
        'application': application,
        'family_composition_forms': family_composition_forms,
        'document_forms': document_forms,
        'doc_forms_and_reqs': zip(document_forms, document_requirements)
    }

    return render(request, 'programs/spark_application_step2.html', context)

@login_required
def sinag_application_step2_view(request, application_id):
    try:
        sinag_program = Program.objects.get(name="SINAG")
    except Program.DoesNotExist:
        # Handle case where SINAG program is not found
        return redirect('home')

    application = get_object_or_404(Application, id=application_id, applicant=request.user, program=sinag_program)

    # Prevent re-submission of an already-submitted application
    if application.status != 'draft':
        return redirect('programs:application_detail', application_id=application.id)

    document_requirements = DocumentRequirement.objects.filter(program=sinag_program)
    FamilyCompositionFormSet = formset_factory(FamilyCompositionForm, extra=2)

    if request.method == 'POST':
        family_formset = FamilyCompositionFormSet(request.POST)
        document_forms = [ApplicationDocumentForm(request.POST, request.FILES, prefix=str(req.id)) for req in document_requirements]

        if family_formset.is_valid():
            family_data = [form for form in family_formset.cleaned_data if form]
            application.remarks = json.dumps(family_data)
            application.save()

        for i, form in enumerate(document_forms):
            if form.is_valid() and 'file' in request.FILES:
                doc, created = ApplicationDocument.objects.get_or_create(application=application, requirement=document_requirements[i])
                doc.file = form.cleaned_data['file']
                doc.status = 'submitted'
                doc.save()

        application.status = 'for_review'
        application.save()
        ApplicationStatusLog.objects.create(application=application, status='for_review', changed_by=request.user)
        send_status_notification(application, 'for_review')
        run_rule_evaluation(application)

        # Render the same page with the success flag instead of redirecting
        context = {
            'program': sinag_program,
            'document_requirements': document_requirements,
            'application': application,
            'family_composition_forms': family_formset,
            'document_forms': document_forms,
            'doc_forms_and_reqs': zip(document_forms, document_requirements),
            'application_submitted': True,
        }
        return render(request, 'programs/sinag_application_step2.html', context)

    else:
        family_composition_forms = FamilyCompositionFormSet()
        document_forms = [ApplicationDocumentForm(prefix=str(req.id)) for req in document_requirements]


    context = {
        'program': sinag_program,
        'document_requirements': document_requirements,
        'application': application,
        'family_composition_forms': family_composition_forms,
        'document_forms': document_forms,
        'doc_forms_and_reqs': zip(document_forms, document_requirements)
    }

    return render(request, 'programs/sinag_application_step2.html', context)


@staff_member_required(login_url="staff_login")
def application_review_view(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    requirements = DocumentRequirement.objects.filter(program=application.program)
    doc_map = {doc.requirement_id: doc for doc in application.application_documents.all()}
    doc_statuses = [(req, doc_map.get(req.id)) for req in requirements]

    family_data = []
    if application.remarks:
        try:
            family_data = json.loads(application.remarks)
        except (json.JSONDecodeError, ValueError):
            family_data = []

    screening = None
    try:
        screening = application.screening_result
    except Exception:
        pass

    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ['approved', 'rejected', 'for_review', 'awaiting_physical']:
            application.status = action
            application.save()
            ApplicationStatusLog.objects.create(application=application, status=action, changed_by=request.user)
            send_status_notification(application, action)
            if action == 'for_review':
                run_rule_evaluation(application)
            messages.success(request, f'Application has been marked as {application.get_status_display()}.')
            return redirect('admin_dashboard')
        elif action == 'update_doc':
            doc_id = request.POST.get('doc_id')
            new_status = request.POST.get('new_status')
            notes = request.POST.get('issue_notes', '').strip()
            if doc_id and new_status in ['submitted', 'invalid', 'missing']:
                doc = get_object_or_404(ApplicationDocument, id=doc_id, application=application)
                doc.status = new_status
                doc.issue_notes = notes
                doc.save()
                run_rule_evaluation(application)
                if new_status == 'invalid':
                    send_document_invalid_notification(application, doc.requirement.name, notes)
                messages.success(request, 'Document status updated.')
            return redirect('programs:application_review', application_id=application.id)

    profile = getattr(application.applicant, 'applicant_profile', None)
    status_log_map = {}
    for log in application.status_logs.order_by('changed_at'):
        if log.status not in status_log_map:
            status_log_map[log.status] = log

    context = {
        'application': application,
        'doc_statuses': doc_statuses,
        'family_data': family_data,
        'screening': screening,
        'profile': profile,
        'educational_data': application.educational_data,
        'status_log_map': status_log_map,
    }
    return render(request, 'programs/application_review.html', context)


@login_required
def program_list_applicant_view(request):
    programs = Program.objects.filter(status='active', is_archived=False).order_by('name')
    user_app_program_ids = set(
        Application.objects.filter(
            applicant=request.user,
            status__in=['for_review', 'submitted'],
            is_archived=False,
        ).values_list('program_id', flat=True)
    )
    context = {
        'programs': programs,
        'user_app_program_ids': user_app_program_ids,
    }
    return render(request, 'programs/programs_list_applicant.html', context)


@login_required
def my_applications_view(request):
    applications = Application.objects.filter(
        applicant=request.user, is_archived=False
    ).select_related('program')
    return render(request, 'programs/my_applications.html', {'applications': applications})


@login_required
def application_detail_view(request, application_id):
    application = get_object_or_404(Application, id=application_id, applicant=request.user, is_archived=False)
    requirements = DocumentRequirement.objects.filter(program=application.program)
    doc_map = {doc.requirement_id: doc for doc in application.application_documents.all()}
    doc_statuses = [(req, doc_map.get(req.id)) for req in requirements]
    profile = getattr(request.user, 'applicant_profile', None)
    status_log_map = {}
    for log in application.status_logs.order_by('changed_at'):
        if log.status not in status_log_map:
            status_log_map[log.status] = log
    context = {
        'application': application,
        'doc_statuses': doc_statuses,
        'profile': profile,
        'educational_data': application.educational_data,
        'status_log_map': status_log_map,
    }
    return render(request, 'programs/application_detail.html', context)


@login_required
def generic_application_step1_view(request, program_id):
    program = get_object_or_404(Program, id=program_id, status='active')

    # Block re-apply if a submitted/for_review app exists
    existing = Application.objects.filter(
        applicant=request.user,
        program=program,
        status__in=['submitted', 'for_review'],
        is_archived=False,
    ).first()
    if existing:
        return render(request, 'programs/existing_application.html', {
            'application': existing,
            'program': program,
        })

    application, _ = Application.objects.get_or_create(
        applicant=request.user,
        program=program,
        status='draft',
        defaults={'status': 'draft'},
    )

    if request.method == 'POST':
        _save_step1_data(request, application)
        return redirect('programs:generic_application_step2', program_id=program.id, application_id=application.id)

    profile = getattr(request.user, 'applicant_profile', None)
    document_requirements = DocumentRequirement.objects.filter(program=program)
    context = {
        'program': program,
        'application': application,
        'profile': profile,
        'document_requirements': document_requirements,
        'barangay_choices': BARANGAY_CHOICES,
    }
    return render(request, 'programs/generic_application_step1.html', context)


@login_required
def generic_application_step2_view(request, program_id, application_id):
    program = get_object_or_404(Program, id=program_id)
    application = get_object_or_404(Application, id=application_id, applicant=request.user, program=program)

    if application.status != 'draft':
        return redirect('programs:application_detail', application_id=application.id)

    document_requirements = DocumentRequirement.objects.filter(program=program)
    document_forms = [ApplicationDocumentForm(prefix=str(req.id), file_required=req.required) for req in document_requirements]

    if request.method == 'POST':
        document_forms = [
            ApplicationDocumentForm(request.POST, request.FILES, prefix=str(req.id), file_required=req.required)
            for req in document_requirements
        ]
        all_docs_valid = all(form.is_valid() for form in document_forms)
        if not all_docs_valid:
            context = {
                'program': program,
                'application': application,
                'document_requirements': document_requirements,
                'doc_forms_and_reqs': zip(document_forms, document_requirements),
            }
            return render(request, 'programs/generic_application_step2.html', context)
        for i, form in enumerate(document_forms):
            if form.is_valid() and form.cleaned_data.get('file'):
                doc, _ = ApplicationDocument.objects.get_or_create(
                    application=application,
                    requirement=document_requirements[i],
                )
                doc.file = form.cleaned_data['file']
                doc.status = 'submitted'
                doc.save()

        application.status = 'for_review'
        application.save()
        ApplicationStatusLog.objects.create(application=application, status='for_review', changed_by=request.user)
        send_status_notification(application, 'for_review')
        run_rule_evaluation(application)

        context = {
            'program': program,
            'application': application,
            'document_requirements': document_requirements,
            'doc_forms_and_reqs': zip(document_forms, document_requirements),
            'application_submitted': True,
        }
        return render(request, 'programs/generic_application_step2.html', context)

    context = {
        'program': program,
        'application': application,
        'document_requirements': document_requirements,
        'doc_forms_and_reqs': zip(document_forms, document_requirements),
    }
    return render(request, 'programs/generic_application_step2.html', context)


@login_required
def sinag_application_view(request):
    try:
        sinag_program = Program.objects.get(name="SINAG")
        return redirect('programs:generic_application_step1', program_id=sinag_program.id)
    except Program.DoesNotExist:
        return redirect('home')
