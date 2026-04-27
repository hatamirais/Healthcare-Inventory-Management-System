from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_systemsettings_platform_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemsettings",
            name="lplpo_distribution_number_template",
            field=models.CharField(
                default="440/{seq}/SBBK.RF/{year}",
                help_text="Template nomor dokumen distribusi LPLPO. Gunakan placeholder {seq} dan {year}.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="special_request_distribution_number_template",
            field=models.CharField(
                default="440/{seq}/KD.F/{year}",
                help_text="Template nomor dokumen Permintaan Khusus. Gunakan placeholder {seq} dan {year}.",
                max_length=255,
            ),
        ),
    ]