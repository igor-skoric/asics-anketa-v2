"""Excel izvoz/uvoz kataloga za jedno tržište (panel)."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from openpyxl import Workbook, load_workbook

from .models import AnswerPath, Recommendation, RecommendationItem, Shoe, Variant
from .panel_forms import COLOR_CHOICES

SHEET_GUIDE = "Uputstvo"
SHEET_SHOES = "Patike"
SHEET_VARIANTS = "Varijante"
SHEET_PLACES = "Preporuke"

SHOE_HEADERS = ("ID patike", "Ref", "Naziv na kartici", "Puno ime modela", "Prikazana")
VARIANT_HEADERS = ("ID varijante", "ID patike", "Ref patike", "Redosled", "Pol", "Boja", "Šifra", "Link")
PLACE_HEADERS = ("ID patike", "Ref patike", "Kod putanje", "Uloga")

YES = {"da", "yes", "true", "1", "on"}
NO = {"ne", "no", "false", "0", "off"}
GENDER_MAP = {
    "men": "men",
    "muške": "men",
    "muske": "men",
    "muški": "men",
    "muski": "men",
    "women": "women",
    "ženske": "women",
    "zenske": "women",
    "ženski": "women",
    "zenski": "women",
    "unisex": "unisex",
}
PLACE_MAP = {
    "main": "main",
    "glavni": "main",
    "glavni predlog": "main",
    "extra": "extra",
    "dodatni": "extra",
    "dodatni model": "extra",
    "ukloni": "ukloni",
    "ne": "ukloni",
    "ne prikazuj": "ukloni",
}
ALLOWED_COLORS = {choice[0] for choice in COLOR_CHOICES}

GUIDE_LINES = [
    "ASICS Shoe Finder — katalog za jedno tržište",
    "",
    "1. Izvezi katalog sa stranice tržišta u panelu.",
    "2. Menjaj samo listove Patike, Varijante i Preporuke.",
    "3. ID kolone su stabilni identifikatori. Ne menjaj ID ako menjaš naziv ili šifru — inače nastaje duplikat.",
    "4. Prazan ID = novi red. Za novu patiku upiši Ref (npr. NOVO-1) i isti Ref u Varijante/Preporuke.",
    "5. Prazna ćelija = bez izmene postojeće vrednosti. Izostavljen red ne briše zapis.",
    "6. Prikazana: da ili ne (obavezno za isključenje iz ponude).",
    "7. Uloga: glavni, dodatni ili ukloni (ukloni skida preporuku sa putanje).",
    "8. Pol: muške / ženske / unisex. Boja: Plava, Zelena, Bela, Crna, Bež, Roze, Ljubičasta, Multicolor.",
    "9. Slike se ne menjaju ovim fajlom — ostaju postojeće; nove se dodaju u formi patike.",
    "10. Uvoz važi samo za tržište sa kog je fajl preuzet.",
]


@dataclass
class CellError:
    sheet: str
    row: int
    column: str
    message: str


@dataclass
class PreviewChange:
    kind: str  # add | change | same
    sheet: str
    summary: str
    detail: str = ""


@dataclass
class ImportPreview:
    market_code: str
    revision: str
    errors: list[CellError] = field(default_factory=list)
    changes: list[PreviewChange] = field(default_factory=list)
    ops: dict = field(default_factory=dict)

    @property
    def ok(self):
        return not self.errors

    @property
    def change_count(self):
        return sum(1 for item in self.changes if item.kind != "same")


def market_revision(market):
    """Otisak kataloga: ako se promeni između pregleda i potvrde, traži se novi pregled."""
    parts = []
    for shoe in market.shoes.prefetch_related("variants", "placements").order_by("pk"):
        parts.append(
            f"s:{shoe.pk}:{shoe.family_name}:{shoe.model_name}:{int(shoe.available)}:{shoe.key}"
        )
        for variant in shoe.variants.order_by("pk"):
            parts.append(
                f"v:{variant.pk}:{shoe.pk}:{variant.position}:{variant.gender}:{variant.color}:"
                f"{variant.sku}:{variant.store_url}"
            )
        for item in shoe.placements.select_related("recommendation").order_by("pk"):
            parts.append(
                f"p:{item.pk}:{item.recommendation.path_id}:{item.placement}:{item.position}"
            )
    raw = "\n".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def export_workbook(market) -> bytes:
    wb = Workbook()
    guide = wb.active
    guide.title = SHEET_GUIDE
    for index, line in enumerate(GUIDE_LINES, start=1):
        guide.cell(index, 1, line)
    guide.column_dimensions["A"].width = 100

    shoes_ws = wb.create_sheet(SHEET_SHOES)
    shoes_ws.append(list(SHOE_HEADERS))
    for shoe in market.shoes.order_by("family_name", "pk"):
        shoes_ws.append(
            [
                shoe.pk,
                "",
                shoe.family_name,
                shoe.model_name,
                "da" if shoe.available else "ne",
            ]
        )

    variants_ws = wb.create_sheet(SHEET_VARIANTS)
    variants_ws.append(list(VARIANT_HEADERS))
    for shoe in market.shoes.prefetch_related("variants").order_by("family_name", "pk"):
        for variant in shoe.variants.order_by("position", "pk"):
            variants_ws.append(
                [
                    variant.pk,
                    shoe.pk,
                    "",
                    variant.position,
                    variant.gender,
                    variant.color,
                    variant.sku,
                    variant.store_url,
                ]
            )

    places_ws = wb.create_sheet(SHEET_PLACES)
    places_ws.append(list(PLACE_HEADERS))
    path_codes = list(AnswerPath.objects.order_by("position").values_list("pk", flat=True))
    places_ws.append(["", "", "Dozvoljeni kodovi putanje:", ", ".join(path_codes)])
    for shoe in market.shoes.prefetch_related("placements__recommendation").order_by("family_name", "pk"):
        for item in shoe.placements.all():
            places_ws.append(
                [
                    shoe.pk,
                    "",
                    item.recommendation.path_id,
                    "glavni" if item.placement == "main" else "dodatni",
                ]
            )

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cell(row_values, headers, name):
    try:
        index = headers.index(name)
    except ValueError:
        return None
    if index >= len(row_values):
        return None
    value = row_values[index]
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, Decimal):
        value = int(value) if value == value.to_integral_value() else str(value)
    text = str(value).strip()
    return text if text != "" else None


def _read_sheet(wb, name):
    if name not in wb.sheetnames:
        return None, []
    ws = wb[name]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []
    headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    body = []
    for offset, row in enumerate(rows[1:], start=2):
        if row is None or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        # Skip helper rows on Preporuke
        first = row[0] if row else None
        if name == SHEET_PLACES and first in (None, "") and row[2] and "Dozvoljeni" in str(row[2]):
            continue
        body.append((offset, list(row)))
    return headers, body


def _parse_bool(raw, sheet, row, column, errors, required=False):
    if raw is None:
        if required:
            errors.append(CellError(sheet, row, column, "Obavezno polje (da ili ne)."))
        return None
    key = raw.casefold()
    if key in YES:
        return True
    if key in NO:
        return False
    errors.append(CellError(sheet, row, column, "Dozvoljeno je samo da ili ne."))
    return None


def _parse_int(raw, sheet, row, column, errors):
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        errors.append(CellError(sheet, row, column, "Očekivan je broj."))
        return None


def _parse_gender(raw, sheet, row, column, errors):
    if raw is None:
        return None
    mapped = GENDER_MAP.get(raw.casefold())
    if not mapped:
        errors.append(CellError(sheet, row, column, "Pol mora biti muške, ženske ili unisex."))
        return None
    return mapped


def _parse_place(raw, sheet, row, column, errors):
    if raw is None:
        return None
    mapped = PLACE_MAP.get(raw.casefold())
    if not mapped:
        errors.append(CellError(sheet, row, column, "Uloga: glavni, dodatni ili ukloni."))
        return None
    return mapped


def build_preview(market, file_bytes) -> ImportPreview:
    preview = ImportPreview(market_code=market.code, revision=market_revision(market))
    try:
        wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception:
        preview.errors.append(CellError(SHEET_GUIDE, 1, "fajl", "Fajl nije važeći .xlsx."))
        return preview

    shoe_headers, shoe_rows = _read_sheet(wb, SHEET_SHOES)
    variant_headers, variant_rows = _read_sheet(wb, SHEET_VARIANTS)
    place_headers, place_rows = _read_sheet(wb, SHEET_PLACES)
    if shoe_headers is None or variant_headers is None or place_headers is None:
        preview.errors.append(
            CellError(SHEET_GUIDE, 1, "listovi", "Nedostaju listovi Patike, Varijante ili Preporuke.")
        )
        return preview

    for required, headers, sheet in (
        (SHOE_HEADERS, shoe_headers, SHEET_SHOES),
        (VARIANT_HEADERS, variant_headers, SHEET_VARIANTS),
        (PLACE_HEADERS, place_headers, SHEET_PLACES),
    ):
        missing = [name for name in required if name not in headers]
        if missing:
            preview.errors.append(
                CellError(sheet, 1, ", ".join(missing), "Nedostaju kolone u zaglavlju.")
            )
            return preview

    existing_shoes = {shoe.pk: shoe for shoe in market.shoes.all()}
    existing_variants = {
        variant.pk: variant
        for variant in Variant.objects.filter(shoe__market=market).select_related("shoe")
    }
    path_ids = set(AnswerPath.objects.values_list("pk", flat=True))

    shoe_ops = []
    ref_to_op = {}
    seen_refs = set()

    for row_number, values in shoe_rows:
        shoe_id = _parse_int(_cell(values, shoe_headers, "ID patike"), SHEET_SHOES, row_number, "ID patike", preview.errors)
        ref = _cell(values, shoe_headers, "Ref")
        family = _cell(values, shoe_headers, "Naziv na kartici")
        model = _cell(values, shoe_headers, "Puno ime modela")
        available = _parse_bool(
            _cell(values, shoe_headers, "Prikazana"),
            SHEET_SHOES,
            row_number,
            "Prikazana",
            preview.errors,
            required=shoe_id is None,
        )

        if shoe_id is not None and shoe_id not in existing_shoes:
            preview.errors.append(
                CellError(SHEET_SHOES, row_number, "ID patike", "ID ne pripada ovom tržištu.")
            )
            continue

        if shoe_id is None:
            if not family:
                preview.errors.append(
                    CellError(SHEET_SHOES, row_number, "Naziv na kartici", "Obavezno za novu patiku.")
                )
                continue
            if not model:
                preview.errors.append(
                    CellError(SHEET_SHOES, row_number, "Puno ime modela", "Obavezno za novu patiku.")
                )
                continue
            if available is None:
                continue
            ref = ref or f"NOVO-{row_number}"
            if ref in seen_refs:
                preview.errors.append(CellError(SHEET_SHOES, row_number, "Ref", "Ref mora biti jedinstven."))
                continue
            seen_refs.add(ref)
            op = {
                "action": "add",
                "row": row_number,
                "ref": ref,
                "family_name": family,
                "model_name": model,
                "available": available,
            }
            shoe_ops.append(op)
            ref_to_op[ref] = op
            preview.changes.append(
                PreviewChange("add", SHEET_SHOES, f"Nova patika {family}", f"red {row_number}")
            )
            continue

        shoe = existing_shoes[shoe_id]
        fields = {}
        if family is not None and family != shoe.family_name:
            fields["family_name"] = family
        if model is not None and model != shoe.model_name:
            fields["model_name"] = model
        if available is not None and available != shoe.available:
            fields["available"] = available
        if fields:
            shoe_ops.append({"action": "change", "row": row_number, "shoe_id": shoe_id, "fields": fields})
            preview.changes.append(
                PreviewChange(
                    "change",
                    SHEET_SHOES,
                    f"Izmena {shoe.family_name}",
                    ", ".join(f"{k}={v}" for k, v in fields.items()),
                )
            )
        else:
            preview.changes.append(
                PreviewChange("same", SHEET_SHOES, f"Bez izmene: {shoe.family_name}", f"ID {shoe_id}")
            )

    variant_ops = []
    for row_number, values in variant_rows:
        variant_id = _parse_int(
            _cell(values, variant_headers, "ID varijante"), SHEET_VARIANTS, row_number, "ID varijante", preview.errors
        )
        shoe_id = _parse_int(
            _cell(values, variant_headers, "ID patike"), SHEET_VARIANTS, row_number, "ID patike", preview.errors
        )
        shoe_ref = _cell(values, variant_headers, "Ref patike")
        position_raw = _cell(values, variant_headers, "Redosled")
        gender = _parse_gender(
            _cell(values, variant_headers, "Pol"), SHEET_VARIANTS, row_number, "Pol", preview.errors
        )
        color = _cell(values, variant_headers, "Boja")
        sku = _cell(values, variant_headers, "Šifra")
        store_url = _cell(values, variant_headers, "Link")
        position = _parse_int(position_raw, SHEET_VARIANTS, row_number, "Redosled", preview.errors) if position_raw else None

        if color is not None:
            current = None
            if variant_id and variant_id in existing_variants:
                current = existing_variants[variant_id].color
            allowed = set(ALLOWED_COLORS)
            if current:
                allowed.add(current)
            if color not in allowed:
                preview.errors.append(
                    CellError(SHEET_VARIANTS, row_number, "Boja", "Boja nije sa dozvoljene liste.")
                )
                color = None

        if variant_id is not None:
            if variant_id not in existing_variants:
                preview.errors.append(
                    CellError(SHEET_VARIANTS, row_number, "ID varijante", "ID ne pripada ovom tržištu.")
                )
                continue
            variant = existing_variants[variant_id]
            if shoe_id is not None and shoe_id != variant.shoe_id:
                preview.errors.append(
                    CellError(SHEET_VARIANTS, row_number, "ID patike", "Varijanta ne pripada toj patiki.")
                )
                continue
            fields = {}
            if position is not None and position != variant.position:
                fields["position"] = position
            if gender is not None and gender != variant.gender:
                fields["gender"] = gender
            if color is not None and color != variant.color:
                fields["color"] = color
            if sku is not None and sku != variant.sku:
                fields["sku"] = sku
            if store_url is not None and store_url != variant.store_url:
                fields["store_url"] = store_url
            if fields:
                if "sku" in fields:
                    clash = (
                        Variant.objects.filter(shoe_id=variant.shoe_id, sku__iexact=fields["sku"])
                        .exclude(pk=variant.pk)
                        .exists()
                    )
                    if clash:
                        preview.errors.append(
                            CellError(SHEET_VARIANTS, row_number, "Šifra", "Šifra već postoji na ovoj patiki.")
                        )
                        continue
                variant_ops.append(
                    {"action": "change", "row": row_number, "variant_id": variant_id, "fields": fields}
                )
                preview.changes.append(
                    PreviewChange(
                        "change",
                        SHEET_VARIANTS,
                        f"Izmena varijante {variant.sku}",
                        ", ".join(f"{k}={v}" for k, v in fields.items()),
                    )
                )
            else:
                preview.changes.append(
                    PreviewChange("same", SHEET_VARIANTS, f"Bez izmene: {variant.sku}", f"ID {variant_id}")
                )
            continue

        # new variant
        if not sku or gender is None or not color or not store_url:
            preview.errors.append(
                CellError(
                    SHEET_VARIANTS,
                    row_number,
                    "Šifra/Pol/Boja/Link",
                    "Nova varijanta zahteva pol, boju, šifru i link.",
                )
            )
            continue
        target_shoe_id = shoe_id
        target_ref = None
        if shoe_id is not None:
            if shoe_id not in existing_shoes:
                preview.errors.append(
                    CellError(SHEET_VARIANTS, row_number, "ID patike", "ID ne pripada ovom tržištu.")
                )
                continue
        elif shoe_ref:
            if shoe_ref not in ref_to_op:
                preview.errors.append(
                    CellError(SHEET_VARIANTS, row_number, "Ref patike", "Nepoznat Ref nove patike.")
                )
                continue
            target_ref = shoe_ref
        else:
            preview.errors.append(
                CellError(SHEET_VARIANTS, row_number, "ID patike", "Upiši ID postojeće ili Ref nove patike.")
            )
            continue

        if target_shoe_id and Variant.objects.filter(shoe_id=target_shoe_id, sku__iexact=sku).exists():
            preview.errors.append(
                CellError(SHEET_VARIANTS, row_number, "Šifra", "Šifra već postoji na ovoj patiki.")
            )
            continue

        variant_ops.append(
            {
                "action": "add",
                "row": row_number,
                "shoe_id": target_shoe_id,
                "shoe_ref": target_ref,
                "position": position or 1,
                "gender": gender,
                "color": color,
                "sku": sku,
                "store_url": store_url,
            }
        )
        preview.changes.append(
            PreviewChange("add", SHEET_VARIANTS, f"Nova varijanta {sku}", f"red {row_number}")
        )

    place_ops = []
    for row_number, values in place_rows:
        shoe_id = _parse_int(
            _cell(values, place_headers, "ID patike"), SHEET_PLACES, row_number, "ID patike", preview.errors
        )
        shoe_ref = _cell(values, place_headers, "Ref patike")
        path_code = _cell(values, place_headers, "Kod putanje")
        role = _parse_place(
            _cell(values, place_headers, "Uloga"), SHEET_PLACES, row_number, "Uloga", preview.errors
        )
        if not path_code or role is None:
            if path_code or role is not None or shoe_id or shoe_ref:
                preview.errors.append(
                    CellError(SHEET_PLACES, row_number, "Kod putanje/Uloga", "Upiši kod putanje i ulogu.")
                )
            continue
        if path_code not in path_ids:
            preview.errors.append(CellError(SHEET_PLACES, row_number, "Kod putanje", "Nepoznata putanja."))
            continue

        target_shoe_id = shoe_id
        target_ref = None
        if shoe_id is not None:
            if shoe_id not in existing_shoes:
                preview.errors.append(
                    CellError(SHEET_PLACES, row_number, "ID patike", "ID ne pripada ovom tržištu.")
                )
                continue
        elif shoe_ref:
            if shoe_ref not in ref_to_op:
                preview.errors.append(
                    CellError(SHEET_PLACES, row_number, "Ref patike", "Nepoznat Ref nove patike.")
                )
                continue
            target_ref = shoe_ref
        else:
            preview.errors.append(
                CellError(SHEET_PLACES, row_number, "ID patike", "Upiši ID postojeće ili Ref nove patike.")
            )
            continue

        current = None
        if target_shoe_id:
            current = (
                RecommendationItem.objects.filter(
                    shoe_id=target_shoe_id, recommendation__market=market, recommendation__path_id=path_code
                )
                .values_list("placement", flat=True)
                .first()
            )
        desired = None if role == "ukloni" else role
        if current == desired and target_shoe_id:
            preview.changes.append(
                PreviewChange("same", SHEET_PLACES, f"Bez izmene: {path_code}", f"patika {target_shoe_id}")
            )
            continue
        place_ops.append(
            {
                "action": "set",
                "row": row_number,
                "shoe_id": target_shoe_id,
                "shoe_ref": target_ref,
                "path_id": path_code,
                "placement": desired,
            }
        )
        label = "ukloni" if desired is None else desired
        preview.changes.append(
            PreviewChange("change" if target_shoe_id else "add", SHEET_PLACES, f"{path_code} → {label}", f"red {row_number}")
        )

    preview.ops = {"shoes": shoe_ops, "variants": variant_ops, "places": place_ops}
    return preview


def apply_preview(market, preview: ImportPreview):
    if market.code != preview.market_code:
        raise ValueError("Tržište se ne poklapa.")
    if market_revision(market) != preview.revision:
        raise RuntimeError("revision")
    if preview.errors:
        raise ValueError("preview has errors")

    with transaction.atomic():
        ref_map = {}
        for op in preview.ops.get("shoes", []):
            if op["action"] == "add":
                shoe = Shoe(
                    market=market,
                    family_name=op["family_name"],
                    model_name=op["model_name"],
                    available=op["available"],
                )
                shoe.save()
                ref_map[op["ref"]] = shoe.pk
            elif op["action"] == "change":
                shoe = Shoe.objects.select_for_update().get(pk=op["shoe_id"], market=market)
                for key, value in op["fields"].items():
                    setattr(shoe, key, value)
                shoe.save()

        for op in preview.ops.get("variants", []):
            if op["action"] == "add":
                shoe_id = op["shoe_id"] or ref_map.get(op["shoe_ref"])
                shoe = Shoe.objects.select_for_update().get(pk=shoe_id, market=market)
                Variant.objects.create(
                    shoe=shoe,
                    position=op["position"],
                    gender=op["gender"],
                    color=op["color"],
                    sku=op["sku"],
                    store_url=op["store_url"],
                )
            elif op["action"] == "change":
                variant = Variant.objects.select_for_update().select_related("shoe").get(pk=op["variant_id"])
                if variant.shoe.market_id != market.code:
                    raise ValueError("variant market mismatch")
                for key, value in op["fields"].items():
                    setattr(variant, key, value)
                variant.save()

        for op in preview.ops.get("places", []):
            shoe_id = op["shoe_id"] or ref_map.get(op["shoe_ref"])
            shoe = Shoe.objects.select_for_update().get(pk=shoe_id, market=market)
            path = AnswerPath.objects.get(pk=op["path_id"])
            recommendation, _created = Recommendation.objects.get_or_create(market=market, path=path)
            item = RecommendationItem.objects.filter(recommendation=recommendation, shoe=shoe).first()
            placement = op["placement"]
            if placement is None:
                if item:
                    item.delete()
                continue
            if item:
                if item.placement != placement:
                    item.placement = placement
                    item.save(update_fields=["placement"])
            else:
                last = recommendation.items.filter(placement=placement).order_by("-position").first()
                RecommendationItem.objects.create(
                    recommendation=recommendation,
                    shoe=shoe,
                    placement=placement,
                    position=(last.position + 1) if last else 1,
                )


def preview_to_session(preview: ImportPreview) -> dict:
    return {
        "market_code": preview.market_code,
        "revision": preview.revision,
        "errors": [error.__dict__ for error in preview.errors],
        "changes": [change.__dict__ for change in preview.changes],
        "ops": preview.ops,
    }


def preview_from_session(payload: dict) -> ImportPreview:
    return ImportPreview(
        market_code=payload["market_code"],
        revision=payload["revision"],
        errors=[CellError(**item) for item in payload.get("errors") or []],
        changes=[PreviewChange(**item) for item in payload.get("changes") or []],
        ops=payload.get("ops") or {},
    )


def dump_preview_token(preview: ImportPreview) -> str:
    return json.dumps(preview_to_session(preview), ensure_ascii=False, separators=(",", ":"))


def load_preview_token(raw: str) -> ImportPreview:
    return preview_from_session(json.loads(raw))
