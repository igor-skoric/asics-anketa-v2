from django.db import models
from django.utils.text import slugify

from .paths import ANSWER_PATHS


class Market(models.Model):
    code = models.CharField("Kod", max_length=8, primary_key=True)
    country = models.CharField("Država", max_length=40)
    locale = models.CharField("Jezik", max_length=8)
    offer_checked = models.CharField("Ponuda proverena", max_length=20)
    ga_ids = models.JSONField("Measurement ID-jevi", default=list)
    store_domain = models.URLField("Prodavnica", max_length=200, blank=True)

    class Meta:
        verbose_name = "Tržište"
        verbose_name_plural = "Tržišta"
        ordering = ["code"]

    def __str__(self):
        return self.country


class AnswerPath(models.Model):
    code = models.CharField(max_length=64, primary_key=True)
    label = models.CharField("Kombinacija", max_length=160)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Kombinacija odgovora"
        verbose_name_plural = "Kombinacije odgovora"
        ordering = ["position"]

    def __str__(self):
        return self.label


class Shoe(models.Model):
    market = models.ForeignKey(Market, verbose_name="Tržište", related_name="shoes", on_delete=models.CASCADE)
    key = models.SlugField("Kod", max_length=64, blank=True, help_text="Kratak kod, npr. gel-nimbus. Prazno polje se popuni iz naziva. Kod postojećeg modela nemoj menjati: analitika ga koristi.")
    family_name = models.CharField("Naziv na kartici", max_length=80, help_text="Kako se model zove na rezultatu, npr. GEL-NIMBUS™.")
    model_name = models.CharField("Puno ime modela", max_length=80, help_text="Npr. GEL-NIMBUS 28.")
    filename = models.CharField("Slika iz assets", max_length=200, blank=True, help_text="Postojeća slika, npr. gel-nimbus.webp. Nova otpremljena slika ima prednost.")
    photo = models.ImageField("Nova slika", upload_to="shoes/", blank=True)
    available = models.BooleanField("Prikazana u ponudi", default=True)

    class Meta:
        verbose_name = "Patika"
        verbose_name_plural = "Patike"
        ordering = ["market", "family_name"]
        constraints = [
            models.UniqueConstraint(fields=["market", "key"], name="unique_shoe_key_per_market"),
        ]

    def __str__(self):
        return f"{self.market.country}: {self.family_name}"

    def save(self, *args, **kwargs):
        if not self.key:
            base = slugify(self.family_name or self.model_name)[:60] or "patika"
            candidate = base
            number = 2
            taken = Shoe.objects.filter(market=self.market, key=candidate)
            if self.pk:
                taken = taken.exclude(pk=self.pk)
            while taken.exists():
                candidate = f"{base}-{number}"
                number += 1
                taken = Shoe.objects.filter(market=self.market, key=candidate)
                if self.pk:
                    taken = taken.exclude(pk=self.pk)
            self.key = candidate
        super().save(*args, **kwargs)


class Variant(models.Model):
    class Gender(models.TextChoices):
        MEN = "men", "Muške"
        WOMEN = "women", "Ženske"
        UNISEX = "unisex", "Unisex"

    shoe = models.ForeignKey(Shoe, verbose_name="Patika", related_name="variants", on_delete=models.CASCADE)
    external_id = models.CharField(max_length=32, blank=True)
    sku = models.CharField("Šifra", max_length=32)
    gender = models.CharField("Pol", max_length=16, choices=Gender.choices)
    color = models.CharField(
        "Boja",
        max_length=40,
        help_text="Plava, Zelena, Bela, Crna, Bež, Roze, Ljubičasta ili Multicolor. Prevod boje ide iz jezika tržišta.",
    )
    filename = models.CharField("Slika iz assets", max_length=200, blank=True)
    photo = models.ImageField("Nova slika", upload_to="variants/", blank=True)
    store_url = models.URLField("Link ka proizvodu", max_length=500)
    available_size_count = models.PositiveIntegerField("Broj veličina", default=0)
    position = models.PositiveIntegerField("Redosled", default=1)

    class Meta:
        verbose_name = "Varijanta"
        verbose_name_plural = "Varijante"
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["shoe", "sku"], name="unique_variant_sku_per_shoe"),
        ]

    def __str__(self):
        return f"{self.get_gender_display()} · {self.color} · {self.sku}"


class Recommendation(models.Model):
    market = models.ForeignKey(Market, verbose_name="Tržište", related_name="recommendations", on_delete=models.CASCADE)
    path = models.ForeignKey(AnswerPath, verbose_name="Odgovori", related_name="recommendations", on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Ponuda za odgovore"
        verbose_name_plural = "Ponude za odgovore"
        ordering = ["market", "path"]
        constraints = [
            models.UniqueConstraint(fields=["market", "path"], name="unique_recommendation_per_market_path"),
        ]

    def __str__(self):
        return f"{self.market.country}: {self.path.label}"


class RecommendationItem(models.Model):
    class Placement(models.TextChoices):
        MAIN = "main", "Glavni predlog"
        EXTRA = "extra", "Dodatni model"

    recommendation = models.ForeignKey(Recommendation, related_name="items", on_delete=models.CASCADE)
    shoe = models.ForeignKey(Shoe, verbose_name="Patika", related_name="placements", on_delete=models.CASCADE)
    placement = models.CharField("Mesto", max_length=16, choices=Placement.choices, default=Placement.MAIN)
    position = models.PositiveIntegerField("Redosled", default=1)

    class Meta:
        verbose_name = "Patika u ponudi"
        verbose_name_plural = "Patike u ponudi"
        ordering = ["placement", "position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["recommendation", "shoe"], name="unique_shoe_per_recommendation"),
        ]

    def __str__(self):
        return f"{self.get_placement_display()}: {self.shoe.family_name}"


def answer_path_labels():
    return {code: label for code, label, _position in ANSWER_PATHS}
