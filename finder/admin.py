from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Market, Recommendation, RecommendationItem, Shoe, Variant

admin.site.site_header = "ASICS Shoe Finder"
admin.site.site_title = "Shoe Finder"
admin.site.index_title = "Patike po tržištu i kombinaciji odgovora"


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1
    fields = ("position", "gender", "color", "sku", "store_url", "filename", "photo", "available_size_count")


class RecommendationItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        market_id = self.instance.market_id or self.data.get("market")
        if not market_id:
            return
        seen = set()
        invalid = False
        for form in self.forms:
            cleaned = getattr(form, "cleaned_data", None) or {}
            if not cleaned or cleaned.get("DELETE"):
                continue
            shoe = cleaned.get("shoe")
            if shoe is None:
                continue
            if str(shoe.market_id) != str(market_id):
                form.add_error("shoe", "Izaberi patiku sa istog tržišta.")
                invalid = True
            if shoe.pk in seen:
                form.add_error("shoe", "Ova patika je već dodata u ovu kombinaciju.")
                invalid = True
            seen.add(shoe.pk)
        if invalid:
            raise ValidationError("Proveri patike u listi.")


class RecommendationItemInline(admin.TabularInline):
    model = RecommendationItem
    formset = RecommendationItemFormSet
    extra = 1
    fields = ("position", "placement", "shoe")
    ordering = ("placement", "position")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "shoe":
            object_id = request.resolver_match.kwargs.get("object_id")
            if object_id:
                recommendation = Recommendation.objects.filter(pk=object_id).only("market_id").first()
                if recommendation:
                    kwargs["queryset"] = Shoe.objects.filter(market_id=recommendation.market_id).order_by("family_name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Shoe)
class ShoeAdmin(admin.ModelAdmin):
    list_display = ("family_name", "model_name", "market", "variant_count")
    list_filter = ("market",)
    search_fields = ("family_name", "model_name", "key", "market__country")
    inlines = [VariantInline]
    fieldsets = (
        (None, {"fields": ("market", "family_name", "model_name", "key", "available")}),
        ("Slika", {"fields": ("photo", "filename")}),
    )

    @admin.display(description="Varijante")
    def variant_count(self, obj):
        return obj.variants.count()


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("market", "path", "main_shoes", "extra_shoes")
    list_filter = ("market", "path")
    search_fields = ("path__label", "market__country", "items__shoe__family_name")
    inlines = [RecommendationItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("items__shoe")

    @admin.display(description="Glavni predlozi")
    def main_shoes(self, obj):
        return ", ".join(item.shoe.family_name for item in obj.items.all() if item.placement == "main") or "—"

    @admin.display(description="Dodatni model")
    def extra_shoes(self, obj):
        return ", ".join(item.shoe.family_name for item in obj.items.all() if item.placement == "extra") or "—"


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ("country", "code", "locale", "offer_checked")
    fields = ("code", "country", "locale", "offer_checked", "ga_ids", "store_domain")

    def has_delete_permission(self, request, obj=None):
        return False
