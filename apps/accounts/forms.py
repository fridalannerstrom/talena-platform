from django import forms
from django.contrib.auth import get_user_model
from apps.accounts.models import Account, UserAccountAccess, CompanyMember

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
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
                'placeholder': 'T.ex. JM Stockholm'
            }),
            'account_code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
                'placeholder': 'T.ex. K00846'
            }),
            'parent': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
            })
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
            'user': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
            }),
            'account': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
            })
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