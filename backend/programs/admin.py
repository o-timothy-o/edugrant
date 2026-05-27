from django.contrib import admin

from .models import (
    Application,
    ApplicationDocument,
    DocumentRequirement,
    Program,
    ProgramRule,
    ScreeningResult,
)


class DocumentRequirementInline(admin.TabularInline):
    model = DocumentRequirement
    extra = 1


class ProgramRuleInline(admin.TabularInline):
    model = ProgramRule
    extra = 0
    fields = ("name", "rule_type", "rule_field", "condition", "value", "display_order")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "program_type", "status", "application_frequency")
    list_filter = ("program_type", "status")
    inlines = [DocumentRequirementInline, ProgramRuleInline]


class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "program", "status", "submitted_at", "created_at")
    list_filter = ("program", "status")
    search_fields = ("applicant__username", "applicant__email")
    inlines = [ApplicationDocumentInline]

    actions = ["run_screening"]

    def get_inline_instances(self, request, obj=None):
        # Hide document inline when adding: the signal creates ApplicationDocuments.
        # Show it when editing so staff can update status/file.
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    @admin.action(description="Run rule evaluation")
    def run_screening(self, request, queryset):
        from programs.services import run_rule_evaluation

        for app in queryset:
            run_rule_evaluation(app)
        self.message_user(request, f"Screening run for {queryset.count()} application(s).")


@admin.register(DocumentRequirement)
class DocumentRequirementAdmin(admin.ModelAdmin):
    list_display = ("name", "program", "required", "display_order")
    list_filter = ("program", "required")


@admin.register(ProgramRule)
class ProgramRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "program", "rule_type", "rule_field", "condition", "value", "display_order")
    list_filter = ("program", "rule_type", "rule_field")
    fieldsets = (
        (None, {
            "fields": ("program", "name", "rule_type", "display_order"),
        }),
        ("Rule Definition", {
            "fields": ("rule_field", "condition", "value"),
            "description": (
                "Set the Field, Condition, and Value for this rule. "
                "Leave blank for Conflict and Completeness rule types (those run automatically)."
            ),
        }),
    )


@admin.register(ScreeningResult)
class ScreeningResultAdmin(admin.ModelAdmin):
    list_display = ("application", "outcome", "created_at")
    list_filter = ("outcome",)
