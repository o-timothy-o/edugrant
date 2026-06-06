from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

from accounts.views import StaffLoginView
from .views import (
    about_view, home, admin_dashboard_view, users_list_view, applicants_list_view,
    reports_view, program_list_view, add_program_view, edit_program_view,
    delete_program_view, archive_application_view, restore_application_view,
    archive_program_view, restore_program_view, archived_list_view,
    export_applications_csv, export_programs_csv, export_applicants_csv,
    view_applications_report, view_programs_report, view_applicants_report,
    program_rules_view, edit_rule_view, delete_rule_view, all_applications_view,
    screening_analytics_view, rejection_reasons_view,
    export_screening_csv, export_rejection_reasons_csv,
    view_screening_report, view_rejection_reasons_report,
)

urlpatterns = [
    path("", home, name="home"),
    path("about/", about_view, name="about"),
    path("dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("applicants/", users_list_view, name="users_list"),
    path("applications/", applicants_list_view, name="applicants_list"),
    path("applications/all/", all_applications_view, name="all_applications"),
    path("applications/<int:application_id>/archive/", archive_application_view, name="archive_application"),
    path("applications/<int:application_id>/restore/", restore_application_view, name="restore_application"),
    path("reports/", reports_view, name="reports"),
    path("reports/export/applications/", export_applications_csv, name="export_applications_csv"),
    path("reports/export/programs/", export_programs_csv, name="export_programs_csv"),
    path("reports/export/applicants/", export_applicants_csv, name="export_applicants_csv"),
    path("reports/view/applications/", view_applications_report, name="view_applications_report"),
    path("reports/view/programs/", view_programs_report, name="view_programs_report"),
    path("reports/view/applicants/", view_applicants_report, name="view_applicants_report"),
    path("reports/screening/", screening_analytics_view, name="screening_analytics"),
    path("reports/rejection-reasons/", rejection_reasons_view, name="rejection_reasons"),
    path("reports/export/screening/", export_screening_csv, name="export_screening_csv"),
    path("reports/export/rejection-reasons/", export_rejection_reasons_csv, name="export_rejection_reasons_csv"),
    path("reports/view/screening/", view_screening_report, name="view_screening_report"),
    path("reports/view/rejection-reasons/", view_rejection_reasons_report, name="view_rejection_reasons_report"),
    path("manage/programs/", program_list_view, name="program_list"),
    path("manage/programs/add/", add_program_view, name="add_program"),
    path("manage/programs/<int:program_id>/edit/", edit_program_view, name="edit_program"),
    path("manage/programs/<int:program_id>/delete/", delete_program_view, name="delete_program"),
    path("manage/programs/<int:program_id>/rules/", program_rules_view, name="program_rules"),
    path("manage/programs/<int:program_id>/rules/<int:rule_id>/edit/", edit_rule_view, name="edit_rule"),
    path("manage/programs/<int:program_id>/rules/<int:rule_id>/delete/", delete_rule_view, name="delete_rule"),
    path("manage/programs/<int:program_id>/archive/", archive_program_view, name="archive_program"),
    path("manage/programs/<int:program_id>/restore/", restore_program_view, name="restore_program"),
    path("manage/archived/", archived_list_view, name="archived_list"),
    # Hidden staff login — not linked from the public site
    path("caydo-portal/", StaffLoginView.as_view(), name="staff_login"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("programs/", include("programs.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
