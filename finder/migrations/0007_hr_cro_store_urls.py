"""Uvezi CRO Sport Vision .hr linkove u živi HR katalog."""

from django.db import migrations


def apply_hr_cro_catalog(apps, schema_editor):
    Market = apps.get_model("finder", "Market")
    if not Market.objects.filter(pk="hr").exists():
        return
    from finder.store_sync import sync_market_from_links

    sync_market_from_links(
        "hr",
        scrape=False,
        download_missing_images=False,
        replace_catalog=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("finder", "0006_editor_profile"),
    ]

    operations = [
        migrations.RunPython(apply_hr_cro_catalog, migrations.RunPython.noop),
    ]
