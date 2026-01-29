from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CUSTOMER = "customer", "Customer"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )


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
    """
    Hierarkisk kontostruktur för företag och avdelningar.
    Exempel:
    - JM Koncernen (parent=None)
      - JM AB (parent=JM Koncernen)
        - JM Stockholm (parent=JM AB)
    """
    name = models.CharField(max_length=200, verbose_name="Kontonamn")
    account_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Kontokod",
        help_text="T.ex. K00979"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Överliggande konto"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
    
    def __str__(self):
        return f"{self.name} ({self.account_code})"
    
    def get_descendants(self):
        """
        Hämtar alla underkonton rekursivt (barn, barnbarn, osv.)
        Returnerar: set av Account-objekt
        """
        descendants = set()
        for child in self.children.all():
            descendants.add(child)
            descendants.update(child.get_descendants())
        return descendants
    
    def get_ancestors(self):
        """
        Hämtar alla föräldrakonton uppåt i hierarkin.
        Returnerar: list av Account-objekt [parent, grandparent, ...]
        """
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors
    
    @property
    def level(self):
        """
        Räknar ut nivå i hierarkin.
        0 = root (ingen parent)
        1 = första nivån under root
        osv.
        """
        return len(self.get_ancestors())
    
    @property
    def full_path(self):
        """
        Returnerar full sökväg, t.ex. "JM Koncernen > JM AB > JM Stockholm"
        """
        ancestors = list(reversed(self.get_ancestors()))
        path = [a.name for a in ancestors] + [self.name]
        return " > ".join(path)


class UserAccountAccess(models.Model):
    """
    Kopplar en User till ett Account.
    En user kan bara tillhöra ETT account (enligt ditt krav B).
    Users får automatiskt access till sitt account + alla child-accounts.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='account_access'
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='user_accesses'
    )
    
    # Valfritt: Lägg till roller per account om du vill ha finare behörigheter senare
    ROLE_CHOICES = [
        ('viewer', 'Viewer'),
        ('editor', 'Editor'),
        ('manager', 'Manager'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='viewer',
        verbose_name="Roll"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Account Access'
        verbose_name_plural = 'User Account Accesses'
    
    def __str__(self):
        return f"{self.user.email} → {self.account.name} ({self.role})"
    
    def get_accessible_accounts(self):
        """
        Returnerar set av alla accounts som användaren har tillgång till:
        - Sitt eget account
        - Alla child-accounts nedåt
        """
        accounts = {self.account}
        accounts.update(self.account.get_descendants())
        return accounts


