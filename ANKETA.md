# ASICS Shoe Finder — sadržaj ankete

Kratki vodič kroz celu anketu (Srbija `/rs/`, Hrvatska `/hr/`, Slovenija `/si/`), da se kasnije brzo snađemo pri izmenama ponude i linkova.

## Kako radi

1. Posetilac odgovara na **3 pitanja**.
2. Odgovori sklapaju **putanju** (`road/comfort/soft`, `trail/light/technical`, …).
3. Za tu putanju se prikazuju **preporučeni modeli** + opcioni **trail extras**.
4. Dugme ka Sport Visionu vodi na **`Variant.store_url`** (konkretna boja/model), ne na search.

Živi podaci idu iz **SQLite baze** (admin + sync). JSON u `finder/data/<market>/` je izvor/backup; `copy.json` i dalje drži prevode.

## Tri pitanja (stablo)

| # | ID pitanja | Opcije | Značenje |
|---|---|---|---|
| 1 | `surface` | `road` / `trail` | Asfalt vs trail |
| 2a | `road` | `comfort` / `speed` | posle asfalta |
| 2b | `trail` | `protection` / `light` | posle traila |
| 3a | `comfort` | `soft` / `support` | mekši korak vs podrška |
| 3b | `speed` | `training` / `race` | trening vs trka |
| 3c | `terrain` | `technical` / `smooth` | neravan vs uređeniji trail |

Tekstovi opcija su po tržištu u `finder/data/<market>/copy.json` → `questions`.

## 8 putanja → modeli

Kod putanje je uvek `odgovor1/odgovor2/odgovor3`.

### Podrazumevano (RS seed / fallback u `finder/paths.py`)

| # | Putanja | Glavni modeli | Extra |
|---|---|---|---|
| 1 | `road/comfort/soft` | gel-nimbus, gel-cumulus, dynablast | — |
| 2 | `road/comfort/support` | gel-kayano, gt-2000 | — |
| 3 | `road/speed/training` | superblast, novablast, noosa-tri, dynablast, versablast | — |
| 4 | `road/speed/race` | metaspeed, magic-speed, noosa-tri | — |
| 5 | `trail/protection/technical` | trabuco-max | blazeblast |
| 6 | `trail/protection/smooth` | trabuco-max | blazeblast |
| 7 | `trail/light/technical` | fujispeed, metafuji-trail | blazeblast |
| 8 | `trail/light/smooth` | fujispeed, metafuji-trail | blazeblast |

### Slovenija (SI) — važi od 06.11.2026.

Izvor istine za linkove i mapiranje: `finder/data/si/links.json`.

| # | Putanja (SLO opis) | Modeli | Napomena |
|---|---|---|---|
| 1 | Asfalt → Udobje → Mehak korak | gel-nimbus, gel-cumulus, dynablast | |
| 2 | Asfalt → Udobje → Dodatna podpora | gel-kayano, gt-2000 | GT-2000 14/15 (+ TR/GTX) |
| 3 | Asfalt → Hitrost → Trening | **megablast**, novablast, noosa-tri, dynablast, versablast | SUPERBLAST uklonjen |
| 4 | Asfalt → Hitrost → Tekme | metaspeed, magic-speed, noosa-tri | Magic Speed 4 i 5 |
| 5–6 | Trail → Zaščita → (oba terena) | trabuco-max | bez blazeblast |
| 7–8 | Trail → Lahkotnost → (oba terena) | fujispeed, metafuji-trail | bez blazeblast |

Nedostupno na SI: `superblast`, `blazeblast`.

Sledeća sezona (napomena klijenta): trail proširiti sa **TRABUCO**, **TRABUCO TERRA**, eventualno **SONOMA**.

### Hrvatska (HR) — važi od 25.11.2026.

Izvor istine: `finder/data/hr/links.json`.

Klijentova CRO lista (`Linkovi za aplikaciju CRO.docx`) koristi **konkretne `sportvision.hr` product URL-ove** za modele koji već postoje u katalogu. Search/fallback ostaje `sportvision.hr/proizvodi/asics`.

Uvezeni iz CRO liste: gel-nimbus (+ TR), gel-cumulus, gel-kayano, gt-2000 (14/15 TR/GTX), novablast, dynablast, versablast, magic-speed, noosa-tri, trabuco-max. Nisu dodati novi modeli iz liste (GEL-PULSE, TRABUCO 14/GTX, TRABUCO TERRA). SUPERBLAST, METASPEED, BLAZEBLAST, FUJISPEED i METAFUJI TRAIL nisu u CRO listi — CTA ide na `sportvision.hr/proizvodi/asics`.

| # | Putanja | Modeli | Extra |
|---|---|---|---|
| 1 | Asfalt → Udobnost → Mekan korak | gel-nimbus, gel-cumulus, dynablast | — |
| 2 | Asfalt → Udobnost → Dodatni oslonac | gel-kayano, gt-2000 | — |
| 3 | Asfalt → Brzina → Trening | superblast, novablast, noosa-tri, dynablast, versablast | — |
| 4 | Asfalt → Brzina → Utrka | metaspeed, magic-speed, noosa-tri | — |
| 5–6 | Trail → Zaštita → (oba terena) | trabuco-max | blazeblast |
| 7–8 | Trail → Lakoća → (oba terena) | fujispeed, metafuji-trail | blazeblast |

Razlika vs SI: HR zadržava **SUPERBLAST** i **BLAZEBLAST**; nema MEGABLAST.

## Fajlovi po tržištu

```
finder/data/<rs|hr|si>/
  market.json     # kod, jezik, offer_checked, GA, store_domain
  copy.json       # svi UI tekstovi + boje
  products.json   # generisani katalog (varijante + URL)
  links.json      # (SI/HR) ručni unos sa Sport Vision linkovima + recommendations
```

Ključni kodovi:

- `finder/paths.py` — 8 putanja, default modeli, family names
- `finder/models.py` — Market, Shoe, Variant, Recommendation
- `finder/catalog.py` — šta frontend dobija (`available=True` only)
- `static/app.js` — kviz UI; fallback `recommendationModels` ako DB nema putanju
- Admin: Patike + Ponude za odgovore

## Početni uvoz i održavanje kataloga

`migrate` / seed stavlja istu RS ponudu na `rs`, `hr` i `si`. Živu SI/HR ponudu iz `links.json` u bazu unosiš jednom:

```bat
python manage.py sync_store_catalog si --no-scrape --replace-catalog
python manage.py sync_store_catalog hr --no-scrape --replace-catalog
```

Sa scrapom Sport Visiona izostavi `--no-scrape`. **`--replace-catalog` zamenjuje patike, varijante i preporuke u bazi** za to tržište.

Srbija nema `finder/data/rs/links.json`. RS katalog ostaje iz seed-a (`finder/data/rs/products.json`) i dalje se menja kroz `/panel/` ili admin.

Posle početnog uvoza, zaposleni održavaju katalog u `/panel/`. Rutinski sync **bez** `--replace-catalog` samo osvežava `products.json` (i datum u `market.json`); **ne dira** živi katalog u bazi, jer kod ne razlikuje uvezene zapise od ručnih izmena.

Namerni reset tržišta iz `links.json`:

```bat
python manage.py sync_store_catalog si --replace-catalog
```

3. Provera: `http://127.0.0.1:8000/si/` pa proći svih 8 putanja i filter Muško/Žensko.

## Pol / boja / analitika

- Pol varijante: `men` | `women` | `unisex` (isti product ID u obe liste → unisex).
- Boje u bazi su **srpski ključevi** (`Crna`, `Plava`, …); prevod je u `copy.json` → `colors`.
- `Shoe.key` se **ne menja** za postojeće modele (analitika). Novi model (npr. `megablast`) mora u `shoeCode` / `familyNames` u `static/app.js` i u `FAMILY_NAMES`.

## Deploy napomena

`db.sqlite3` i `media/` ostaju na serveru. Posle početne instalacije baza je izvor kataloga za kviz.

- **Nova baza:** `migrate`, pa jednom `sync_store_catalog si|hr --replace-catalog` (po potrebi `--no-scrape`).
- **Postojeća baza:** deploy koda + `pip install -r requirements.txt` + `migrate` + `collectstatic`. **Ne** treba sync ni ponovni uvoz kataloga. **Ne** pokretati `--replace-catalog` ako urednici već rade u panelu.

`products.json` / `links.json` ostaju za seed i početni uvoz; javni kviz ih ne koristi kao živi katalog.
