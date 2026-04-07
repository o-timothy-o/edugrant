"""Signals for programs app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Application, ApplicationDocument, DocumentRequirement


@receiver(post_save, sender=Application)
def create_application_documents(sender, instance, created, **kwargs):
    """Create ApplicationDocument records for each DocumentRequirement when an application is created."""
    if created:
        for req in instance.program.document_requirements.all():
            ApplicationDocument.objects.get_or_create(
                application=instance,
                requirement=req,
                defaults={"status": ApplicationDocument.DocStatus.MISSING},
            )
