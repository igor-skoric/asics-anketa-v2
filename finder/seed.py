import json

from .markets import DATA_DIR
from .paths import ANSWER_PATHS, DEFAULT_SHOES, FAMILY_NAMES, TRAIL_EXTRA


def seed_catalog(apps, schema_editor=None):
    Market = apps.get_model("finder", "Market")
    AnswerPath = apps.get_model("finder", "AnswerPath")
    Shoe = apps.get_model("finder", "Shoe")
    Variant = apps.get_model("finder", "Variant")
    Recommendation = apps.get_model("finder", "Recommendation")
    RecommendationItem = apps.get_model("finder", "RecommendationItem")

    products = json.loads((DATA_DIR / "rs" / "products.json").read_text(encoding="utf-8"))
    paths = {}
    for code, label, position in ANSWER_PATHS:
        path, _created = AnswerPath.objects.get_or_create(
            code=code,
            defaults={"label": label, "position": position},
        )
        paths[code] = path

    for market_code in ("rs", "hr", "si"):
        meta = json.loads((DATA_DIR / market_code / "market.json").read_text(encoding="utf-8"))
        market, _created = Market.objects.get_or_create(
            code=market_code,
            defaults={
                "country": meta["country"],
                "locale": meta["locale"],
                "offer_checked": meta["offer_checked"],
                "ga_ids": meta["ga_ids"],
                "store_domain": meta.get("store_domain", ""),
            },
        )
        shoes = {}
        for item in products:
            shoe, _created = Shoe.objects.get_or_create(
                market=market,
                key=item["key"],
                defaults={
                    "family_name": FAMILY_NAMES.get(item["key"], item["model_name"]),
                    "model_name": item["model_name"],
                    "filename": item.get("filename") or "",
                    "available": bool(item.get("available", True)),
                },
            )
            shoes[item["key"]] = shoe
            for index, variant in enumerate(item.get("variants") or [], start=1):
                Variant.objects.get_or_create(
                    shoe=shoe,
                    sku=variant["sku"],
                    defaults={
                        "external_id": str(variant.get("id") or ""),
                        "gender": variant["gender"],
                        "color": variant["color"],
                        "filename": variant.get("filename") or "",
                        "store_url": variant["store_url"],
                        "available_size_count": variant.get("available_size_count") or 0,
                        "position": index,
                    },
                )
        for path_code, shoe_keys in DEFAULT_SHOES.items():
            recommendation, _created = Recommendation.objects.get_or_create(
                market=market,
                path=paths[path_code],
            )
            for index, key in enumerate(shoe_keys, start=1):
                RecommendationItem.objects.get_or_create(
                    recommendation=recommendation,
                    shoe=shoes[key],
                    defaults={"placement": "main", "position": index},
                )
            if path_code.startswith("trail/") and TRAIL_EXTRA in shoes:
                RecommendationItem.objects.get_or_create(
                    recommendation=recommendation,
                    shoe=shoes[TRAIL_EXTRA],
                    defaults={"placement": "extra", "position": 1},
                )
