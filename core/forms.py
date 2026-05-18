from django import forms
from .models import MonitoringReport, Project, ProjectProposal, Sector
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User
from django.db.models import Q 

# فورم التسجيل
# forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import User, MonitoringReport


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
        })
    )
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Choose a username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'your@email.com',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Last name',
            }),
        }
        # هنا نغيّر رسالة التكرار
        error_messages = {
            'username': {
                'unique': 'اسم المستخدم هذا مستخدَم بالفعل، الرجاء اختيار اسم آخر.',
                'required': 'اسم المستخدم مطلوب.',
            },
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise ValidationError("كلمتا المرور غير متطابقتين.")

        return cleaned_data
    def clean_username(self):
         username = self.cleaned_data.get('username')
         if username and User.objects.filter(username__iexact=username).exists():
            raise ValidationError('اسم المستخدم هذا مستخدَم بالفعل، الرجاء اختيار اسم آخر.')
         return username
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_approved = False  # ينتظر موافقة الأدمن
        user.email_verified = False  
        user.role = 'OFFICER'
        if commit:
            user.save()
        return user


# فورم الدخول (مع ستايل)
class StyledLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-input',
        'placeholder': 'Username',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-input',
        'placeholder': 'Password',
    }))

class MonitoringReportForm(forms.ModelForm):
    class Meta:
        model = MonitoringReport
        exclude = ['officer', 'beneficiaries_reached']
        widgets = {
            'project': forms.Select(attrs={
                'class': 'form-input',
            }),
            'visit_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input',
            }),
            'progress_percentage': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
                'max': 100,
                'placeholder': '0 - 100',
            }),
            'male': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
            }),
            'female': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
            }),
            'children': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
            }),
            'risk_level': forms.Select(attrs={
                'class': 'form-input',
            }),
            'issues': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Describe any issues encountered...',
            }),
            'recommendation': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Your recommendations...',
            }),
            'report_file': forms.ClearableFileInput(attrs={
                'class': 'form-file',
            }),
        }
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name',
            'sector',
            'donor',
            'budget',
            'start_date',
            'end_date',
            'location',
            'target_beneficiaries',
            'status',
            'assigned_officer',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Project name'}),
            'sector': forms.Select(attrs={'class': 'form-input'}),
            'donor': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Donor name'}),
            'budget': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Location'}),
            'target_beneficiaries': forms.NumberInput(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'assigned_officer': forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Sector.objects.filter(is_active=True).order_by('name')

        # لو بنعدل مشروع قطاعه صار inactive، نخليه ظاهر حتى لا يختفي من الفورم
        if self.instance and self.instance.pk and self.instance.sector_id:
            qs = Sector.objects.filter(
                Q(is_active=True) | Q(id=self.instance.sector_id)
            ).distinct().order_by('name')

        self.fields['sector'].queryset = qs
class ProjectProposalForm(forms.ModelForm):
    class Meta:
        model = ProjectProposal
        fields = [
            'title',
            'sector',
            'donor',
            'proposed_budget',
            'proposed_start_date',
            'proposed_end_date',
            'location',
            'target_beneficiaries',
            'summary',
            'proposal_file',
            'status',
            'project',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Proposal title',
            }),
            'sector': forms.Select(attrs={
                'class': 'form-input',
            }),
            'donor': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Donor name',
            }),
            'proposed_budget': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
            }),
            'proposed_start_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'proposed_end_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Location',
            }),
            'target_beneficiaries': forms.NumberInput(attrs={
                'class': 'form-input',
            }),
            'summary': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Summary / objectives / main activities...',
            }),
            'status': forms.Select(attrs={
                'class': 'form-input',
            }),
            'project': forms.Select(attrs={
                'class': 'form-input',
            }),
            'proposal_file': forms.ClearableFileInput(attrs={
                'class': 'form-file',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Sector.objects.filter(is_active=True).order_by('name')

        if self.instance and self.instance.pk and self.instance.sector_id:
            qs = Sector.objects.filter(
                Q(is_active=True) | Q(id=self.instance.sector_id)
            ).distinct().order_by('name')

        self.fields['sector'].queryset = qs