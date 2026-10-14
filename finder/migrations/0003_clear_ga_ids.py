from django.db import migrations


def clear_ga_ids(apps, schema_editor):
    Market = apps.get_model("finder", "Market")
    Market.objects.all().update(ga_ids=[])


class Migration(migrations.Migration):
    dependencies = [
        ("finder", "0002_seed_catalog"),
    ]

    operations = [
        migrations.RunPython(clear_ga_ids, migrations.RunPython.noop),
    ]
