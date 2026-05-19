import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from programs.models import Application, Program, ScreeningResult
from programs.forms import ProgramForm, DocumentRequirementFormSet

User = get_user_model()


def home(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
    context = {}
    if request.user.is_authenticated:
        context['my_applications'] = Application.objects.filter(
            applicant=request.user, is_archived=False
        ).select_related('program')
        active_programs = Program.objects.filter(status='active', is_archived=False).order_by('name')
        context['featured_programs'] = active_programs[:3]
        context['total_programs'] = active_programs.count()
    return render(request, "home.html", context)


@staff_member_required(login_url="staff_login")
def users_list_view(request):
    search = request.GET.get('q', '').strip()
    users = User.objects.filter(is_staff=False).select_related('applicant_profile').annotate(
        application_count=Count('applications')
    ).order_by('-date_joined')
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(applicant_profile__full_name__icontains=search)
        )
    context = {
        'users': users,
        'total': users.count(),
        'search': search,
    }
    return render(request, 'users_list.html', context)


@staff_member_required(login_url="staff_login")
def applicants_list_view(request):
    program_filter = request.GET.get('program', '')
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()

    applications = Application.objects.filter(is_archived=False).select_related('applicant', 'program').order_by('-created_at')

    if program_filter:
        applications = applications.filter(program__name=program_filter)
    if status_filter:
        applications = applications.filter(status=status_filter)
    if search:
        applications = applications.filter(
            applicant__email__icontains=search
        ) | applications.filter(
            applicant__first_name__icontains=search
        ) | applications.filter(
            applicant__last_name__icontains=search
        )
        applications = applications.filter(is_archived=False).select_related('applicant', 'program').order_by('-created_at')

    programs = Program.objects.filter(is_archived=False)

    context = {
        'applications': applications,
        'programs': programs,
        'program_filter': program_filter,
        'status_filter': status_filter,
        'search': search,
        'total': applications.count(),
        'status_choices': Application.ApplicationStatus.choices,
    }
    return render(request, 'applicants_list.html', context)


@staff_member_required(login_url="staff_login")
def program_list_view(request):
    programs = Program.objects.filter(is_archived=False).prefetch_related('document_requirements').order_by('name')
    context = {'programs': programs}
    return render(request, 'programs/program_list.html', context)


@staff_member_required(login_url="staff_login")
def add_program_view(request):
    if request.method == 'POST':
        form = ProgramForm(request.POST)
        if form.is_valid():
            program = form.save()
            formset = DocumentRequirementFormSet(request.POST, instance=program)
            if formset.is_valid():
                formset.save()
            messages.success(request, f'Program "{program.name}" created successfully.')
            return redirect('program_list')
    else:
        form = ProgramForm()
        formset = DocumentRequirementFormSet()
    context = {'form': form, 'formset': formset}
    return render(request, 'programs/add_program.html', context)


@staff_member_required(login_url="staff_login")
def delete_program_view(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    if request.method == 'POST':
        name = program.name
        program.delete()
        messages.success(request, f'Program "{name}" has been deleted.')
        return redirect('program_list')
    return redirect('program_list')


@staff_member_required(login_url="staff_login")
def edit_program_view(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    if request.method == 'POST':
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            form.save()
            formset = DocumentRequirementFormSet(request.POST, instance=program)
            if formset.is_valid():
                formset.save()
            messages.success(request, f'Program "{program.name}" updated successfully.')
            return redirect('program_list')
    else:
        form = ProgramForm(instance=program)
        formset = DocumentRequirementFormSet(instance=program)
    context = {'form': form, 'formset': formset, 'program': program}
    return render(request, 'programs/edit_program.html', context)


@staff_member_required(login_url="staff_login")
def archive_application_view(request, application_id):
    if request.method == 'POST':
        application = get_object_or_404(Application, id=application_id)
        application.is_archived = True
        application.save()
        messages.success(request, 'Application has been archived.')
    return redirect('applicants_list')


@staff_member_required(login_url="staff_login")
def restore_application_view(request, application_id):
    if request.method == 'POST':
        application = get_object_or_404(Application, id=application_id)
        application.is_archived = False
        application.save()
        messages.success(request, 'Application has been restored.')
    return redirect('archived_list')


@staff_member_required(login_url="staff_login")
def archive_program_view(request, program_id):
    if request.method == 'POST':
        program = get_object_or_404(Program, id=program_id)
        program.is_archived = True
        program.save()
        messages.success(request, f'Program "{program.name}" has been archived.')
    return redirect('program_list')


@staff_member_required(login_url="staff_login")
def restore_program_view(request, program_id):
    if request.method == 'POST':
        program = get_object_or_404(Program, id=program_id)
        program.is_archived = False
        program.save()
        messages.success(request, f'Program "{program.name}" has been restored.')
    return redirect('archived_list')


@staff_member_required(login_url="staff_login")
def archived_list_view(request):
    archived_programs = Program.objects.filter(is_archived=True).order_by('name')
    archived_applications = Application.objects.filter(is_archived=True).select_related('applicant', 'program').order_by('-created_at')
    context = {
        'archived_programs': archived_programs,
        'archived_applications': archived_applications,
    }
    return render(request, 'archived.html', context)


@staff_member_required(login_url="staff_login")
def reports_view(request):
    # Monthly submissions (non-draft applications grouped by month)
    monthly_qs = (
        Application.objects
        .exclude(status='draft')
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    monthly_data = list(monthly_qs)
    max_monthly = max((d['count'] for d in monthly_data), default=1)
    for d in monthly_data:
        d['pct'] = round(d['count'] / max_monthly * 100)
        d['month_label'] = d['month'].strftime('%b %Y') if d['month'] else ''

    all_programs = Program.objects.filter(is_archived=False).order_by('name')
    all_program_stats = []
    for prog in all_programs:
        base = Application.objects.filter(program=prog)
        total = base.count()
        approved = base.filter(status='approved').count()
        rejected = base.filter(status='rejected').count()
        pending = base.filter(status__in=['submitted', 'for_review']).count()
        draft = base.filter(status='draft').count()
        all_program_stats.append({
            'program': prog,
            'total': total,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'draft': draft,
            'approval_rate': round(approved / total * 100) if total else 0,
            'rejection_rate': round(rejected / total * 100) if total else 0,
            'pending_rate': round(pending / total * 100) if total else 0,
            'draft_rate': round(draft / total * 100) if total else 0,
        })

    screening_pass = ScreeningResult.objects.filter(outcome='pass').count()
    screening_flag = ScreeningResult.objects.filter(outcome='flag').count()
    screening_total = screening_pass + screening_flag

    total_applications = Application.objects.exclude(status='draft').count()
    total_approved = Application.objects.filter(status='approved').count()
    total_rejected = Application.objects.filter(status='rejected').count()
    total_pending = Application.objects.filter(status__in=['submitted', 'for_review']).count()

    context = {
        'monthly_data': monthly_data,
        'max_monthly': max_monthly,
        'all_program_stats': all_program_stats,
        'screening_pass': screening_pass,
        'screening_flag': screening_flag,
        'screening_total': screening_total,
        'total_applications': total_applications,
        'total_approved': total_approved,
        'total_rejected': total_rejected,
        'total_pending': total_pending,
    }
    return render(request, 'reports.html', context)


@staff_member_required(login_url="staff_login")
def admin_dashboard_view(request):
    total_applicants = User.objects.filter(is_staff=False).count()
    total_applications = Application.objects.filter(is_archived=False).count()
    program_counts = [
        {'program': prog, 'count': Application.objects.filter(program=prog, is_archived=False).count()}
        for prog in Program.objects.filter(is_archived=False).order_by('name')
    ]

    status_counts = {
        'submitted': Application.objects.filter(status='submitted', is_archived=False).count(),
        'for_review': Application.objects.filter(status='for_review', is_archived=False).count(),
        'approved': Application.objects.filter(status='approved', is_archived=False).count(),
        'rejected': Application.objects.filter(status='rejected', is_archived=False).count(),
        'draft': Application.objects.filter(status='draft', is_archived=False).count(),
    }

    recent_applications = Application.objects.filter(is_archived=False).select_related(
        'applicant', 'program'
    ).order_by('-created_at')[:10]

    context = {
        'total_applicants': total_applicants,
        'total_applications': total_applications,
        'program_counts': program_counts,
        'status_counts': status_counts,
        'recent_applications': recent_applications,
    }
    return render(request, 'admin_dashboard.html', context)


@staff_member_required(login_url="staff_login")
def export_applications_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="applications.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Full Name', 'Email', 'Contact Number', 'Barangay', 'Address',
        'Program', 'Program Type', 'Status', 'Date Submitted',
    ])
    applications = (
        Application.objects
        .filter(is_archived=False)
        .exclude(status='draft')
        .select_related('applicant', 'program', 'applicant__applicant_profile')
        .order_by('-created_at')
    )
    for app in applications:
        profile = getattr(app.applicant, 'applicant_profile', None)
        writer.writerow([
            profile.full_name if profile else '',
            app.applicant.email,
            profile.contact_number if profile else '',
            profile.barangay if profile else '',
            profile.address if profile else '',
            app.program.name,
            app.program.get_program_type_display(),
            app.get_status_display(),
            app.created_at.strftime('%Y-%m-%d'),
        ])
    return response


@staff_member_required(login_url="staff_login")
def export_programs_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="program_summary.csv"'
    writer = csv.writer(response)
    writer.writerow(['Program', 'Type', 'Total', 'Approved', 'Rejected', 'Pending', 'Draft', 'Approval Rate (%)'])
    for prog in Program.objects.filter(is_archived=False).order_by('name'):
        base = Application.objects.filter(program=prog)
        total = base.count()
        approved = base.filter(status='approved').count()
        rejected = base.filter(status='rejected').count()
        pending = base.filter(status__in=['submitted', 'for_review']).count()
        draft = base.filter(status='draft').count()
        approval_rate = round(approved / total * 100, 1) if total else 0
        writer.writerow([
            prog.name,
            prog.get_program_type_display(),
            total, approved, rejected, pending, draft,
            f'{approval_rate}%',
        ])
    return response


@staff_member_required(login_url="staff_login")
def export_applicants_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="applicants.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Full Name', 'Email', 'Barangay', 'Address', 'Contact Number',
        'Gender', 'Civil Status', 'Monthly Income', 'Date Joined', 'Total Applications',
    ])
    users = (
        User.objects.filter(is_staff=False)
        .select_related('applicant_profile')
        .annotate(application_count=Count('applications'))
        .order_by('-date_joined')
    )
    for user in users:
        profile = getattr(user, 'applicant_profile', None)
        writer.writerow([
            profile.full_name if profile else '',
            user.email,
            profile.barangay if profile else '',
            profile.address if profile else '',
            profile.contact_number if profile else '',
            profile.gender if profile else '',
            profile.civil_status if profile else '',
            profile.monthly_income if profile else '',
            user.date_joined.strftime('%Y-%m-%d'),
            user.application_count,
        ])
    return response
