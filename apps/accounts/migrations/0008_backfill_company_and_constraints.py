from django.db import migrations, models


def forwards_func(apps, schema_editor):
    Company = apps.get_model("accounts", "Company")
    Account = apps.get_model("accounts", "Account")

    # 1) Skapa default company (om den inte finns)
    default_company, _ = Company.objects.get_or_create(
        name="Default company",
        defaults={"org_number": None},
    )

    # 2) Backfilla alla Accounts som saknar company
    Account.objects.filter(company__isnull=True).update(company=default_company)


def reverse_func(apps, schema_editor):
    # Vi gör ingen reverse på detta (lämna data som den är)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_add_company_to_account_nullable"),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),

        # Gör company REQUIRED
        migrations.AlterField(
            model_name="account",
            name="company",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="accounts",
                to="accounts.company",
                verbose_name="Företag",
            ),
        ),

        # Ta bort global unique på account_code (om du har unique=True idag)
        migrations.AlterField(
            model_name="account",
            name="account_code",
            field=models.CharField(
                max_length=50,
                help_text="T.ex. K00979",
                verbose_name="Kontokod",
            ),
        ),

        # Lägg till unique per company
        migrations.AddConstraint(
            model_name="account",
            constraint=models.UniqueConstraint(
                fields=("company", "account_code"),
                name="uniq_account_code_per_company",
            ),
        ),
    ]
