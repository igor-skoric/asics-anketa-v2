import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

# Jezik u ?lang= i primarni kod iz Accept-Language.
LANG_TO_MARKET = {
    "sr": "rs",
    "hr": "hr",
    "sl": "si",
}

# ISO država iz CF-IPCountry / X-Country-Code.
COUNTRY_TO_MARKET = {
    "RS": "rs",
    "HR": "hr",
    "SI": "si",
}


def market_exists(code):
    return (DATA_DIR / code / "market.json").is_file()


def get_market(code):
    folder = DATA_DIR / code
    if not market_exists(code):
        return None
    market = _read(folder / "market.json")
    market["copy"] = _read(folder / "copy.json")
    market["products"] = _read(folder / "products.json")
    return market


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def market_from_token(value):
    token = (value or "").strip().lower()
    if not token:
        return None
    if market_exists(token):
        return token
    return LANG_TO_MARKET.get(token)


def market_from_country(value):
    return COUNTRY_TO_MARKET.get((value or "").strip().upper())


def market_from_accept_language(header):
    for item in (header or "").split(","):
        lang = item.split(";", 1)[0].strip().lower()
        if not lang:
            continue
        market = LANG_TO_MARKET.get(lang.split("-", 1)[0])
        if market:
            return market
    return None
