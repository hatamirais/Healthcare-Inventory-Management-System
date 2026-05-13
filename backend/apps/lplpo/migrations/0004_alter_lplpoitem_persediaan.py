from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lplpo", "0002_add_pembelian_puskesmas"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lplpoitem",
            name="persediaan",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="stock_awal + penerimaan + pembelian_puskesmas",
                max_digits=12,
            ),
        ),
    ]