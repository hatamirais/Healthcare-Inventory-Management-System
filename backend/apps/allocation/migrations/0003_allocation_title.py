from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("allocation", "0002_remove_allocation_sumber_dana"),
    ]

    operations = [
        migrations.AddField(
            model_name="allocation",
            name="title",
            field=models.CharField(
                blank=True,
                help_text="Judul dokumen alokasi untuk header atau kebutuhan cetak.",
                max_length=255,
            ),
        ),
    ]