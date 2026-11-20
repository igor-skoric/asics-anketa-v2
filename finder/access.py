from django.contrib.auth.models import Group

from .models import Market

EDITOR_GROUP = "urednici"


def is_editor(user):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=EDITOR_GROUP).exists()


def editor_group():
    group, _created = Group.objects.get_or_create(name=EDITOR_GROUP)
    return group


def allowed_markets(user):
    """Tržišta koja urednik sme da vidi. Vlasnik vidi sva."""
    if not is_editor(user):
        return Market.objects.none()
    if user.is_superuser:
        return Market.objects.all()
    profile = getattr(user, "editor_profile", None)
    if profile is None:
        return Market.objects.none()
    return profile.markets.all().order_by("code")


def can_access_market(user, market_code):
    if user.is_superuser:
        return Market.objects.filter(pk=market_code).exists()
    return allowed_markets(user).filter(pk=market_code).exists()
