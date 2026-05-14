from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lplpo", "0004_alter_lplpoitem_persediaan"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lplpo",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft"),
                    ("SUBMITTED", "Diajukan"),
                    ("REJECTED", "Ditolak"),
                    ("REVIEWED", "Ditinjau"),
                    ("DISTRIBUTED", "Didistribusikan"),
                    ("CLOSED", "Ditutup"),
                ],
                default="DRAFT",
                max_length=20,
            ),
        ),
    ]