from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.forms.models import BaseInlineFormSet, inlineformset_factory

from .models import Market, Variant, Shoe

COLOR_CHOICES = (
    ("Plava", "Plava"),
    ("Zelena", "Zelena"),
    ("Bela", "Bela"),
    ("Crna", "Crna"),
    ("Bež", "Bež"),
    ("Roze", "Roze"),
    ("Ljubičasta", "Ljubičasta"),
    ("Multicolor", "Multicolor"),
)

VARIANT_MAX = 10


def _photo_widget():
    return forms.FileInput(attrs={"accept": "image/*", "class": "visually-hidden"})


def _style_controls(form, *names):
    for name in names:
        field = form.fields.get(name)
        if field is None:
            continue
        classes = field.widget.attrs.get("class", "")
        if "panel-control" not in classes.split():
            field.widget.attrs["class"] = f"{classes} panel-control".strip()


def _apply_photo_update(form, instance):
    uploaded = form.files.get(form.add_prefix("photo")) if form.is_bound else None
    if uploaded:
        instance.filename = ""
        return
    if form.cleaned_data.get("clear_photo"):
        if instance.photo:
            instance.photo.delete(save=False)
        instance.photo = ""
        instance.filename = ""


class ShoePanelForm(forms.ModelForm):
    clear_photo = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "visually-hidden"}))

    class Meta:
        model = Shoe
        fields = ("family_name", "model_name", "available", "photo")
        labels = {
            "family_name": "Naziv na kartici",
            "model_name": "Puno ime modela",
            "available": "Prikazana u anketi",
            "photo": "Slika",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].required = False
        self.fields["photo"].widget = _photo_widget()
        _style_controls(self, "family_name", "model_name")

    def save(self, commit=True):
        shoe = super().save(commit=False)
        _apply_photo_update(self, shoe)
        if commit:
            shoe.save()
            self.save_m2m()
        return shoe


class VariantPanelForm(forms.ModelForm):
    clear_photo = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "visually-hidden"}))

    class Meta:
        model = Variant
        fields = ("position", "gender", "color", "sku", "store_url", "photo")
        labels = {
            "position": "Redosled",
            "gender": "Pol",
            "color": "Boja",
            "sku": "Šifra",
            "store_url": "Link ka proizvodu",
            "photo": "Slika",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        existing = bool(self.instance.pk)
        allowed = [choice[0] for choice in COLOR_CHOICES]
        current = (self.instance.color or "") if existing else ""
        color_choices = list(COLOR_CHOICES)
        if current and current not in allowed:
            color_choices.append((current, current))

        self.fields["photo"].widget = _photo_widget()
        self.fields["color"].widget = forms.Select(choices=[("", "—")] + color_choices)
        self.fields["gender"].widget = forms.Select(choices=[("", "—")] + list(Variant.Gender.choices))
        self.fields["gender"].choices = [("", "—")] + list(Variant.Gender.choices)
        self.fields["store_url"].widget.attrs.setdefault("placeholder", "https://")
        self.fields["position"].widget.attrs.setdefault("min", "1")
        self.fields["position"].widget.attrs.setdefault("inputmode", "numeric")
        _style_controls(self, "position", "gender", "color", "sku", "store_url")

        # Empty / new rows must not block save or delete of other variants.
        for name in ("position", "gender", "color", "sku", "store_url", "photo"):
            self.fields[name].required = False
        if not existing:
            self.fields["position"].initial = ""

    def save(self, commit=True):
        variant = super().save(commit=False)
        _apply_photo_update(self, variant)
        if commit:
            variant.save()
            self.save_m2m()
        return variant

    def clean_color(self):
        color = (self.cleaned_data.get("color") or "").strip()
        if not color:
            return ""
        allowed = {choice[0] for choice in COLOR_CHOICES}
        current = (self.instance.color or "") if self.instance.pk else ""
        if current:
            allowed.add(current)
        if color not in allowed:
            raise forms.ValidationError("Izaberi boju iz liste.")
        return color

    def clean_sku(self):
        return (self.cleaned_data.get("sku") or "").strip()

    def clean(self):
        cleaned = super().clean()
        if self.cleaned_data.get("DELETE"):
            return cleaned

        gender = cleaned.get("gender") or ""
        color = cleaned.get("color") or ""
        sku = cleaned.get("sku") or ""
        store_url = cleaned.get("store_url") or ""
        position = cleaned.get("position")
        photo = cleaned.get("photo")
        touched = any([gender, color, sku, store_url, photo, position not in (None, "")])

        if not touched and not self.instance.pk:
            return cleaned

        for field in ("gender", "color", "sku", "store_url"):
            if not cleaned.get(field):
                self.add_error(field, "Obavezno za varijantu.")
        if position in (None, ""):
            cleaned["position"] = 1
        return cleaned


class VariantPanelFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        seen = set()
        kept = 0
        for form in self.forms:
            cleaned = getattr(form, "cleaned_data", None) or {}
            if not cleaned or cleaned.get("DELETE"):
                continue
            sku = (cleaned.get("sku") or "").strip()
            gender = cleaned.get("gender") or ""
            color = cleaned.get("color") or ""
            store_url = cleaned.get("store_url") or ""
            if not any([sku, gender, color, store_url]) and not form.instance.pk:
                continue
            kept += 1
            if not sku:
                continue
            key = sku.casefold()
            if key in seen:
                form.add_error("sku", "Ova šifra je već uneta.")
            seen.add(key)
        if kept < 1:
            raise forms.ValidationError("Patika mora imati bar jednu varijantu.")


VariantFormSet = inlineformset_factory(
    Shoe,
    Variant,
    form=VariantPanelForm,
    formset=VariantPanelFormSet,
    extra=0,
    max_num=VARIANT_MAX,
    validate_max=True,
    min_num=1,
    validate_min=False,
    can_delete=True,
)


class PlacementForm(forms.Form):
    def __init__(self, *args, paths=None, selected=None, **kwargs):
        super().__init__(*args, **kwargs)
        selected = selected or {}
        for path in paths or []:
            name = "place_" + path.pk.replace("/", "_")
            field = forms.ChoiceField(
                label=path.label,
                required=False,
                choices=(
                    ("", "Ne prikazuj"),
                    ("main", "Glavni predlog"),
                    ("extra", "Dodatni model"),
                ),
                initial=selected.get(path.pk, ""),
                widget=forms.Select(attrs={"class": "panel-control"}),
            )
            field.path = path
            self.fields[name] = field


class EditorCreateForm(forms.Form):
    username = forms.CharField(label="Korisničko ime", max_length=150)
    first_name = forms.CharField(label="Ime", max_length=150, required=False)
    password = forms.CharField(label="Lozinka", widget=forms.PasswordInput, min_length=8)
    markets = forms.ModelMultipleChoiceField(
        label="Tržišta",
        queryset=Market.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        help_text="Urednik vidi i menja samo označena tržišta. Nema pristup /admin/.",
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not username:
            raise forms.ValidationError("Upiši korisničko ime.")
        if get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError("Ovo korisničko ime je zauzeto.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean_markets(self):
        markets = self.cleaned_data["markets"]
        if not markets:
            raise forms.ValidationError("Izaberi bar jedno tržište.")
        return markets


class EditorMarketsForm(forms.Form):
    markets = forms.ModelMultipleChoiceField(
        label="Tržišta",
        queryset=Market.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )

    def clean_markets(self):
        markets = self.cleaned_data["markets"]
        if not markets:
            raise forms.ValidationError("Izaberi bar jedno tržište.")
        return markets
