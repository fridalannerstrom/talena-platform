from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_account_useraccountaccess"),  
        ("accounts", "0006_create_company_models"), # byt till din senaste migration före detta
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="accounts",
                to="accounts.company",
                verbose_name="Företag",
            ),
        ),
    ]
