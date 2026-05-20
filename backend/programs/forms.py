import os
from django import forms
from django.forms import inlineformset_factory
from .models import Application, ApplicationDocument, DocumentRequirement, Program

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
ALLOWED_CONTENT_TYPES = {'application/pdf', 'image/jpeg', 'image/png'}

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
        widgets = {
            'file': forms.FileInput(attrs={'accept': 'application/pdf,image/jpeg,image/png'}),
        }

    def __init__(self, *args, file_required=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].required = file_required

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file and hasattr(file, 'name'):
            ext = os.path.splitext(file.name)[1].lower()
            content_type = getattr(file, 'content_type', '')
            if ext not in ALLOWED_EXTENSIONS and content_type not in ALLOWED_CONTENT_TYPES:
                raise forms.ValidationError('Only PDF, JPG, and PNG files are allowed.')
        return file

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
