import json
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .markets import DATA_DIR
from .models import AnswerPath, Market, Recommendation, RecommendationItem, Shoe, Variant
from .paths import FAMILY_NAMES

ASSETS_DIR = Path(settings.BASE_DIR) / "assets"

UA = {"User-Agent": "Mozilla/5.0 (compatible; ASICSShoeFinder/1.0)"}

COLOR_MAP = {
    "crna": "Crna",
    "črna": "Crna",
    "crno": "Crna",
    "black": "Crna",
    "plava": "Plava",
    "modra": "Plava",
    "blue": "Plava",
    "zelena": "Zelena",
    "green": "Zelena",
    "bela": "Bela",
    "bijela": "Bela",
    "white": "Bela",
    "bež": "Bež",
    "bez": "Bež",
    "beige": "Bež",
    "roze": "Roze",
    "rožnata": "Roze",
    "roznata": "Roze",
    "ružičasta": "Roze",
    "ruzicasta": "Roze",
    "pink": "Roze",
    "ljubičasta": "Ljubičasta",
    "ljubicasta": "Ljubičasta",
    "vijolična": "Ljubičasta",
    "vijolicna": "Ljubičasta",
    "vijoličasta": "Ljubičasta",
    "vijolicasta": "Ljubičasta",
    "purple": "Ljubičasta",
    "siva": "Multicolor",
    "grey": "Multicolor",
    "gray": "Multicolor",
    "oranžna": "Multicolor",
    "oranzna": "Multicolor",
    "rumena": "Multicolor",
    "rdeča": "Multicolor",
    "rdeca": "Multicolor",
    "turkizna": "Plava",
    "roza": "Roze",
    "multicolor": "Multicolor",
    "večbarvna": "Multicolor",
    "vecbarvna": "Multicolor",
    "višebojna": "Multicolor",
    "visebojna": "Multicolor",
}

GENDER_MAP = {
    "moško": "men",
    "mosko": "men",
    "moški": "men",
    "moski": "men",
    "muški": "men",
    "muski": "men",
    "muško": "men",
    "musko": "men",
    "muškarci": "men",
    "muskarci": "men",
    "žensko": "women",
    "zensko": "women",
    "ženski": "women",
    "zenski": "women",
    "žene": "women",
    "zene": "women",
    "unisex": "unisex",
}


def load_links(market_code):
    path = DATA_DIR / market_code / "links.json"
    return json.loads(path.read_text(encoding="utf-8"))


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.read().decode("utf-8", "replace")


def _plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def normalize_color(raw):
    key = (raw or "").strip().lower()
    if not key:
        return "Multicolor"
    if key in COLOR_MAP:
        return COLOR_MAP[key]
    for token, mapped in COLOR_MAP.items():
        if token in key:
            return mapped
    return "Multicolor"


def normalize_gender(raw, fallback):
    key = (raw or "").strip().lower()
    return GENDER_MAP.get(key, fallback)


def scrape_product(url):
    html = fetch(url)
    pid = re.search(r"/(\d+)-", url)
    product_id = pid.group(1) if pid else ""
    m = re.search(r'data-productid="(\d+)"', html, re.I)
    if m:
        product_id = m.group(1)

    color_m = re.search(
        r'<tr class="attr-(?:barva|boja)">\s*<td>(?:Barva|Boja)</td>\s*<td[^>]*>(.*?)</td>',
        html,
        re.I | re.S,
    )
    color = normalize_color(_plain(color_m.group(1)) if color_m else "")

    gender_m = re.search(
        r'<tr class="attr-spol">\s*<td>Spol</td>\s*<td[^>]*>(.*?)</td>',
        html,
        re.I | re.S,
    )
    scraped_gender = _plain(gender_m.group(1)) if gender_m else ""

    img_m = re.search(r'property="og:image" content="([^"]+)"', html, re.I)
    image_url = img_m.group(1) if img_m else ""
    sku_m = re.search(r"/media/\d+/([A-Za-z0-9]+-\d+)/", image_url)
    if not sku_m:
        sku_m = re.search(r"\b([A-Z0-9]{4,}[A-Z0-9]*-\d{2,4})\b", html)
    sku = sku_m.group(1).upper() if sku_m else f"SI-{product_id}"

    title_m = re.search(r"<title>([^<]+)</title>", html, re.I)
    title = _plain(title_m.group(1).split("|")[0]) if title_m else ""

    sizes = re.findall(r'data-productsize-name="([^"]+)"', html, re.I)
    return {
        "id": product_id,
        "sku": sku,
        "color": color,
        "scraped_gender": scraped_gender,
        "image_url": image_url,
        "title": title,
        "available_size_count": len(set(sizes)),
        "store_url": url,
    }


def build_products_payload(links, scrape_cache=None, sleep_s=0.25):
    scrape_cache = scrape_cache if scrape_cache is not None else {}
    checked = links.get("updated") or date.today().isoformat()
    products = []
    for shoe in links["shoes"]:
        by_id = {}
        for section, urls in (shoe.get("products") or {}).items():
            for url in urls:
                if url not in scrape_cache:
                    scrape_cache[url] = scrape_product(url)
                    time.sleep(sleep_s)
                info = dict(scrape_cache[url])
                pid = info["id"] or url
                entry = by_id.setdefault(
                    pid,
                    {
                        "id": str(info["id"] or pid),
                        "sku": info["sku"],
                        "color": info["color"],
                        "filename": f"variants/{info['sku']}.webp",
                        "image_url": info["image_url"],
                        "store_url": info["store_url"],
                        "available_size_count": info["available_size_count"],
                        "sections": set(),
                        "scraped_gender": info.get("scraped_gender") or "",
                    },
                )
                entry["sections"].add(section)

        variants = []
        for index, entry in enumerate(by_id.values(), start=1):
            sections = entry.pop("sections")
            scraped = entry.pop("scraped_gender")
            if "unisex" in sections or sections == {"men", "women"}:
                gender = "unisex"
            elif len(sections) == 1:
                gender = next(iter(sections))
            else:
                gender = normalize_gender(scraped, "unisex")
            local = ASSETS_DIR / entry["filename"]
            if not local.is_file():
                entry["filename"] = ""
            variants.append(
                {
                    "id": entry["id"],
                    "sku": entry["sku"],
                    "gender": gender,
                    "color": entry["color"],
                    "filename": entry["filename"],
                    "image_url": entry["image_url"],
                    "store_url": entry["store_url"],
                    "available_size_count": entry["available_size_count"],
                    "_position": index,
                }
            )

        search_url = shoe.get("search_url") or ""
        first = variants[0] if variants else None
        products.append(
            {
                "key": shoe["key"],
                "model_name": shoe["model_name"],
                "sku": first["sku"] if first else shoe["key"],
                "filename": shoe.get("filename") or f"{shoe['key']}.webp",
                "source_url": search_url,
                "image_url": first["image_url"] if first else "",
                "bytes": 0,
                "store_url": search_url,
                "store_sku": first["sku"] if first else "",
                "available": True,
                "checked_at": checked,
                "available_size_count": sum(v["available_size_count"] for v in variants),
                "store_product_url": first["store_url"] if first else search_url,
                "variants": [
                    {k: v for k, v in item.items() if not k.startswith("_")}
                    for item in variants
                ],
            }
        )
    return products, scrape_cache


def write_products_json(market_code, products):
    path = DATA_DIR / market_code / "products.json"
    path.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def download_image(url, dest: Path):
    if not url:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as resp:
        dest.write_bytes(resp.read())
    return True


def _refresh_products_files(market_code, links, scrape=True, download_missing_images=True):
    """Osveži products.json i lokalne slike. Ne dira bazu."""
    if scrape:
        products, _cache = build_products_payload(links)
    else:
        products = json.loads((DATA_DIR / market_code / "products.json").read_text(encoding="utf-8"))

    if download_missing_images:
        for shoe in products:
            shoe_file = ASSETS_DIR / (shoe.get("filename") or f"{shoe['key']}.webp")
            if shoe.get("image_url") and not shoe_file.is_file():
                try:
                    download_image(shoe["image_url"], shoe_file)
                except Exception:
                    pass
            for variant in shoe.get("variants") or []:
                if not variant.get("filename") and variant.get("sku"):
                    candidate = f"variants/{variant['sku']}.webp"
                    if (ASSETS_DIR / candidate).is_file():
                        variant["filename"] = candidate
                if variant.get("image_url") and variant.get("sku"):
                    dest = ASSETS_DIR / "variants" / f"{variant['sku']}.webp"
                    if not dest.is_file():
                        try:
                            download_image(variant["image_url"], dest)
                            variant["filename"] = f"variants/{variant['sku']}.webp"
                        except Exception:
                            variant["filename"] = variant.get("filename") or ""
                    else:
                        variant["filename"] = f"variants/{variant['sku']}.webp"

    write_products_json(market_code, products)

    offer_checked = date.today().strftime("%d.%m.%Y")
    meta_path = DATA_DIR / market_code / "market.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["offer_checked"] = offer_checked
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return products, offer_checked


@transaction.atomic
def replace_market_catalog(market_code, products, links, offer_checked):
    """Zameni živi katalog u bazi podacima iz links/products. Briše postojeće preporuke putanja."""
    market = Market.objects.get(pk=market_code)
    market.offer_checked = offer_checked
    market.save(update_fields=["offer_checked"])

    active_keys = {item["key"] for item in products}
    shoes = {}
    for item in products:
        family = None
        for src in links["shoes"]:
            if src["key"] == item["key"]:
                family = src.get("family_name")
                break
        shoe, _created = Shoe.objects.update_or_create(
            market=market,
            key=item["key"],
            defaults={
                "family_name": family or FAMILY_NAMES.get(item["key"], item["model_name"]),
                "model_name": item["model_name"],
                "filename": item.get("filename") or "",
                "available": True,
            },
        )
        shoes[item["key"]] = shoe
        keep_skus = set()
        for index, variant in enumerate(item.get("variants") or [], start=1):
            keep_skus.add(variant["sku"])
            Variant.objects.update_or_create(
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
        shoe.variants.exclude(sku__in=keep_skus).delete()

    for key, _reason in (links.get("unavailable") or {}).items():
        shoe, created = Shoe.objects.get_or_create(
            market=market,
            key=key,
            defaults={
                "family_name": FAMILY_NAMES.get(key, key),
                "model_name": FAMILY_NAMES.get(key, key).replace("™", ""),
                "filename": f"{key}.webp",
                "available": False,
            },
        )
        if not created:
            shoe.available = False
            shoe.save(update_fields=["available"])
        shoes[key] = shoe

    for path_code, spec in (links.get("recommendations") or {}).items():
        path = AnswerPath.objects.get(pk=path_code)
        recommendation, _created = Recommendation.objects.get_or_create(market=market, path=path)
        recommendation.items.all().delete()
        position = 1
        for key in spec.get("shoes") or []:
            RecommendationItem.objects.create(
                recommendation=recommendation,
                shoe=shoes[key],
                placement="main",
                position=position,
            )
            position += 1
        for key in spec.get("extras") or []:
            RecommendationItem.objects.create(
                recommendation=recommendation,
                shoe=shoes[key],
                placement="extra",
                position=1,
            )

    # Sakrij patike koje nisu u uvozu ni u unavailable listi.
    market.shoes.exclude(key__in=set(shoes)).update(available=False)
    return {
        "products": len(products),
        "variants": sum(len(p.get("variants") or []) for p in products),
        "active_keys": sorted(active_keys),
        "offer_checked": market.offer_checked,
        "catalog_replaced": True,
    }


def sync_market_from_links(
    market_code,
    scrape=True,
    download_missing_images=True,
    replace_catalog=False,
):
    """Osveži JSON iz links.json.

    Podrazumevano ne dira Shoe/Variant/Recommendation u bazi: kod ne razlikuje
    uvezene zapise od ručnih izmena iz panela, pa se živi katalog ne prepisuje tiho.
    Za početni uvoz ili namerni reset prosledi replace_catalog=True.
    """
    links = load_links(market_code)
    products, offer_checked = _refresh_products_files(
        market_code,
        links,
        scrape=scrape,
        download_missing_images=download_missing_images,
    )
    if not replace_catalog:
        market = Market.objects.filter(pk=market_code).first()
        if market is not None:
            market.offer_checked = offer_checked
            market.save(update_fields=["offer_checked"])
        return {
            "products": len(products),
            "variants": sum(len(p.get("variants") or []) for p in products),
            "active_keys": sorted(item["key"] for item in products),
            "offer_checked": offer_checked,
            "catalog_replaced": False,
        }
    return replace_market_catalog(market_code, products, links, offer_checked)
