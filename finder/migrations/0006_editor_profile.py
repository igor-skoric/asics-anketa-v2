from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_profiles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Market = apps.get_model("finder", "Market")
    EditorProfile = apps.get_model("finder", "EditorProfile")
    group = Group.objects.filter(name="urednici").first()
    markets = list(Market.objects.all())
    if group is None or not markets:
        return
    for user in User.objects.filter(groups=group, is_superuser=False):
        profile, _created = EditorProfile.objects.get_or_create(user=user)
        if not profile.markets.exists():
            profile.markets.set(markets)
        if getattr(user, "is_staff", False):
            user.is_staff = False
            user.save(update_fields=["is_staff"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("finder", "0005_market_and_shoe_help_text"),
    ]

    operations = [
        migrations.CreateModel(
            name="EditorProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "markets",
                    models.ManyToManyField(
                        blank=True,
                        related_name="editors",
                        to="finder.market",
                        verbose_name="Tržišta",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="editor_profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Nalog",
                    ),
                ),
            ],
            options={
                "verbose_name": "Profil urednika",
                "verbose_name_plural": "Profili urednika",
            },
        ),
        migrations.RunPython(seed_profiles, migrations.RunPython.noop),
    ]
