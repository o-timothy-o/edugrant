from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

from accounts.views import StaffLoginView
from .views import (
    home, admin_dashboard_view, users_list_view, applicants_list_view,
    reports_view, program_list_view, add_program_view, edit_program_view,
    delete_program_view, archive_application_view, restore_application_view,
    archive_program_view, restore_program_view, archived_list_view,
)

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("applicants/", users_list_view, name="users_list"),
    path("applications/", applicants_list_view, name="applicants_list"),
    path("applications/<int:application_id>/archive/", archive_application_view, name="archive_application"),
    path("applications/<int:application_id>/restore/", restore_application_view, name="restore_application"),
    path("reports/", reports_view, name="reports"),
    path("manage/programs/", program_list_view, name="program_list"),
    path("manage/programs/add/", add_program_view, name="add_program"),
    path("manage/programs/<int:program_id>/edit/", edit_program_view, name="edit_program"),
    path("manage/programs/<int:program_id>/delete/", delete_program_view, name="delete_program"),
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
