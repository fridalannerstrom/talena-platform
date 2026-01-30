from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError



User = settings.AUTH_USER_MODEL

def clean(self):
    if not CompanyMember.objects.filter(user=self.user, company=self.account.company).exists():
        raise ValidationError("User måste vara medlem i företaget innan account-access kan ges.")


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CUSTOMER = "customer", "Customer"

class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Företagsnamn")
    org_number = models.CharField(max_length=30, blank=True, null=True, verbose_name="Organisationsnummer")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


class CompanyMember(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"
    ROLE_VIEWER = "viewer"

    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_MEMBER, "Member"),
        (ROLE_VIEWER, "Viewer"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Företag",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="company_memberships",
        verbose_name="Användare",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER, verbose_name="Roll")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "user")
        verbose_name = "Company member"
        verbose_name_plural = "Company members"

    def __str__(self):
        return f"{self.company} ↔ {self.user} ({self.role})"

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    image = models.ImageField(upload_to="profile_images/", blank=True, null=True)

    def __str__(self):
        return f"Profile: {self.user.email}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile_exists(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)



# ============================================================================
# ACCOUNT HIERARCHY (NY FUNKTIONALITET)
# ============================================================================

class Account(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="accounts",
        verbose_name="Företag",
    )

    name = models.CharField(max_length=200, verbose_name="Kontonamn")

    account_code = models.CharField(
        max_length=50,
        verbose_name="Kontokod",
        help_text="T.ex. K00979"
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Överliggande konto",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "account_code"],
                name="uniq_account_code_per_company",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.account_code})"

    def clean(self):
        # hindra att man kopplar parent från annat företag
        if self.parent and self.company_id and self.parent.company_id != self.company_id:
            raise ValidationError({"parent": "Överliggande konto måste tillhöra samma företag."})

    # --- dina befintliga metoder ---
    def get_descendants(self):
        descendants = set()
        for child in self.children.all():
            descendants.add(child)
            descendants.update(child.get_descendants())
        return descendants

    def get_ancestors(self):
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    @property
    def level(self):
        return len(self.get_ancestors())

    @property
    def full_path(self):
        ancestors = list(reversed(self.get_ancestors()))
        path = [a.name for a in ancestors] + [self.name]
        return " > ".join(path)
    

class UserAccountAccess(models.Model):
    """
    Kopplar en user till ett account (många-till-många via denna tabell).
    En user kan ha access till flera accounts.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_accesses",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="user_accesses",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "account"], name="uniq_user_account"),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.account.name}"
