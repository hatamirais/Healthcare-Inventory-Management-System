from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("items", "0005_alter_facility_facility_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="is_essential",
            field=models.BooleanField(
                default=False,
                help_text="Designated essential item [E]",
            ),
        ),
    ]