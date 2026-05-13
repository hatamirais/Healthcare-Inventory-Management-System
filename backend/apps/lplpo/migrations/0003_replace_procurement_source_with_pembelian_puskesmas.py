from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lplpo", "0002_lplpoitem_procurement_source"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="lplpoitem",
            name="procurement_source",
        ),
        migrations.AddField(
            model_name="lplpoitem",
            name="pembelian_puskesmas",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Jumlah pembelian mandiri Puskesmas pada periode ini",
                max_digits=12,
            ),
        ),
    ]