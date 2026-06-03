"""Management command: generate bulk dummy applications for analytics testing."""

import random
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import ApplicantProfile
from programs.models import Application, ApplicationDocument, Program
from programs.services import run_rule_evaluation

User = get_user_model()

# ---------------------------------------------------------------------------
# Name pools
# ---------------------------------------------------------------------------

MALE_FIRST_NAMES = [
    "Jose", "Juan", "Carlo", "Mark", "Luis", "Ryan", "Leo", "Joel",
    "Dante", "Rico", "Jomar", "Rodel", "Arnel", "Edgar", "Ronnie",
    "Ramon", "Eduardo", "Rodrigo", "Antonio", "Fernando", "Roberto",
    "Ernesto", "Alfredo", "Renato", "Danilo", "Melvin", "Arnold",
    "Gilbert", "Harold", "Nestor", "Rogelio", "Victorino", "Cesar",
    "Noel", "Ricky", "Jeffrey", "Aldrin", "Jayson", "Marvin", "Erick",
    "Jerome", "Neil", "Alex", "Patrick", "Eugene", "Winston", "Gerry",
    "Raul", "Rolando", "Dario",
]

FEMALE_FIRST_NAMES = [
    "Maria", "Ana", "Liza", "Grace", "Rose", "Cris", "Faith", "Luz",
    "Alma", "Elena", "Nena", "Tess", "Gloria", "Marites", "Jasmin",
    "Rosario", "Erlinda", "Teresita", "Corazon", "Remedios", "Lourdes",
    "Evelyn", "Marilyn", "Norma", "Cecilia", "Felicitas", "Amelia",
    "Perla", "Violeta", "Nenita", "Luzviminda", "Natividad", "Milagros",
    "Florencia", "Carmela", "Rowena", "Sheila", "Melanie", "Christine",
    "Jennifer", "Michelle", "Kristine", "Joanna", "Patricia", "Vanessa",
    "Rhea", "Aileen", "Maricel", "Gemma", "Nora",
]

LAST_NAMES = [
    "Santos", "Reyes", "Cruz", "Bautista", "Ocampo", "Garcia", "Torres",
    "Ramos", "Flores", "De Leon", "Castro", "Mendoza", "Aquino", "Villanueva",
    "Salazar", "Ramirez", "Pascual", "Delos Santos", "Gonzales", "Jimenez",
    "Dela Cruz", "Fernandez", "Lopez", "Hernandez", "Perez", "Diaz",
    "Morales", "Aguilar", "Dela Torre", "Serrano", "Valdez", "Navarro",
    "Macaraeg", "Galang", "Manalo", "Tolentino", "Resurreccion", "Espiritu",
    "Ilagan", "Manalang", "Tibay", "Macapagal", "Buenaventura", "Mallari",
    "Pangan", "Quiambao", "Lingad", "Lacap", "Sangalang", "Pineda",
]

MIDDLE_NAMES = [
    "Santos", "Reyes", "Cruz", "Garcia", "Torres", "Ramos", "Flores",
    "Castro", "Mendoza", "Pascual", "Gonzales", "Lopez", "Fernandez",
    "Perez", "Morales", "Aguilar", "Serrano", "Valdez", "Navarro",
]

BARANGAYS = [
    "Bagumbayan", "Pag-asa", "Maligaya", "Masagana", "Silangan",
    "Bagong Pag-asa", "Malaya", "Kabayanan", "Sta. Cruz", "San Jose",
    "San Isidro", "Sto. Niño", "Sta. Maria", "San Pedro", "Poblacion",
    "Bagong Silang", "Kalikasan", "Kaibigan", "Mabuhay", "Pagkakaisa",
]

STREET_NAMES = [
    "Rizal St.", "Bonifacio St.", "Mabini St.", "Luna St.", "Aguinaldo St.",
    "Quezon Ave.", "Magsaysay Blvd.", "Osmena St.", "Roxas St.", "Laurel St.",
    "Sampaguita St.", "Rosal St.", "Camia St.", "Ilang-ilang St.", "Dahlia St.",
]

RELIGIONS = [
    "Roman Catholic", "Roman Catholic", "Roman Catholic", "Roman Catholic",
    "Iglesia ni Cristo", "Born Again Christian", "Baptist", "Seventh-day Adventist",
    "Aglipayan", "Islam",
]

# ---------------------------------------------------------------------------
# Profile scenarios
# ---------------------------------------------------------------------------

# SINAG rules: residency >= 10, income <= 25000, currently_working must be "No"

SINAG_APPROVED_PROFILES = [
    {"residency_years": "12", "monthly_income": "20000", "currently_working": "No"},
    {"residency_years": "15", "monthly_income": "18000", "currently_working": "No"},
    {"residency_years": "20", "monthly_income": "12000", "currently_working": "No"},
    {"residency_years": "10", "monthly_income": "24000", "currently_working": "No"},
    {"residency_years": "25", "monthly_income": "8000",  "currently_working": "No"},
    {"residency_years": "18", "monthly_income": "15000", "currently_working": "No"},
    {"residency_years": "30", "monthly_income": "22000", "currently_working": "No"},
]

SINAG_REJECTED_SCENARIOS = [
    # Income too high
    {
        "profile": {"residency_years": "12", "monthly_income": "28000", "currently_working": "No"},
        "rejection_reasons": ["income"],
    },
    {
        "profile": {"residency_years": "15", "monthly_income": "35000", "currently_working": "No"},
        "rejection_reasons": ["income"],
    },
    {
        "profile": {"residency_years": "20", "monthly_income": "30000", "currently_working": "No"},
        "rejection_reasons": ["income"],
    },
    # Residency too low
    {
        "profile": {"residency_years": "5",  "monthly_income": "20000", "currently_working": "No"},
        "rejection_reasons": ["residency"],
    },
    {
        "profile": {"residency_years": "8",  "monthly_income": "15000", "currently_working": "No"},
        "rejection_reasons": ["residency"],
    },
    {
        "profile": {"residency_years": "3",  "monthly_income": "18000", "currently_working": "No"},
        "rejection_reasons": ["residency"],
    },
    # Employed
    {
        "profile": {"residency_years": "12", "monthly_income": "20000", "currently_working": "Yes"},
        "rejection_reasons": ["employment"],
    },
    {
        "profile": {"residency_years": "15", "monthly_income": "18000", "currently_working": "Yes"},
        "rejection_reasons": ["employment"],
    },
    # Multiple failures
    {
        "profile": {"residency_years": "5",  "monthly_income": "30000", "currently_working": "No"},
        "rejection_reasons": ["income", "residency"],
    },
    {
        "profile": {"residency_years": "8",  "monthly_income": "20000", "currently_working": "Yes"},
        "rejection_reasons": ["residency", "employment"],
    },
    {
        "profile": {"residency_years": "5",  "monthly_income": "28000", "currently_working": "Yes"},
        "rejection_reasons": ["income", "residency", "employment"],
    },
]

# SPARK has no eligibility rules — rejections are admin-discretion

SPARK_APPROVED_PROFILES = [
    {"residency_years": "5",  "monthly_income": "50000", "currently_working": "Yes"},
    {"residency_years": "3",  "monthly_income": "35000", "currently_working": "Yes"},
    {"residency_years": "10", "monthly_income": "40000", "currently_working": "No"},
    {"residency_years": "2",  "monthly_income": "60000", "currently_working": "Yes"},
    {"residency_years": "7",  "monthly_income": "45000", "currently_working": "Yes"},
    {"residency_years": "1",  "monthly_income": "55000", "currently_working": "No"},
]

SPARK_REJECTED_SCENARIOS = [
    {
        "profile": {"residency_years": "5",  "monthly_income": "50000", "currently_working": "Yes"},
        "rejection_reasons": ["other"],
    },
    {
        "profile": {"residency_years": "3",  "monthly_income": "35000", "currently_working": "Yes"},
        "rejection_reasons": ["not_enrolled"],
    },
    {
        "profile": {"residency_years": "10", "monthly_income": "40000", "currently_working": "No"},
        "rejection_reasons": ["incomplete"],
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _application_month_slots(years):
    """
    Return (year, month) slots for May and June across the past N full years.
    Mirrors the real application season without touching the current year's real data.
    """
    now = timezone.now()
    result = []
    for y in range(years, 0, -1):
        year = now.year - y
        result.append((year, 5))  # May
        result.append((year, 6))  # June
    return result


def _random_datetime_in_month(year, month):
    import calendar
    _, days = calendar.monthrange(year, month)
    day = random.randint(1, days)
    naive = datetime(year, month, day, random.randint(8, 17), random.randint(0, 59))
    return timezone.make_aware(naive)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Generate bulk dummy applications across May–June of the past N years."

    def add_arguments(self, parser):
        parser.add_argument("--sinag-approved", type=int, default=740,
                            help="Total approved SINAG applications across all years (default: 740)")
        parser.add_argument("--sinag-rejected", type=int, default=90,
                            help="Total rejected SINAG applications across all years (default: 90)")
        parser.add_argument("--spark-approved", type=int, default=740,
                            help="Total approved SPARK applications across all years (default: 740)")
        parser.add_argument("--spark-rejected", type=int, default=90,
                            help="Total rejected SPARK applications across all years (default: 90)")
        parser.add_argument("--years", type=int, default=4,
                            help="How many past years to spread applications across (default: 4)")
        parser.add_argument("--clean", action="store_true",
                            help="Delete all existing dummy data before generating")

    def handle(self, *args, **options):
        if options["clean"]:
            deleted, _ = User.objects.filter(username__startswith="dummy_").delete()
            self.stdout.write(self.style.WARNING(f"Cleaned up {deleted} existing dummy records."))

        month_slots = _application_month_slots(options["years"])
        existing = User.objects.filter(username__startswith="dummy_").count()
        counter = existing

        created = 0

        total_target = (options["sinag_approved"] + options["sinag_rejected"]
                        + options["spark_approved"] + options["spark_rejected"])
        self.stdout.write(f"Generating {total_target} applications across {options['years']} years (May–June each year)...")

        for short_name, approved_count, rejected_count, approved_pool, rejected_pool in [
            ("SINAG", options["sinag_approved"], options["sinag_rejected"],
             SINAG_APPROVED_PROFILES, SINAG_REJECTED_SCENARIOS),
            ("SPARK", options["spark_approved"], options["spark_rejected"],
             SPARK_APPROVED_PROFILES, SPARK_REJECTED_SCENARIOS),
        ]:
            try:
                program = Program.objects.get(short_name__iexact=short_name)
            except Program.DoesNotExist:
                self.stderr.write(self.style.WARNING(
                    f"{short_name} program not found — skipping."
                ))
                continue

            for _ in range(approved_count):
                counter += 1
                profile_data = random.choice(approved_pool)
                app = self._create_application(program, profile_data, counter, month_slots)
                run_rule_evaluation(app)
                app.status = Application.ApplicationStatus.APPROVED
                app.save(update_fields=["status"])
                created += 1

            for _ in range(rejected_count):
                counter += 1
                scenario = random.choice(rejected_pool)
                app = self._create_application(program, scenario["profile"], counter, month_slots)
                run_rule_evaluation(app)
                app.status = Application.ApplicationStatus.REJECTED
                app.rejection_reason = scenario["rejection_reasons"]
                app.save(update_fields=["status", "rejection_reason"])
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} dummy applications."))

    def _create_application(self, program, profile_data, n, month_slots):
        gender = random.choice(["Male", "Female"])
        first = random.choice(MALE_FIRST_NAMES if gender == "Male" else FEMALE_FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        middle = random.choice(MIDDLE_NAMES)

        user = User.objects.create_user(
            username=f"dummy_{n:05d}",
            email=f"dummy_{n:05d}@example.com",
            password="DummyPass123!",
            first_name=first,
            last_name=last,
        )

        civil_status = random.choice(["Single", "Single", "Married", "Widowed"])

        ApplicantProfile.objects.create(
            user=user,
            first_name=first,
            last_name=last,
            middle_name=middle,
            address=f"{random.randint(1, 300)} {random.choice(STREET_NAMES)}",
            barangay=random.choice(BARANGAYS),
            residency_years=profile_data.get("residency_years", "10"),
            gender=gender,
            civil_status=civil_status,
            citizenship="Filipino",
            contact_number=f"09{random.randint(100000000, 999999999)}",
            currently_working=profile_data.get("currently_working", "No"),
            religion=random.choice(RELIGIONS),
            monthly_income=profile_data.get("monthly_income", "20000"),
        )

        backdate = _random_datetime_in_month(*random.choice(month_slots))

        app = Application.objects.create(
            applicant=user,
            program=program,
            status=Application.ApplicationStatus.SUBMITTED,
            submitted_at=backdate,
            educational_data={},
        )

        # Bypass auto_now_add to backdate created_at
        Application.objects.filter(pk=app.pk).update(created_at=backdate)
        app.refresh_from_db()

        # Signal already created ApplicationDocuments as MISSING on save — just update to SUBMITTED
        ApplicationDocument.objects.filter(
            application=app,
            requirement__required=True,
        ).update(status=ApplicationDocument.DocStatus.SUBMITTED)

        return app
