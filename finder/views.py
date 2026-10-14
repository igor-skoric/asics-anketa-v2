from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse

from .catalog import public_catalog
from .markets import (
    get_market,
    market_from_accept_language,
    market_from_country,
    market_from_token,
)

MARKET_COOKIE = "asics_market"
COOKIE_MAX_AGE = 60 * 60 * 24 * 180
COUNTRY_HEADERS = (
    "HTTP_CF_IPCOUNTRY",
    "HTTP_CLOUDFRONT_VIEWER_COUNTRY",
    "HTTP_X_COUNTRY_CODE",
)


def entry(request):
    market = _market_from_request(request)
    response = HttpResponseRedirect(reverse("finder", kwargs={"market": market}))
    return _remember(response, market)


def finder(request, market):
    data = get_market(market)
    if data is None:
        raise Http404("Nepoznato tržište.")
    asset_base = static("assets")
    if not asset_base.endswith("/"):
        asset_base += "/"
    catalog = public_catalog(market)
    products = catalog["products"] if catalog else data["products"]
    recommendations = catalog["recommendations"] if catalog else {}
    ga_ids = catalog["ga_ids"] if catalog else data["ga_ids"]
    offer_checked = catalog["offer_checked"] if catalog else data["offer_checked"]
    response = render(
        request,
        "finder/index.html",
        {
            "market": data,
            "copy": data["copy"],
            "products": products,
            "config": {
                "market": data["code"],
                "gaIds": ga_ids,
                "assetBase": asset_base,
                "offerChecked": offer_checked,
                "recommendations": recommendations,
            },
        },
    )
    return _remember(response, data["code"])


def _market_from_request(request):
    for key in ("market", "lang", "country"):
        found = market_from_token(request.GET.get(key)) or market_from_country(request.GET.get(key))
        if found:
            return found
    cookie = market_from_token(request.COOKIES.get(MARKET_COOKIE))
    if cookie:
        return cookie
    for header in COUNTRY_HEADERS:
        found = market_from_country(request.META.get(header))
        if found:
            return found
    return market_from_accept_language(request.META.get("HTTP_ACCEPT_LANGUAGE", "")) or "rs"


def _remember(response, market):
    response.set_cookie(
        MARKET_COOKIE,
        market,
        max_age=COOKIE_MAX_AGE,
        path="/",
        samesite="Lax",
    )
    return response
