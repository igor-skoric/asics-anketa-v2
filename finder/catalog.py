from django.templatetags.static import static

from .models import AnswerPath, Market, Recommendation


def public_src(photo, filename):
    if photo:
        return photo.url
    if filename:
        base = static("assets")
        if not base.endswith("/"):
            base += "/"
        return base + filename
    return ""


def public_catalog(code):
    """Živi katalog iz baze. Prazna preporuka ostaje prazna — bez JSON/JS fallbacka."""
    market = Market.objects.filter(pk=code).first()
    if market is None:
        return None
    shoes = market.shoes.filter(available=True).prefetch_related("variants").all()
    products = [_shoe_payload(shoe) for shoe in shoes]
    recommendations = {path.pk: {"shoes": [], "extras": []} for path in AnswerPath.objects.all()}
    rows = (
        Recommendation.objects.filter(market=market)
        .select_related("path")
        .prefetch_related("items__shoe")
    )
    for row in rows:
        recommendations[row.path_id] = {
            "shoes": [
                item.shoe.key
                for item in row.items.all()
                if item.placement == "main" and item.shoe.available
            ],
            "extras": [
                item.shoe.key
                for item in row.items.all()
                if item.placement == "extra" and item.shoe.available
            ],
        }
    return {
        "products": products,
        "recommendations": recommendations,
        "ga_ids": market.ga_ids,
        "offer_checked": market.offer_checked,
    }


def paths_missing_active_shoes(market):
    """Putanje bez bar jedne dostupne patike u glavnoj ili dodatnoj ponudi."""
    catalog = public_catalog(market.code if hasattr(market, "code") else market)
    if not catalog:
        return []
    missing = []
    labels = {path.pk: path.label for path in AnswerPath.objects.all()}
    for path_id, spec in catalog["recommendations"].items():
        if not spec["shoes"] and not spec["extras"]:
            missing.append({"code": path_id, "label": labels.get(path_id, path_id)})
    return missing


def _shoe_payload(shoe):
    variants = []
    for variant in shoe.variants.all():
        variants.append(
            {
                "id": variant.external_id or str(variant.pk),
                "sku": variant.sku,
                "gender": variant.gender,
                "color": variant.color,
                "filename": variant.filename,
                "image_src": public_src(variant.photo, variant.filename) or public_src(shoe.photo, shoe.filename),
                "store_url": variant.store_url,
                "available_size_count": variant.available_size_count,
            }
        )
    return {
        "key": shoe.key,
        "model_name": shoe.model_name,
        "family_name": shoe.family_name,
        "filename": shoe.filename,
        "image_src": public_src(shoe.photo, shoe.filename),
        "available": shoe.available,
        "analytics_code": shoe.analytics_code,
        "variants": variants,
    }
