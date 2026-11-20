from django.core.management.base import BaseCommand, CommandError

from finder.markets import market_exists
from finder.store_sync import sync_market_from_links


class Command(BaseCommand):
    help = (
        "Učitaj links.json za tržište i osveži products.json. "
        "Živi katalog u bazi se menja samo uz --replace-catalog."
    )

    def add_arguments(self, parser):
        parser.add_argument("market", help="Kod tržišta, npr. si ili hr")
        parser.add_argument(
            "--no-scrape",
            action="store_true",
            help="Ne scrapuj sajt; koristi postojeći products.json",
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Ne preuzimaj slike koje fale u assets/",
        )
        parser.add_argument(
            "--replace-catalog",
            action="store_true",
            help=(
                "Zameni patike, varijante i preporuke u bazi podacima iz links/products. "
                "Briše ručne izmene iz panela za to tržište. Koristi samo za početni uvoz ili namerni reset."
            ),
        )

    def handle(self, *args, **options):
        market = options["market"].lower()
        if not market_exists(market):
            raise CommandError(f"Nepoznato tržište: {market}")
        links_path = f"finder/data/{market}/links.json"
        try:
            summary = sync_market_from_links(
                market,
                scrape=not options["no_scrape"],
                download_missing_images=not options["no_images"],
                replace_catalog=options["replace_catalog"],
            )
        except FileNotFoundError as exc:
            raise CommandError(f"Nedostaje {links_path}: {exc}") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"{market}: {summary['products']} modela, {summary['variants']} varijanti, "
                f"ponuda {summary['offer_checked']}"
            )
        )
        self.stdout.write("Aktivni u JSON: " + ", ".join(summary["active_keys"]))
        if summary.get("catalog_replaced"):
            self.stdout.write(self.style.WARNING("Živi katalog u bazi je zamenjen (--replace-catalog)."))
        else:
            self.stdout.write(
                "Živi katalog u bazi nije dirnut. "
                "Za početni uvoz ili namerni reset dodaj --replace-catalog."
            )
