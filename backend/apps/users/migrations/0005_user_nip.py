from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_alter_user_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="nip",
            field=models.CharField(blank=True, max_length=30, verbose_name="NIP"),
        ),
    ]
