from django.apps import AppConfig


class ProgramsConfig(AppConfig):
    name = "programs"

    def ready(self):
        import programs.signals  # noqa: F401
