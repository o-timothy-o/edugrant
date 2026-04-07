"""Seed SINAG and SPARK programs with document requirements and rules. Run: python manage.py seed_programs"""

from django.core.management.base import BaseCommand

from programs.models import DocumentRequirement, Program, ProgramRule


def seed_program(name, program_type, doc_requirements, rules):
    """Create or get program and add requirements/rules if missing."""
    program, created = Program.objects.get_or_create(
        name=name,
        defaults={
            "program_type": program_type,
            "status": Program.Status.ACTIVE,
            "application_frequency": "per batch / as announced",
        },
    )
    added_docs = 0
    for order, (doc_name, required) in enumerate(doc_requirements, 1):
        _, doc_created = DocumentRequirement.objects.get_or_create(
            program=program,
            name=doc_name,
            defaults={"required": required, "display_order": order},
        )
        if doc_created:
            added_docs += 1

    added_rules = 0
    for order, (rule_name, rule_type, definition) in enumerate(rules, 1):
        _, rule_created = ProgramRule.objects.get_or_create(
            program=program,
            name=rule_name,
            defaults={"rule_type": rule_type, "definition": definition, "display_order": order},
        )
        if rule_created:
            added_rules += 1

    return created, added_docs, added_rules


class Command(BaseCommand):
    help = "Create SINAG and SPARK programs with document requirements and rules."

    def handle(self, *args, **options):
        created = []
        doc_requirements = [
            ("Valid ID", True),
            ("Barangay Certificate/Clearance", True),
            ("Certificate of Enrollment/Acceptance", True),
        ]
        rules = [
            ("No prior assistance", ProgramRule.RuleType.CONFLICT, {}),
            ("Documents complete", ProgramRule.RuleType.COMPLETENESS, {}),
        ]

        prog_created, docs_added, rules_added = seed_program(
            "SINAG", Program.ProgramType.SCHOLARSHIP, doc_requirements, rules
        )
        if prog_created:
            created.append("SINAG")
        if docs_added or rules_added:
            created.append(f"SINAG: {docs_added} docs, {rules_added} rules")

        prog_created, docs_added, rules_added = seed_program(
            "SPARK", Program.ProgramType.GRANT, doc_requirements, rules
        )
        if prog_created:
            created.append("SPARK")
        if docs_added or rules_added:
            created.append(f"SPARK: {docs_added} docs, {rules_added} rules")

        if created:
            self.stdout.write(self.style.SUCCESS(f"Seeded: {', '.join(created)}"))
        else:
            self.stdout.write("SINAG and SPARK already fully seeded.")
