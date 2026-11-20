from django.db import migrations, models


def fill_analytics_codes(apps, schema_editor):
    from finder.paths import SHOE_EVENT_CODES

    Shoe = apps.get_model("finder", "Shoe")
    taken = {}
    for shoe in Shoe.objects.order_by("market_id", "key"):
        used = taken.setdefault(shoe.market_id, set())
        known = SHOE_EVENT_CODES.get(shoe.key)
        if known and known not in used:
            code = known
        else:
            raw = (shoe.key or "patika").replace("-", "")
            base = raw[:6] or "patika"
            code = base
            number = 2
            while code in used:
                suffix = str(number)
                code = f"{base[: 6 - len(suffix)]}{suffix}"
                number += 1
        used.add(code)
        shoe.analytics_code = code
        shoe.save(update_fields=["analytics_code"])


class Migration(migrations.Migration):
    dependencies = [
        ("finder", "0003_clear_ga_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoe",
            name="analytics_code",
            field=models.SlugField(
                blank=True,
                default="",
                help_text="Kratka oznaka u imenu Google Analytics događaja. Popuni se sama i ista je za isti model na sva tri tržišta.",
                max_length=6,
                verbose_name="Kod u statistici",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(fill_analytics_codes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="shoe",
            constraint=models.UniqueConstraint(
                fields=("market", "analytics_code"),
                name="unique_shoe_analytics_code_per_market",
            ),
        ),
    ]
