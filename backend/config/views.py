import csv
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from programs.models import Application, Program, ProgramRule, ScreeningResult
from programs.forms import ProgramForm, DocumentRequirementFormSet

User = get_user_model()

_MONTHS = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]


def _get_filter_params(request):
    return (
        request.GET.get('filter_type', ''),
        request.GET.get('year', ''),
        request.GET.get('month', ''),
        request.GET.get('from_date', ''),
        request.GET.get('to_date', ''),
    )


def _date_filter(filter_type, year, month, from_date, to_date, field='created_at'):
    f = Q()
    if filter_type == 'year' and year:
        try:
            f = Q(**{f'{field}__year': int(year)})
        except ValueError:
            pass
    elif filter_type == 'month' and year and month:
        try:
            f = Q(**{f'{field}__year': int(year), f'{field}__month': int(month)})
        except ValueError:
            pass
    elif filter_type == 'range':
        if from_date:
            f &= Q(**{f'{field}__date__gte': from_date})
        if to_date:
            f &= Q(**{f'{field}__date__lte': to_date})
    return f


def _filter_label(filter_type, year, month, from_date, to_date):
    if filter_type == 'year' and year:
        return f'Year {year}'
    if filter_type == 'month' and year and month:
        try:
            return f'{_MONTHS[int(month)]} {year}'
        except (ValueError, IndexError):
            pass
    if filter_type == 'range':
        parts = []
        if from_date:
            parts.append(f'From {from_date}')
        if to_date:
            parts.append(f'To {to_date}')
        if parts:
            return ' — '.join(parts)
    return 'All Time'


def about_view(request):
    return render(request, 'about.html')


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

    qs = (
        Application.objects
        .filter(is_archived=False)
        .select_related('applicant', 'program')
        .order_by('-created_at')
    )

    if program_filter:
        qs = qs.filter(program__name=program_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(
            Q(applicant__email__icontains=search) |
            Q(applicant__first_name__icontains=search) |
            Q(applicant__last_name__icontains=search)
        )

    programs = Program.objects.filter(is_archived=False)

    PAGE_SIZE = 20
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    offset = (page - 1) * PAGE_SIZE
    batch = list(qs[offset:offset + PAGE_SIZE + 1])
    has_next = len(batch) > PAGE_SIZE
    applications = batch[:PAGE_SIZE]

    context = {
        'applications': applications,
        'programs': programs,
        'program_filter': program_filter,
        'status_filter': status_filter,
        'search': search,
        'page': page,
        'has_prev': page > 1,
        'has_next': has_next,
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


def _rule_choices():
    return {
        'rule_type_choices': ProgramRule.RuleType.choices,
        'rule_field_choices': ProgramRule.RuleField.choices,
        'condition_choices': ProgramRule.Condition.choices,
    }


@staff_member_required(login_url="staff_login")
def program_rules_view(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        rule_type = request.POST.get('rule_type', '')
        rule_field = request.POST.get('rule_field', '')
        condition = request.POST.get('condition', '')
        value = request.POST.get('value', '').strip()
        display_order = request.POST.get('display_order', 0) or 0
        if name and rule_type:
            ProgramRule.objects.create(
                program=program, name=name, rule_type=rule_type,
                rule_field=rule_field, condition=condition,
                value=value, display_order=display_order,
            )
            messages.success(request, f'Rule "{name}" added.')
        return redirect('program_rules', program_id=program_id)
    context = {
        'program': program,
        'rules': program.rules.all(),
        **_rule_choices(),
    }
    return render(request, 'programs/program_rules.html', context)


@staff_member_required(login_url="staff_login")
def edit_rule_view(request, program_id, rule_id):
    program = get_object_or_404(Program, id=program_id)
    rule = get_object_or_404(ProgramRule, id=rule_id, program=program)
    if request.method == 'POST':
        rule.name = request.POST.get('name', '').strip()
        rule.rule_type = request.POST.get('rule_type', '')
        rule.rule_field = request.POST.get('rule_field', '')
        rule.condition = request.POST.get('condition', '')
        rule.value = request.POST.get('value', '').strip()
        rule.display_order = request.POST.get('display_order', 0) or 0
        rule.save()
        messages.success(request, f'Rule "{rule.name}" updated.')
        return redirect('program_rules', program_id=program_id)
    context = {
        'program': program,
        'rules': program.rules.all(),
        'editing_rule': rule,
        **_rule_choices(),
    }
    return render(request, 'programs/program_rules.html', context)


@staff_member_required(login_url="staff_login")
def delete_rule_view(request, program_id, rule_id):
    rule = get_object_or_404(ProgramRule, id=rule_id, program__id=program_id)
    if request.method == 'POST':
        name = rule.name
        rule.delete()
        messages.success(request, f'Rule "{name}" deleted.')
    return redirect('program_rules', program_id=program_id)


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
    filter_type, year, month, from_date, to_date = _get_filter_params(request)
    df = _date_filter(filter_type, year, month, from_date, to_date)
    label = _filter_label(filter_type, year, month, from_date, to_date)

    year_vals = Application.objects.values_list('created_at__year', flat=True).distinct().order_by('-created_at__year')
    available_years = list(year_vals) or [timezone.now().year]

    monthly_qs = (
        Application.objects
        .filter(df)
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
        base = Application.objects.filter(df, program=prog)
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

    total_applications = Application.objects.filter(df).exclude(status='draft').count()
    total_approved = Application.objects.filter(df, status__in=['approved', 'awaiting_physical']).count()
    total_rejected = Application.objects.filter(df, status='rejected').count()
    total_pending = Application.objects.filter(df, status__in=['submitted', 'for_review']).count()

    context = {
        'monthly_data': monthly_data,
        'max_monthly': max_monthly,
        'all_program_stats': all_program_stats,
        'total_applications': total_applications,
        'total_approved': total_approved,
        'total_rejected': total_rejected,
        'total_pending': total_pending,
        'filter_type': filter_type,
        'active_year': year,
        'active_month': month,
        'active_from_date': from_date,
        'active_to_date': to_date,
        'filter_label': label,
        'available_years': available_years,
    }
    return render(request, 'reports.html', context)


@staff_member_required(login_url="staff_login")
def all_applications_view(request):
    qs = (
        Application.objects
        .filter(is_archived=False)
        .exclude(status='draft')
        .select_related('applicant', 'program', 'screening_result')
        .order_by('-created_at')
    )

    status_filter  = request.GET.get('status', '')
    program_filter = request.GET.get('program', '')
    search         = request.GET.get('q', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if program_filter:
        qs = qs.filter(program_id=program_filter)
    if search:
        qs = qs.filter(
            Q(applicant__first_name__icontains=search) |
            Q(applicant__last_name__icontains=search) |
            Q(applicant__email__icontains=search)
        )

    programs = Program.objects.filter(is_archived=False).order_by('name')
    status_choices = [s for s in Application.ApplicationStatus.choices if s[0] != 'draft']

    PAGE_SIZE = 20
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    offset = (page - 1) * PAGE_SIZE
    batch = list(qs[offset:offset + PAGE_SIZE + 1])
    has_next = len(batch) > PAGE_SIZE
    applications = batch[:PAGE_SIZE]

    context = {
        'applications': applications,
        'programs': programs,
        'status_choices': status_choices,
        'status_filter': status_filter,
        'program_filter': program_filter,
        'search': search,
        'page': page,
        'has_prev': page > 1,
        'has_next': has_next,
    }
    return render(request, 'all_applications.html', context)


@staff_member_required(login_url="staff_login")
def admin_dashboard_view(request):
    # Single aggregate query replaces 6 individual COUNT queries
    app_stats = Application.objects.filter(is_archived=False).aggregate(
        total=Count('id'),
        submitted=Count('id', filter=Q(status='submitted')),
        for_review=Count('id', filter=Q(status='for_review')),
        approved=Count('id', filter=Q(status__in=['approved', 'awaiting_physical'])),
        rejected=Count('id', filter=Q(status='rejected')),
        draft=Count('id', filter=Q(status='draft')),
    )

    # Single annotated query replaces N per-program COUNT queries
    program_counts = [
        {'program': p, 'count': p.app_count}
        for p in Program.objects.filter(is_archived=False).annotate(
            app_count=Count('applications', filter=Q(applications__is_archived=False))
        ).order_by('name')
    ]

    total_applicants = User.objects.filter(is_staff=False).count()

    recent_applications = Application.objects.filter(is_archived=False).select_related(
        'applicant', 'program'
    ).order_by('-created_at')[:10]

    context = {
        'total_applicants': total_applicants,
        'total_applications': app_stats['total'],
        'program_counts': program_counts,
        'status_counts': {
            'submitted': app_stats['submitted'],
            'for_review': app_stats['for_review'],
            'approved': app_stats['approved'],
            'rejected': app_stats['rejected'],
            'draft': app_stats['draft'],
        },
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


@staff_member_required(login_url="staff_login")
def view_applications_report(request):
    filter_type, year, month, from_date, to_date = _get_filter_params(request)
    df = _date_filter(filter_type, year, month, from_date, to_date)
    label = _filter_label(filter_type, year, month, from_date, to_date)

    applications = (
        Application.objects
        .filter(df, is_archived=False)
        .exclude(status='draft')
        .select_related('applicant', 'program', 'applicant__applicant_profile')
        .order_by('-created_at')
    )
    total = applications.count()
    context = {
        'applications': applications,
        'report_date': timezone.now(),
        'filter_label': label,
        'total': total,
        'total_approved': applications.filter(status='approved').count(),
        'total_rejected': applications.filter(status='rejected').count(),
        'total_pending': applications.filter(status__in=['submitted', 'for_review']).count(),
    }
    return render(request, 'reports/applications_report.html', context)


@staff_member_required(login_url="staff_login")
def view_programs_report(request):
    filter_type, year, month, from_date, to_date = _get_filter_params(request)
    df = _date_filter(filter_type, year, month, from_date, to_date)
    label = _filter_label(filter_type, year, month, from_date, to_date)

    programs_data = []
    for prog in Program.objects.filter(is_archived=False).order_by('name'):
        base = Application.objects.filter(df, program=prog)
        total = base.count()
        approved = base.filter(status='approved').count()
        rejected = base.filter(status='rejected').count()
        pending = base.filter(status__in=['submitted', 'for_review']).count()
        draft = base.filter(status='draft').count()
        programs_data.append({
            'program': prog,
            'total': total,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'draft': draft,
            'approval_rate': round(approved / total * 100, 1) if total else 0,
        })
    context = {
        'programs_data': programs_data,
        'report_date': timezone.now(),
        'filter_label': label,
    }
    return render(request, 'reports/programs_report.html', context)


@staff_member_required(login_url="staff_login")
def view_applicants_report(request):
    filter_type, year, month, from_date, to_date = _get_filter_params(request)
    df = _date_filter(filter_type, year, month, from_date, to_date, field='date_joined')
    label = _filter_label(filter_type, year, month, from_date, to_date)

    users = (
        User.objects.filter(df, is_staff=False)
        .select_related('applicant_profile')
        .annotate(application_count=Count('applications'))
        .order_by('-date_joined')
    )
    context = {
        'users': users,
        'report_date': timezone.now(),
        'filter_label': label,
        'total': users.count(),
    }
    return render(request, 'reports/applicants_report.html', context)


def _screening_by_program_data(program_filter=''):
    all_programs = Program.objects.filter(is_archived=False).order_by('name')
    programs_to_show = all_programs.filter(id=program_filter) if program_filter else all_programs
    result = []
    for prog in programs_to_show:
        s_pass = ScreeningResult.objects.filter(application__program=prog, outcome='pass').count()
        s_flag = ScreeningResult.objects.filter(application__program=prog, outcome='flag').count()
        s_total = s_pass + s_flag
        result.append({
            'program': prog,
            'pass': s_pass,
            'flag': s_flag,
            'total': s_total,
            'pass_rate': round(s_pass / s_total * 100) if s_total else 0,
            'flag_rate': round(s_flag / s_total * 100) if s_total else 0,
        })
    return result


@staff_member_required(login_url="staff_login")
def screening_analytics_view(request):
    filter_type, year, month, from_date, to_date = _get_filter_params(request)
    df = _date_filter(filter_type, year, month, from_date, to_date)
    label = _filter_label(filter_type, year, month, from_date, to_date)
    program_filter = request.GET.get('program', '')

    year_vals = Application.objects.values_list('created_at__year', flat=True).distinct().order_by('-created_at__year')
    available_years = list(year_vals) or [timezone.now().year]

    all_programs = Program.objects.filter(is_archived=False).order_by('name')
    screening_by_program = _screening_by_program_data(program_filter)

    base_monthly_qs = ScreeningResult.objects.filter(df)
    if program_filter:
        base_monthly_qs = base_monthly_qs.filter(application__program_id=program_filter)
    screening_monthly_qs = (
        base_monthly_qs
        .annotate(month=TruncMonth('created_at'))
        .values('month', 'outcome')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    screening_monthly_map = {}
    for row in screening_monthly_qs:
        key = row['month']
        if key not in screening_monthly_map:
            screening_monthly_map[key] = {'month_label': key.strftime('%b %Y') if key else '', 'pass': 0, 'flag': 0}
        screening_monthly_map[key][row['outcome']] = row['count']
    screening_monthly_data = sorted(screening_monthly_map.values(), key=lambda x: x['month_label'])

    context = {
        'screening_by_program': screening_by_program,
        'screening_monthly_data': screening_monthly_data,
        'all_programs': all_programs,
        'program_filter': program_filter,
        'filter_type': filter_type,
        'active_year': year,
        'active_month': month,
        'active_from_date': from_date,
        'active_to_date': to_date,
        'filter_label': label,
        'available_years': available_years,
    }
    return render(request, 'reports/screening.html', context)


@staff_member_required(login_url="staff_login")
def rejection_reasons_view(request):
    filter_type, year, month, from_date, to_date = _get_filter_params(request)
    df = _date_filter(filter_type, year, month, from_date, to_date)
    label = _filter_label(filter_type, year, month, from_date, to_date)
    program_filter = request.GET.get('program', '')

    year_vals = Application.objects.values_list('created_at__year', flat=True).distinct().order_by('-created_at__year')
    available_years = list(year_vals) or [timezone.now().year]

    all_programs = Program.objects.filter(is_archived=False).order_by('name')
    REJECTION_LABELS = dict(Application.RejectionReason.choices)
    rejected_apps = Application.objects.filter(df, status='rejected')
    if program_filter:
        rejected_apps = rejected_apps.filter(program_id=program_filter)

    reason_counter = {}
    for app in rejected_apps:
        for reason in (app.rejection_reason or []):
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
    total_rejected = rejected_apps.count()
    rejection_reason_data = sorted(
        [
            {
                'reason': REJECTION_LABELS.get(r, r),
                'count': c,
                'pct': round(c / total_rejected * 100) if total_rejected else 0,
            }
            for r, c in reason_counter.items()
        ],
        key=lambda x: x['count'],
        reverse=True,
    )

    context = {
        'rejection_reason_data': rejection_reason_data,
        'total_rejected': total_rejected,
        'all_programs': all_programs,
        'program_filter': program_filter,
        'filter_type': filter_type,
        'active_year': year,
        'active_month': month,
        'active_from_date': from_date,
        'active_to_date': to_date,
        'filter_label': label,
        'available_years': available_years,
    }
    return render(request, 'reports/rejection_reasons.html', context)


@staff_member_required(login_url="staff_login")
def export_screening_csv(request):
    program_filter = request.GET.get('program', '')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="screening_outcomes.csv"'
    writer = csv.writer(response)
    writer.writerow(['Program', 'Pass', 'Flag', 'Total', 'Pass Rate (%)', 'Flag Rate (%)'])
    for row in _screening_by_program_data(program_filter):
        writer.writerow([
            row['program'].name,
            row['pass'], row['flag'], row['total'],
            row['pass_rate'], row['flag_rate'],
        ])
    return response


@staff_member_required(login_url="staff_login")
def export_rejection_reasons_csv(request):
    filter_type, year, month, from_date, to_date = _get_filter_params(request)
    df = _date_filter(filter_type, year, month, from_date, to_date)
    program_filter = request.GET.get('program', '')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rejection_reasons.csv"'
    writer = csv.writer(response)
    writer.writerow(['Reason', 'Count', 'Percentage (%)'])
    REJECTION_LABELS = dict(Application.RejectionReason.choices)
    rejected_apps = Application.objects.filter(df, status='rejected')
    if program_filter:
        rejected_apps = rejected_apps.filter(program_id=program_filter)
    reason_counter = {}
    for app in rejected_apps:
        for reason in (app.rejection_reason or []):
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
    total = rejected_apps.count()
    for r, c in sorted(reason_counter.items(), key=lambda x: x[1], reverse=True):
        writer.writerow([
            REJECTION_LABELS.get(r, r), c,
            round(c / total * 100, 1) if total else 0,
        ])
    return response


@staff_member_required(login_url="staff_login")
def view_screening_report(request):
    program_filter = request.GET.get('program', '')
    all_programs = Program.objects.filter(is_archived=False).order_by('name')
    selected_program = None
    if program_filter:
        selected_program = all_programs.filter(id=program_filter).first()
    context = {
        'screening_by_program': _screening_by_program_data(program_filter),
        'report_date': timezone.now(),
        'filter_label': selected_program.name if selected_program else 'All Programs',
    }
    return render(request, 'reports/screening_report.html', context)


@staff_member_required(login_url="staff_login")
def view_rejection_reasons_report(request):
    filter_type, year, month, from_date, to_date = _get_filter_params(request)
    df = _date_filter(filter_type, year, month, from_date, to_date)
    label = _filter_label(filter_type, year, month, from_date, to_date)
    program_filter = request.GET.get('program', '')
    REJECTION_LABELS = dict(Application.RejectionReason.choices)
    rejected_apps = Application.objects.filter(df, status='rejected')
    if program_filter:
        rejected_apps = rejected_apps.filter(program_id=program_filter)
    reason_counter = {}
    for app in rejected_apps:
        for reason in (app.rejection_reason or []):
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
    total_rejected = rejected_apps.count()
    rejection_reason_data = sorted(
        [
            {
                'reason': REJECTION_LABELS.get(r, r),
                'count': c,
                'pct': round(c / total_rejected * 100, 1) if total_rejected else 0,
            }
            for r, c in reason_counter.items()
        ],
        key=lambda x: x['count'],
        reverse=True,
    )
    context = {
        'rejection_reason_data': rejection_reason_data,
        'total_rejected': total_rejected,
        'report_date': timezone.now(),
        'filter_label': label,
    }
    return render(request, 'reports/rejection_reasons_report.html', context)


# ---------------------------------------------------------------------------
# Dataset Integrity Check
# ---------------------------------------------------------------------------

def _run_integrity_checks():
    from accounts.models import ApplicantProfile
    from programs.services import _extract_number

    ACTIVE = [
        Application.ApplicationStatus.SUBMITTED,
        Application.ApplicationStatus.FOR_REVIEW,
        Application.ApplicationStatus.APPROVED,
        Application.ApplicationStatus.AWAITING_PHYSICAL,
        Application.ApplicationStatus.REJECTED,
    ]
    RECORD_CAP = 20

    def check(dimension, name, passed, detail='', records=None):
        return {
            'dimension': dimension,
            'name': name,
            'passed': passed,
            'detail': detail,
            'records': records or [],
        }

    def app_label(a):
        prog = a.program.short_name or a.program.name
        return f"#{a.id} — {a.applicant.email} ({prog})"

    def review_url(app_id):
        return f"/programs/application/{app_id}/review/"

    results = []

    # — Completeness —
    active_ids = set(Application.objects.filter(status__in=ACTIVE).values_list('applicant_id', flat=True))
    profile_ids = set(ApplicantProfile.objects.filter(user_id__in=active_ids).values_list('user_id', flat=True))
    missing_ids = active_ids - profile_ids
    missing_profile_records = [
        {'label': u['email'], 'url': f"/applicants/?q={u['email']}"}
        for u in User.objects.filter(id__in=missing_ids).values('email')[:RECORD_CAP]
    ]
    results.append(check(
        'Completeness', 'All applicants have a profile record',
        len(missing_ids) == 0, f'{len(missing_ids)} applicant(s) missing a profile',
        missing_profile_records,
    ))

    blank_profiles = (
        ApplicantProfile.objects
        .filter(user_id__in=active_ids)
        .filter(Q(first_name='') | Q(last_name='') | Q(monthly_income='') | Q(residency_years=''))
        .select_related('user')[:RECORD_CAP]
    )
    blank_records = []
    for p in blank_profiles:
        missing_fields = [f for f, v in [('First Name', p.first_name), ('Last Name', p.last_name), ('Income', p.monthly_income), ('Residency', p.residency_years)] if not v]
        app = Application.objects.filter(applicant=p.user, status__in=ACTIVE).first()
        blank_records.append({
            'label': f"{p.user.email} — missing: {', '.join(missing_fields)}",
            'url': review_url(app.id) if app else None,
        })
    blank_count = ApplicantProfile.objects.filter(user_id__in=active_ids).filter(
        Q(first_name='') | Q(last_name='') | Q(monthly_income='') | Q(residency_years='')
    ).count()
    results.append(check(
        'Completeness', 'No blank critical fields (name, income, residency)',
        blank_count == 0, f'{blank_count} profile(s) with blank required fields',
        blank_records,
    ))

    no_date_qs = Application.objects.filter(status__in=ACTIVE, submitted_at__isnull=True).select_related('applicant', 'program')
    no_date_records = [{'label': app_label(a), 'url': review_url(a.id)} for a in no_date_qs[:RECORD_CAP]]
    results.append(check(
        'Completeness', 'All submitted applications have a submission date',
        no_date_qs.count() == 0, f'{no_date_qs.count()} application(s) missing submitted_at',
        no_date_records,
    ))

    # — Validity —
    profiles_qs = list(
        ApplicantProfile.objects.filter(user_id__in=active_ids)
        .select_related('user')
        .only('monthly_income', 'residency_years', 'user__email', 'user__id')
    )
    bad_income_records = []
    bad_res_records = []
    for p in profiles_qs:
        if p.monthly_income and _extract_number(p.monthly_income) is None:
            app = Application.objects.filter(applicant=p.user, status__in=ACTIVE).first()
            bad_income_records.append({
                'label': f"{p.user.email} — value: \"{p.monthly_income}\"",
                'url': review_url(app.id) if app else None,
            })
        if p.residency_years and _extract_number(p.residency_years) is None:
            app = Application.objects.filter(applicant=p.user, status__in=ACTIVE).first()
            bad_res_records.append({
                'label': f"{p.user.email} — value: \"{p.residency_years}\"",
                'url': review_url(app.id) if app else None,
            })
    results.append(check(
        'Validity', 'monthly_income is a parseable numeric value',
        len(bad_income_records) == 0, f'{len(bad_income_records)} profile(s) with unparseable income',
        bad_income_records[:RECORD_CAP],
    ))
    results.append(check(
        'Validity', 'residency_years is a parseable numeric value',
        len(bad_res_records) == 0, f'{len(bad_res_records)} profile(s) with unparseable residency',
        bad_res_records[:RECORD_CAP],
    ))

    valid_statuses = {s for s, _ in Application.ApplicationStatus.choices}
    bad_status_qs = Application.objects.exclude(status__in=valid_statuses).select_related('applicant', 'program')
    bad_status_records = [
        {'label': f"{app_label(a)} — status: \"{a.status}\"", 'url': review_url(a.id)}
        for a in bad_status_qs[:RECORD_CAP]
    ]
    results.append(check(
        'Validity', 'All application status values are valid',
        bad_status_qs.count() == 0, f'{bad_status_qs.count()} application(s) with invalid status',
        bad_status_records,
    ))

    # — Consistency —
    rejected_qs = Application.objects.filter(
        status=Application.ApplicationStatus.REJECTED
    ).select_related('applicant', 'program')
    no_reason_apps = [a for a in rejected_qs if not getattr(a, 'rejection_reason', None) and not a.remarks]
    no_reason_records = [
        {'label': app_label(a), 'url': review_url(a.id)}
        for a in no_reason_apps[:RECORD_CAP]
    ]
    results.append(check(
        'Consistency', 'All rejected applications have a recorded rejection reason',
        len(no_reason_apps) == 0, f'{len(no_reason_apps)} rejected application(s) with no reason',
        no_reason_records,
    ))

    missing_sr_qs = Application.objects.filter(
        status__in=ACTIVE, screening_result__isnull=True
    ).select_related('applicant', 'program')
    missing_sr_records = [{'label': app_label(a), 'url': review_url(a.id)} for a in missing_sr_qs[:RECORD_CAP]]
    results.append(check(
        'Consistency', 'All submitted applications have a screening result',
        missing_sr_qs.count() == 0, f'{missing_sr_qs.count()} application(s) missing a ScreeningResult',
        missing_sr_records,
    ))

    dup_approved_pairs = (
        Application.objects.filter(status=Application.ApplicationStatus.APPROVED)
        .values('applicant_id', 'program_id')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
    )
    dup_approved_records = []
    for pair in dup_approved_pairs[:RECORD_CAP]:
        u = User.objects.filter(id=pair['applicant_id']).values('email').first()
        p = Program.objects.filter(id=pair['program_id']).values('name', 'short_name').first()
        email = u['email'] if u else f"User #{pair['applicant_id']}"
        prog = (p['short_name'] or p['name']) if p else f"Program #{pair['program_id']}"
        dup_approved_records.append({
            'label': f"{email} — {prog} ({pair['cnt']} approved applications)",
            'url': f"/applicants/?q={email}",
        })
    results.append(check(
        'Consistency', 'No duplicate approved applications per applicant per program',
        dup_approved_pairs.count() == 0, f'{dup_approved_pairs.count()} pair(s) with duplicate approvals',
        dup_approved_records,
    ))

    # — Uniqueness —
    dup_email_qs = User.objects.values('email').annotate(cnt=Count('id')).filter(cnt__gt=1)
    dup_email_records = [
        {'label': f"{e['email']} ({e['cnt']} accounts)", 'url': f"/applicants/?q={e['email']}"}
        for e in dup_email_qs[:RECORD_CAP]
    ]
    results.append(check(
        'Uniqueness', 'No duplicate user email addresses',
        dup_email_qs.count() == 0, f'{dup_email_qs.count()} email(s) used by multiple accounts',
        dup_email_records,
    ))

    dup_sub_pairs = (
        Application.objects.filter(status__in=ACTIVE)
        .values('applicant_id', 'program_id')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
    )
    dup_sub_records = []
    for pair in dup_sub_pairs[:RECORD_CAP]:
        u = User.objects.filter(id=pair['applicant_id']).values('email').first()
        p = Program.objects.filter(id=pair['program_id']).values('name', 'short_name').first()
        email = u['email'] if u else f"User #{pair['applicant_id']}"
        prog = (p['short_name'] or p['name']) if p else f"Program #{pair['program_id']}"
        dup_sub_records.append({
            'label': f"{email} — {prog} ({pair['cnt']} submissions)",
            'url': f"/applicants/?q={email}",
        })
    results.append(check(
        'Uniqueness', 'No applicant submitted more than once to the same program',
        dup_sub_pairs.count() == 0, f'{dup_sub_pairs.count()} (applicant, program) pair(s) with multiple submissions',
        dup_sub_records,
    ))

    # — Referential Integrity —
    valid_prog_ids = set(Program.objects.values_list('id', flat=True))
    orphan_app_qs = Application.objects.exclude(program_id__in=valid_prog_ids).select_related('applicant')
    orphan_app_records = [
        {'label': f"#{a.id} — {a.applicant.email} (program #{a.program_id} not found)", 'url': None}
        for a in orphan_app_qs[:RECORD_CAP]
    ]
    results.append(check(
        'Referential Integrity', 'All applications reference an existing program',
        orphan_app_qs.count() == 0, f'{orphan_app_qs.count()} application(s) with missing program reference',
        orphan_app_records,
    ))

    valid_app_ids = set(Application.objects.values_list('id', flat=True))
    orphan_sr_qs = ScreeningResult.objects.exclude(application_id__in=valid_app_ids)
    orphan_sr_records = [
        {'label': f"ScreeningResult #{sr.id} (application #{sr.application_id} not found)", 'url': None}
        for sr in orphan_sr_qs[:RECORD_CAP]
    ]
    results.append(check(
        'Referential Integrity', 'All screening results reference an existing application',
        orphan_sr_qs.count() == 0, f'{orphan_sr_qs.count()} orphaned ScreeningResult(s)',
        orphan_sr_records,
    ))

    passed = sum(1 for r in results if r['passed'])
    dimensions = {}
    for r in results:
        dimensions.setdefault(r['dimension'], []).append(r)

    return {
        'dimensions': dimensions,
        'results': results,
        'total': len(results),
        'passed': passed,
        'failed': len(results) - passed,
    }


@staff_member_required(login_url="staff_login")
def integrity_check_view(request):
    data = _run_integrity_checks()
    return render(request, 'reports/integrity.html', {'data': data})
