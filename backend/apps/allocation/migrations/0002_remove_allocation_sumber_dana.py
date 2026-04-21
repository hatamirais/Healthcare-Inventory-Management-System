from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("allocation", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="allocation",
            name="sumber_dana",
        ),
    ]