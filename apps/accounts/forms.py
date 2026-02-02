from django import forms
from django.contrib.auth import get_user_model

from apps.accounts.models import OrgUnit, UserOrgUnitAccess, CompanyMember, Company

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


class OrgUnitForm(forms.ModelForm):
    """Form för att skapa/redigera OrgUnit."""

    class Meta:
        model = OrgUnit
        fields = ["name", "unit_code", "parent"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "T.ex. District 12"}),
            "unit_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "T.ex. D12"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "name": "Enhetsnamn",
            "unit_code": "Enhetskod",
            "parent": "Överliggande enhet (valfritt)",
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields["parent"].queryset = (
                OrgUnit.objects.filter(company=company).order_by("name")
            )


class UserOrgUnitAccessForm(forms.ModelForm):
    """Form för att koppla en User till en OrgUnit."""

    class Meta:
        model = UserOrgUnitAccess
        fields = ["user", "org_unit"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "org_unit": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "user": "Användare",
            "org_unit": "Enhet",
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)  # valfritt: filtrera på företag
        super().__init__(*args, **kwargs)

        # Visa bara "vanliga" users (inte staff/superuser)
        self.fields["user"].queryset = (
            User.objects
            .filter(is_superuser=False, is_staff=False)
            .order_by("email")
        )

        # Om vi vet vilket företag vi är i: visa bara users i det företaget
        if company is not None:
            self.fields["user"].queryset = (
                User.objects
                .filter(company_memberships__company=company)
                .order_by("email")
                .distinct()
            )

            # Och visa bara org units i det företaget
            self.fields["org_unit"].queryset = (
                OrgUnit.objects
                .filter(company=company)
                .order_by("name")
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
                "placeholder": "Ex: Panem",
                "autocomplete": "organization",
            }),
            "org_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: 12345",
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

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()
