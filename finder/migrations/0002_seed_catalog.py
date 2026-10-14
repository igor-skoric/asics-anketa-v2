from django.db import migrations

from finder.seed import seed_catalog


class Migration(migrations.Migration):
    dependencies = [
        ("finder", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
    ]
