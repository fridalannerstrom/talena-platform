from django import forms
from django.contrib.auth import get_user_model
from apps.accounts.models import Account, UserAccountAccess, CompanyMember, Company

User = get_user_model()

class InviteUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("En användare med den e-posten finns redan.")
        return email


class AccountForm(forms.ModelForm):
    """Form för att skapa/redigera Account"""
    
    class Meta:
        model = Account
        fields = ['name', 'account_code', 'parent']
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "T.ex. JM Stockholm"}),
            "account_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "T.ex. K00846"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            'name': 'Kontonamn',
            'account_code': 'Kontokod',
            'parent': 'Överliggande konto (valfritt)'
        }


class UserAccountAccessForm(forms.ModelForm):
    """Form för att koppla en User till ett Account"""
    
    class Meta:
        model = UserAccountAccess
        fields = ['user', 'account', 'role']
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "account": forms.Select(attrs={"class": "form-select"}),
            "role": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            'user': 'Användare',
            'account': 'Account',
            'role': 'Roll'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Visa bara customers (inte admins) i user-dropdown
        self.fields['user'].queryset = User.objects.filter(
            role=User.Role.CUSTOMER
        ).exclude(
            account_access__isnull=False  # Visa bara users som inte redan har ett account
        )



class CompanyMemberAddForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_superuser=False, is_staff=False).order_by("email"),
        required=True,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "10"}),
        label="Välj användare",
    )
    role = forms.ChoiceField(
        choices=CompanyMember.ROLE_CHOICES,
        initial=CompanyMember.ROLE_MEMBER,
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Roll",
    )


class CompanyMemberRoleForm(forms.Form):
    role = forms.ChoiceField(
        choices=CompanyMember.ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        label="",
    )


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "org_number"]
        labels = {
            "name": "Företagsnamn",
            "org_number": "Org.nr",
        }
        help_texts = {
            "org_number": "Valfritt. Ex: 556677-8899",
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: JM AB",
                "autocomplete": "organization",
            }),
            "org_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: 556677-8899",
                "autocomplete": "off",
            }),
        }

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Företagsnamn är obligatoriskt.")
        return name

    def clean_org_number(self):
        org = (self.cleaned_data.get("org_number") or "").strip()
        # Låt tomt vara ok
        return org or None


class CompanyInviteMemberForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@company.com"})
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Förnamn"})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Efternamn"})
    )
    role = forms.ChoiceField(
        choices=CompanyMember.ROLE_CHOICES,
        initial=CompanyMember.ROLE_MEMBER,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()