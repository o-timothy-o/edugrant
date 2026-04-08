from django import forms
from django.forms import inlineformset_factory
from .models import Application, ApplicationDocument, DocumentRequirement, Program

class SparkApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = []

class SinagApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = []

class ApplicationDocumentForm(forms.ModelForm):
    class Meta:
        model = ApplicationDocument
        fields = ['file']

class FamilyCompositionForm(forms.Form):
    name = forms.CharField(max_length=100)
    date_of_birth = forms.CharField(max_length=100)
    age = forms.CharField(max_length=100)
    sex = forms.CharField(max_length=100)
    relation_to_child = forms.CharField(max_length=100)
    occupation = forms.CharField(max_length=100)
    income = forms.CharField(max_length=100)
    highest_educ_attainment = forms.CharField(max_length=100)

class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['name', 'short_name', 'program_type', 'status', 'application_frequency', 'description']

DocumentRequirementFormSet = inlineformset_factory(
    Program,
    DocumentRequirement,
    fields=['name', 'required', 'display_order'],
    extra=3,
    can_delete=True,
)
