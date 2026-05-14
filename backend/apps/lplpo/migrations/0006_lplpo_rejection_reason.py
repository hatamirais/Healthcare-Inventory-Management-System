from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lplpo", "0005_alter_lplpo_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="lplpo",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
    ]
