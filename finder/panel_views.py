from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .access import allowed_markets, can_access_market, editor_group, is_editor
from .catalog import paths_missing_active_shoes, public_src
from .models import AnswerPath, EditorProfile, Market, Recommendation, RecommendationItem, Shoe
from .panel_excel import (
    apply_preview,
    build_preview,
    dump_preview_token,
    export_workbook,
    load_preview_token,
    market_revision,
)
from .panel_forms import (
    EditorCreateForm,
    EditorMarketsForm,
    PlacementForm,
    ShoePanelForm,
    VariantFormSet,
)

LOGIN_URL = "/panel/prijava/"
IMPORT_SESSION_KEY = "panel_excel_preview"
PAGE_SIZE = 12
SORT_CHOICES = {
    "name": ("family_name", "Naziv A–Z"),
    "-name": ("-family_name", "Naziv Z–A"),
    "model": ("model_name", "Model A–Z"),
    "variants": ("-variant_count", "Više varijanti"),
    "status": ("-available", "Prvo aktivne"),
}


def editors_only(view):
    @login_required(login_url=LOGIN_URL)
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not is_editor(request.user):
            return render(request, "panel/denied.html", {"message": "Ovaj nalog nema pristup panelu."}, status=403)
        return view(request, *args, **kwargs)

    return wrapped


def owners_only(view):
    @editors_only
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(
                request,
                "panel/denied.html",
                {"message": "Naloge zaposlenih otvara samo vlasnik."},
                status=403,
            )
        return view(request, *args, **kwargs)

    return wrapped


def market_access(view):
    @editors_only
    @wraps(view)
    def wrapped(request, market, *args, **kwargs):
        if not can_access_market(request.user, market):
            return render(
                request,
                "panel/denied.html",
                {"message": "Nemaš pristup ovom tržištu."},
                status=403,
            )
        return view(request, market, *args, **kwargs)

    return wrapped


def _safe_next(request):
    target = request.POST.get("next") or request.GET.get("next") or "/panel/"
    if not target.startswith("/panel/"):
        return "/panel/"
    return target


def _markets_for(request):
    return allowed_markets(request.user)


def login_view(request):
    if is_editor(request.user):
        return redirect("panel_home")
    error = ""
    username = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            error = "Korisničko ime ili lozinka nisu tačni."
        elif not is_editor(user):
            error = "Ovaj nalog nema pristup panelu."
        else:
            login(request, user)
            return redirect(_safe_next(request))
    return render(request, "panel/login.html", {"error": error, "username": username})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("panel_login")


@editors_only
def home(request):
    markets = list(_markets_for(request))
    if len(markets) == 1:
        return redirect("panel_shoes", market=markets[0].code)
    return render(
        request,
        "panel/home.html",
        {
            "markets": markets,
            "breadcrumbs": [("Panel", None)],
        },
    )


@market_access
def shoe_list(request, market):
    current = get_object_or_404(Market, pk=market)
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all").strip() or "all"
    if status not in {"all", "on", "off"}:
        status = "all"
    sort = request.GET.get("sort", "name").strip() or "name"
    if sort not in SORT_CHOICES:
        sort = "name"
    order_field = SORT_CHOICES[sort][0]

    shoes = current.shoes.annotate(variant_count=Count("variants")).prefetch_related("variants")
    if query:
        shoes = shoes.filter(
            Q(family_name__icontains=query)
            | Q(model_name__icontains=query)
            | Q(key__icontains=query)
            | Q(variants__sku__icontains=query)
        ).distinct()
    if status == "on":
        shoes = shoes.filter(available=True)
    elif status == "off":
        shoes = shoes.filter(available=False)
    shoes = shoes.order_by(order_field, "family_name", "pk")

    paginator = Paginator(shoes, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    rows = []
    for shoe in page_obj.object_list:
        variants = list(shoe.variants.all())
        variant = variants[0] if variants else None
        image = public_src(shoe.photo, shoe.filename)
        if not image and variant:
            image = public_src(variant.photo, variant.filename)
        rows.append(
            {
                "shoe": shoe,
                "image": image,
                "variants": len(variants),
                "skus": [item.sku for item in variants[:3]],
                "colors": sorted({item.color for item in variants if item.color}),
            }
        )
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return render(
        request,
        "panel/list.html",
        {
            "market": current,
            "markets": _markets_for(request),
            "rows": rows,
            "page_obj": page_obj,
            "query": query,
            "status": status,
            "sort": sort,
            "sort_choices": SORT_CHOICES,
            "query_string": query_params.urlencode(),
            "empty_paths": paths_missing_active_shoes(current),
            "breadcrumbs": [
                ("Panel", "/panel/"),
                (current.country, None),
            ],
        },
    )


@market_access
@require_GET
def catalog_export(request, market):
    current = get_object_or_404(Market, pk=market)
    payload = export_workbook(current)
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="katalog-{current.code}.xlsx"'
    return response


@market_access
def catalog_import(request, market):
    current = get_object_or_404(Market, pk=market)
    if request.method == "POST":
        upload = request.FILES.get("workbook")
        if not upload:
            messages.error(request, "Izaberi .xlsx fajl.")
            return redirect("panel_catalog_import", market=current.code)
        if not upload.name.lower().endswith(".xlsx"):
            messages.error(request, "Dozvoljen je samo .xlsx fajl.")
            return redirect("panel_catalog_import", market=current.code)
        preview = build_preview(current, upload.read())
        request.session[IMPORT_SESSION_KEY] = dump_preview_token(preview)
        return redirect("panel_catalog_import_preview", market=current.code)
    return render(
        request,
        "panel/import.html",
        {
            "market": current,
            "markets": _markets_for(request),
            "breadcrumbs": [
                ("Panel", "/panel/"),
                (current.country, f"/panel/{current.code}/"),
                ("Uvoz", None),
            ],
        },
    )


@market_access
def catalog_import_preview(request, market):
    current = get_object_or_404(Market, pk=market)
    raw = request.session.get(IMPORT_SESSION_KEY)
    if not raw:
        messages.error(request, "Nema pregleda. Prvo učitaj fajl.")
        return redirect("panel_catalog_import", market=current.code)
    preview = load_preview_token(raw)
    if preview.market_code != current.code:
        messages.error(request, "Pregled pripada drugom tržištu. Učitaj fajl ponovo.")
        request.session.pop(IMPORT_SESSION_KEY, None)
        return redirect("panel_catalog_import", market=current.code)

    if request.method == "POST" and request.POST.get("confirm") == "1":
        if not preview.ok:
            messages.error(request, "Ispravi greške pa učitaj fajl ponovo.")
            return redirect("panel_catalog_import", market=current.code)
        try:
            apply_preview(current, preview)
        except RuntimeError:
            messages.error(
                request,
                "Katalog je izmenjen od pregleda. Učitaj fajl ponovo i potvrdi novi pregled.",
            )
            request.session.pop(IMPORT_SESSION_KEY, None)
            return redirect("panel_catalog_import", market=current.code)
        request.session.pop(IMPORT_SESSION_KEY, None)
        if preview.change_count:
            messages.success(request, f"Uvoz završen: {preview.change_count} izmena.")
        else:
            messages.success(request, "Uvoz završen: nema izmena.")
        return redirect("panel_shoes", market=current.code)

    stale = market_revision(current) != preview.revision
    return render(
        request,
        "panel/import_preview.html",
        {
            "market": current,
            "markets": _markets_for(request),
            "preview": preview,
            "stale": stale,
            "breadcrumbs": [
                ("Panel", "/panel/"),
                (current.country, f"/panel/{current.code}/"),
                ("Uvoz", f"/panel/{current.code}/uvoz/"),
                ("Pregled", None),
            ],
        },
    )


def _selected_paths(shoe):
    if shoe is None or not shoe.pk:
        return {}
    selected = {}
    items = RecommendationItem.objects.filter(shoe=shoe).select_related("recommendation")
    for item in items:
        selected[item.recommendation.path_id] = item.placement
    return selected


def _save_placements(shoe, form):
    for name, field in form.fields.items():
        path = field.path
        placement = form.cleaned_data.get(name) or ""
        recommendation, _created = Recommendation.objects.get_or_create(market=shoe.market, path=path)
        item = RecommendationItem.objects.filter(recommendation=recommendation, shoe=shoe).first()
        if not placement:
            if item:
                item.delete()
            continue
        if item:
            if item.placement != placement:
                item.placement = placement
                item.save(update_fields=["placement"])
            continue
        last = recommendation.items.filter(placement=placement).order_by("-position").first()
        RecommendationItem.objects.create(
            recommendation=recommendation,
            shoe=shoe,
            placement=placement,
            position=(last.position + 1) if last else 1,
        )


@market_access
def shoe_edit(request, market, shoe_id=None):
    current = get_object_or_404(Market, pk=market)
    shoe = get_object_or_404(Shoe, pk=shoe_id, market=current) if shoe_id else Shoe(market=current)
    paths = list(AnswerPath.objects.all())
    if request.method == "POST":
        shoe_form = ShoePanelForm(request.POST, request.FILES, instance=shoe)
        variant_formset = VariantFormSet(request.POST, request.FILES, instance=shoe)
        place_form = PlacementForm(request.POST, paths=paths)
        valid = shoe_form.is_valid() and variant_formset.is_valid() and place_form.is_valid()
        if valid:
            try:
                with transaction.atomic():
                    saved = shoe_form.save(commit=False)
                    saved.market = current
                    saved.save()
                    variant_formset.instance = saved
                    variant_formset.save()
                    _save_placements(saved, place_form)
            except IntegrityError:
                shoe_form.add_error(None, "Šifra varijante već postoji na ovoj patiki.")
            else:
                messages.success(request, "Patika je sačuvana.")
                empty = paths_missing_active_shoes(current)
                if empty:
                    labels = ", ".join(item["label"] for item in empty[:4])
                    more = "" if len(empty) <= 4 else f" (+{len(empty) - 4})"
                    messages.warning(
                        request,
                        f"Putanje bez aktivne preporuke: {labels}{more}.",
                    )
                return redirect("panel_shoe", market=current.code, shoe_id=saved.pk)
    else:
        shoe_form = ShoePanelForm(instance=shoe)
        variant_formset = VariantFormSet(instance=shoe)
        place_form = PlacementForm(paths=paths, selected=_selected_paths(shoe))
    title = shoe.family_name if shoe.pk else "Nova patika"
    return render(
        request,
        "panel/shoe.html",
        {
            "market": current,
            "markets": _markets_for(request),
            "shoe": shoe,
            "shoe_form": shoe_form,
            "variant_formset": variant_formset,
            "place_form": place_form,
            "breadcrumbs": [
                ("Panel", "/panel/"),
                (current.country, f"/panel/{current.code}/"),
                (title, None),
            ],
        },
    )


@market_access
@require_POST
def shoe_delete(request, market, shoe_id):
    current = get_object_or_404(Market, pk=market)
    shoe = get_object_or_404(Shoe, pk=shoe_id, market=current)
    if request.POST.get("confirm") != "on":
        messages.error(request, "Potvrdi brisanje pa pokušaj ponovo.")
        return redirect("panel_shoe", market=current.code, shoe_id=shoe.pk)
    name = shoe.family_name
    shoe.delete()
    messages.success(request, f"{name} je uklonjena.")
    return redirect("panel_shoes", market=current.code)


@owners_only
def users_view(request):
    User = get_user_model()
    form = EditorCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
            first_name=form.cleaned_data["first_name"].strip(),
        )
        user.is_staff = False
        user.is_superuser = False
        user.save(update_fields=["is_staff", "is_superuser"])
        user.groups.add(editor_group())
        profile = EditorProfile.objects.create(user=user)
        profile.markets.set(form.cleaned_data["markets"])
        messages.success(
            request,
            f"Nalog {user.username} može da se prijavi na panel (samo dodeljena tržišta, bez /admin/).",
        )
        return redirect("panel_users")
    people = (
        User.objects.filter(Q(is_superuser=True) | Q(groups__name="urednici"))
        .distinct()
        .order_by("username")
        .prefetch_related("editor_profile__markets")
    )
    for person in people:
        if not person.is_superuser and person.groups.filter(name="urednici").exists():
            EditorProfile.objects.get_or_create(user=person)
    return render(
        request,
        "panel/users.html",
        {
            "form": form,
            "people": people,
            "breadcrumbs": [("Panel", "/panel/"), ("Nalozi", None)],
        },
    )


@owners_only
@require_POST
def user_active(request, user_id):
    User = get_user_model()
    person = get_object_or_404(User, pk=user_id)
    if person.is_superuser or person.pk == request.user.pk:
        messages.error(request, "Vlasnički nalog se ovde ne gasi.")
        return redirect("panel_users")
    if not person.groups.filter(name="urednici").exists():
        return redirect("panel_users")
    person.is_active = not person.is_active
    person.is_staff = False
    person.save(update_fields=["is_active", "is_staff"])
    state = "uključen" if person.is_active else "isključen"
    messages.success(request, f"Nalog {person.username} je {state}.")
    return redirect("panel_users")


@owners_only
def user_markets(request, user_id):
    User = get_user_model()
    person = get_object_or_404(User, pk=user_id)
    if person.is_superuser or not person.groups.filter(name="urednici").exists():
        messages.error(request, "Tržišta se podešavaju samo za urednike.")
        return redirect("panel_users")
    profile, _created = EditorProfile.objects.get_or_create(user=person)
    form = EditorMarketsForm(
        request.POST or None,
        initial={"markets": profile.markets.all()},
    )
    if request.method == "POST" and form.is_valid():
        profile.markets.set(form.cleaned_data["markets"])
        person.is_staff = False
        person.save(update_fields=["is_staff"])
        messages.success(request, f"Tržišta za {person.username} su sačuvana.")
        return redirect("panel_users")
    return render(
        request,
        "panel/user_markets.html",
        {
            "person": person,
            "form": form,
            "breadcrumbs": [
                ("Panel", "/panel/"),
                ("Nalozi", "/panel/nalozi/"),
                (person.username, None),
            ],
        },
    )
