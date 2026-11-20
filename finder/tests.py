import mimetypes
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase


class MarketRoutingTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_default_entry_opens_serbia(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/rs/", fetch_redirect_response=False)

    def test_accept_language_hr_opens_croatia(self):
        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="hr-HR,hr;q=0.9,en;q=0.8")
        self.assertRedirects(response, "/hr/", fetch_redirect_response=False)

    def test_accept_language_sl_opens_slovenia(self):
        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="sl-SI,sl;q=0.9")
        self.assertRedirects(response, "/si/", fetch_redirect_response=False)

    def test_cloudflare_country_header(self):
        response = self.client.get("/", HTTP_CF_IPCOUNTRY="SI")
        self.assertRedirects(response, "/si/", fetch_redirect_response=False)

    def test_query_overrides_cookie(self):
        self.client.get("/hr/")
        response = self.client.get("/?market=rs")
        self.assertRedirects(response, "/rs/", fetch_redirect_response=False)

    def test_old_lang_query(self):
        response = self.client.get("/?lang=sl")
        self.assertRedirects(response, "/si/", fetch_redirect_response=False)

    def test_cookie_keeps_market(self):
        self.client.get("/hr/")
        response = self.client.get("/")
        self.assertRedirects(response, "/hr/", fetch_redirect_response=False)

    def test_unknown_market_is_not_found(self):
        response = self.client.get("/de/")
        self.assertEqual(response.status_code, 404)

    def test_pages_keep_analytics_and_translation(self):
        serbia = self.client.get("/rs/")
        croatia = self.client.get("/hr/")
        slovenia = self.client.get("/si/")
        for response in (serbia, croatia, slovenia):
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "G-NYDZMQX8C8")
            self.assertNotContains(response, "G-G04L3G3962")
            self.assertContains(response, '"gaIds": []')
            self.assertContains(response, "METASPEED SKY TOKYO")
        self.assertContains(serbia, "PRONAĐI SVOJU PATIKU")
        self.assertContains(croatia, "PRONAĐI SVOJE TENISICE")
        self.assertContains(slovenia, "NAJDI SVOJE COPATE")
        self.assertContains(serbia, "patike")
        self.assertContains(croatia, "tenisice")
        self.assertContains(slovenia, "copate")
        self.assertContains(serbia, 'lang="sr-Latn"')
        self.assertContains(croatia, 'lang="hr"')
        self.assertContains(slovenia, 'lang="sl"')

    def test_image_and_font_mime_types(self):
        self.assertEqual(mimetypes.guess_type("patika.webp")[0], "image/webp")
        self.assertEqual(mimetypes.guess_type("ASICSFont.otf")[0], "font/otf")

    def test_quiz_script_keeps_analytics_contract(self):
        script = Path(settings.BASE_DIR, "static", "app.js").read_text(encoding="utf-8")
        self.assertIn("a_opis", script)
        self.assertIn("function track(", script)
        self.assertNotIn("G-NYDZMQX8C8", script)
        self.assertNotIn("G-G04L3G3962", script)
        self.assertIn("korak_", script)
        self.assertIn("rezultat_", script)
        from finder.analytics import EVENT_PARAMETERS

        for item in EVENT_PARAMETERS:
            self.assertIn(item["name"], script)
        self.assertIn("a_drzava:String(finderConfig.market", script)
        self.assertIn("user_properties", script)
        self.assertIn("drzava:", script)


class CatalogAdminTests(TestCase):
    def test_recommendation_stays_on_its_market(self):
        from finder.models import Market, Recommendation, RecommendationItem, Shoe, Variant

        croatia_market = Market.objects.get(pk="hr")
        shoe = Shoe.objects.create(
            market=croatia_market,
            family_name="TEST PATIKA",
            model_name="TEST PATIKA 1",
            key="test-patika",
        )
        Variant.objects.create(
            shoe=shoe,
            sku="TEST-1",
            gender="unisex",
            color="Plava",
            store_url="https://www.sportvision.hr/test-patika",
        )
        recommendation = Recommendation.objects.get(market=croatia_market, path_id="road/comfort/soft")
        RecommendationItem.objects.create(recommendation=recommendation, shoe=shoe, placement="main", position=9)

        croatia = self.client.get("/hr/")
        serbia = self.client.get("/rs/")
        self.assertContains(croatia, "TEST PATIKA")
        self.assertNotContains(serbia, "TEST PATIKA")
        self.assertContains(croatia, "gel-nimbus")
        self.assertContains(serbia, "gel-nimbus")

    def test_admin_lists_markets_and_answer_paths(self):
        from django.contrib.auth import get_user_model

        editor = get_user_model().objects.create_superuser("editor", "editor@example.com", "pass-word-123")
        self.client.force_login(editor)
        response = self.client.get("/admin/finder/recommendation/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Asfalt → Udobnost → Mekan korak")
        self.assertContains(response, "Hrvatska")
        self.assertContains(response, "Srbija")
        self.assertContains(response, "Slovenija")
        self.assertContains(response, "GEL-NIMBUS™")

    def test_admin_form_adds_shoe_for_one_market(self):
        from django.contrib.auth import get_user_model

        from finder.models import Recommendation, Shoe

        editor = get_user_model().objects.create_superuser("clerk", "clerk@example.com", "pass-word-123")
        self.client.force_login(editor)
        created = self.client.post(
            "/admin/finder/shoe/add/",
            {
                "market": "hr",
                "family_name": "TEST PATIKA",
                "model_name": "TEST PATIKA 1",
                "key": "test-patika-admin",
                "available": "on",
                "filename": "",
                "variants-TOTAL_FORMS": "1",
                "variants-INITIAL_FORMS": "0",
                "variants-MIN_NUM_FORMS": "0",
                "variants-MAX_NUM_FORMS": "1000",
                "variants-0-position": "1",
                "variants-0-gender": "unisex",
                "variants-0-color": "Plava",
                "variants-0-sku": "ADMIN-1",
                "variants-0-filename": "",
                "variants-0-store_url": "https://www.sportvision.hr/admin-test",
                "variants-0-available_size_count": "1",
                "variants-0-id": "",
                "variants-0-shoe": "",
            },
        )
        self.assertEqual(created.status_code, 302, created.content.decode()[:1500])
        shoe = Shoe.objects.get(market_id="hr", key="test-patika-admin")
        recommendation = Recommendation.objects.get(market_id="hr", path_id="road/comfort/soft")
        items = list(recommendation.items.order_by("placement", "position", "id"))
        data = {
            "market": "hr",
            "path": "road/comfort/soft",
            "items-TOTAL_FORMS": str(len(items) + 1),
            "items-INITIAL_FORMS": str(len(items)),
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
        }
        for index, item in enumerate(items):
            data[f"items-{index}-id"] = str(item.pk)
            data[f"items-{index}-recommendation"] = str(recommendation.pk)
            data[f"items-{index}-position"] = str(item.position)
            data[f"items-{index}-placement"] = item.placement
            data[f"items-{index}-shoe"] = str(item.shoe_id)
        data[f"items-{len(items)}-id"] = ""
        data[f"items-{len(items)}-recommendation"] = str(recommendation.pk)
        data[f"items-{len(items)}-position"] = "9"
        data[f"items-{len(items)}-placement"] = "main"
        data[f"items-{len(items)}-shoe"] = str(shoe.pk)
        updated = self.client.post(f"/admin/finder/recommendation/{recommendation.pk}/change/", data)
        self.assertEqual(updated.status_code, 302, updated.content.decode()[:1500])

        croatia = self.client.get("/hr/")
        serbia = self.client.get("/rs/")
        self.assertContains(croatia, "TEST PATIKA")
        self.assertNotContains(serbia, "TEST PATIKA")

        self.assertTrue(shoe.analytics_code)
        self.assertLessEqual(len(shoe.analytics_code), 6)
        self.assertContains(croatia, shoe.analytics_code)
        stats = self.client.get("/admin/statistika/")
        self.assertEqual(stats.status_code, 200)
        self.assertContains(stats, "a_drzava")
        self.assertContains(stats, "a_sifra")
        self.assertContains(stats, "Srbija")
        self.assertContains(stats, "Hrvatska")
        self.assertContains(stats, "Slovenija")
        self.assertContains(stats, "nimbus")

        removed = self.client.post(f"/admin/finder/shoe/{shoe.pk}/delete/", {"post": "yes"})
        self.assertEqual(removed.status_code, 302)
        self.assertNotContains(self.client.get("/hr/"), "TEST PATIKA")


class SitePanelTests(TestCase):
    def editor(self, username="ana", markets=None):
        from django.contrib.auth.models import Group
        from django.contrib.auth import get_user_model

        from finder.models import EditorProfile, Market

        user = get_user_model().objects.create_user(username, password="lozinka-ana-123")
        user.is_staff = False
        user.save(update_fields=["is_staff"])
        group, _created = Group.objects.get_or_create(name="urednici")
        user.groups.add(group)
        profile = EditorProfile.objects.create(user=user)
        profile.markets.set(markets or Market.objects.all())
        return user

    def test_quiz_links_to_the_panel(self):
        response = self.client.get("/rs/")
        self.assertContains(response, 'href="/panel/"')

    def test_anonymous_is_sent_to_login(self):
        response = self.client.get("/panel/")
        self.assertRedirects(response, "/panel/prijava/?next=/panel/")

    def test_same_login_accepts_owner_and_rejects_stranger(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser("vlasnik", "vlasnik@example.com", "lozinka-vlasnik-123")
        get_user_model().objects.create_user("gost", password="lozinka-gost-123")
        owner = self.client.post("/panel/prijava/", {"username": "vlasnik", "password": "lozinka-vlasnik-123"})
        self.assertRedirects(owner, "/panel/")
        self.client.logout()
        stranger = self.client.post("/panel/prijava/", {"username": "gost", "password": "lozinka-gost-123"})
        self.assertEqual(stranger.status_code, 200)
        self.assertContains(stranger, "nema pristup")
        self.assertRedirects(self.client.get("/panel/"), "/panel/prijava/?next=/panel/")

    def _shoe_post_data(self, shoe, *, family_name=None, variants=None, deleted=None, extra=None):
        from finder.models import AnswerPath, RecommendationItem

        variants = list(variants if variants is not None else shoe.variants.order_by("position", "id"))
        deleted = {item.pk for item in (deleted or [])}
        data = {
            "family_name": family_name or shoe.family_name,
            "model_name": shoe.model_name,
            "variants-TOTAL_FORMS": str(len(variants) + len(extra or [])),
            "variants-INITIAL_FORMS": str(len(variants)),
            "variants-MIN_NUM_FORMS": "1",
            "variants-MAX_NUM_FORMS": "10",
        }
        if shoe.available:
            data["available"] = "on"
        for index, variant in enumerate(variants):
            data[f"variants-{index}-id"] = str(variant.pk)
            data[f"variants-{index}-shoe"] = str(shoe.pk)
            data[f"variants-{index}-position"] = str(variant.position)
            data[f"variants-{index}-gender"] = variant.gender
            data[f"variants-{index}-color"] = variant.color
            data[f"variants-{index}-sku"] = variant.sku
            data[f"variants-{index}-store_url"] = variant.store_url
            if variant.pk in deleted:
                data[f"variants-{index}-DELETE"] = "on"
        for offset, row in enumerate(extra or []):
            index = len(variants) + offset
            data[f"variants-{index}-id"] = ""
            data[f"variants-{index}-shoe"] = str(shoe.pk) if shoe.pk else ""
            data[f"variants-{index}-position"] = str(row.get("position", index + 1))
            data[f"variants-{index}-gender"] = row["gender"]
            data[f"variants-{index}-color"] = row["color"]
            data[f"variants-{index}-sku"] = row["sku"]
            data[f"variants-{index}-store_url"] = row["store_url"]
        for path in AnswerPath.objects.all():
            item = RecommendationItem.objects.filter(shoe=shoe, recommendation__path=path).first()
            data["place_" + path.pk.replace("/", "_")] = item.placement if item else ""
        return data

    def test_editor_renames_a_shoe_on_one_market(self):
        from finder.models import Shoe

        self.editor()
        self.client.login(username="ana", password="lozinka-ana-123")
        shoe = Shoe.objects.get(market_id="hr", key="gel-nimbus")
        updated = self.client.post(f"/panel/hr/{shoe.pk}/", self._shoe_post_data(shoe, family_name="TEST NIMBUS"))
        self.assertEqual(updated.status_code, 302, updated.content.decode()[:2000])
        croatia = self.client.get("/hr/")
        serbia = self.client.get("/rs/")
        self.assertContains(croatia, "TEST NIMBUS")
        self.assertNotContains(serbia, "TEST NIMBUS")
        self.assertEqual(Shoe.objects.get(pk=shoe.pk).key, "gel-nimbus")

    def test_editor_adds_and_deletes_variants_without_blank_row(self):
        from finder.models import Shoe, Variant

        self.editor()
        self.client.login(username="ana", password="lozinka-ana-123")
        shoe = Shoe.objects.get(market_id="hr", key="gel-nimbus")
        before = list(shoe.variants.order_by("position", "id"))
        self.assertGreaterEqual(len(before), 2)

        page = self.client.get(f"/panel/hr/{shoe.pk}/")
        self.assertContains(page, "Dodaj varijantu")
        self.assertContains(page, "panel-variants.js")
        # No automatic empty extra row on edit.
        self.assertEqual(page.context["variant_formset"].total_form_count(), len(before))

        added = self.client.post(
            f"/panel/hr/{shoe.pk}/",
            self._shoe_post_data(
                shoe,
                variants=before,
                extra=[
                    {
                        "position": len(before) + 1,
                        "gender": "unisex",
                        "color": "Zelena",
                        "sku": "PANEL-ADD-1",
                        "store_url": "https://www.sportvision.hr/panel-add-1",
                    }
                ],
            ),
        )
        self.assertEqual(added.status_code, 302, added.content.decode()[:2000])
        shoe.refresh_from_db()
        self.assertTrue(shoe.variants.filter(sku="PANEL-ADD-1").exists())
        self.assertEqual(shoe.variants.count(), len(before) + 1)

        current = list(shoe.variants.order_by("position", "id"))
        victim = next(item for item in current if item.sku == before[0].sku)
        deleted = self.client.post(
            f"/panel/hr/{shoe.pk}/",
            self._shoe_post_data(shoe, variants=current, deleted=[victim]),
        )
        self.assertEqual(deleted.status_code, 302, deleted.content.decode()[:2000])
        self.assertFalse(Variant.objects.filter(pk=victim.pk).exists())
        self.assertTrue(shoe.variants.filter(sku="PANEL-ADD-1").exists())

        only = list(shoe.variants.order_by("position", "id"))
        blocked = self.client.post(
            f"/panel/hr/{shoe.pk}/",
            self._shoe_post_data(shoe, variants=only, deleted=only),
        )
        self.assertEqual(blocked.status_code, 200)
        self.assertContains(blocked, "bar jednu varijantu")
        self.assertEqual(shoe.variants.count(), len(only))

    def test_editor_adds_a_shoe_and_owner_opens_accounts(self):
        from django.contrib.auth import get_user_model

        from finder.models import Shoe

        self.editor()
        self.client.login(username="ana", password="lozinka-ana-123")
        created = self.client.post(
            "/panel/si/nova/",
            {
                "family_name": "PANEL PATIKA",
                "model_name": "PANEL PATIKA 1",
                "available": "on",
                "variants-TOTAL_FORMS": "1",
                "variants-INITIAL_FORMS": "0",
                "variants-MIN_NUM_FORMS": "0",
                "variants-MAX_NUM_FORMS": "1000",
                "variants-0-id": "",
                "variants-0-shoe": "",
                "variants-0-position": "1",
                "variants-0-gender": "women",
                "variants-0-color": "Plava",
                "variants-0-sku": "PANEL-9",
                "variants-0-store_url": "https://www.sportvision.si/panel-patika",
                "place_road_comfort_soft": "main",
            },
        )
        shoe = Shoe.objects.get(market_id="si", family_name="PANEL PATIKA")
        self.assertRedirects(created, f"/panel/si/{shoe.pk}/")
        self.assertContains(self.client.get("/si/"), "PANEL PATIKA")
        self.assertNotContains(self.client.get("/hr/"), "PANEL PATIKA")
        self.assertEqual(self.client.get("/panel/nalozi/").status_code, 403)

        owner = get_user_model().objects.create_superuser("vlasnik", "vlasnik@example.com", "lozinka-vlasnik-123")
        self.client.force_login(owner)
        opened = self.client.post(
            "/panel/nalozi/",
            {
                "username": "marko",
                "first_name": "Marko",
                "password": "lozinka-marko-123",
                "markets": ["si"],
            },
        )
        self.assertRedirects(opened, "/panel/nalozi/")
        marko = get_user_model().objects.get(username="marko")
        self.assertFalse(marko.is_superuser)
        self.assertFalse(marko.is_staff)
        self.assertTrue(marko.groups.filter(name="urednici").exists())
        self.assertEqual(list(marko.editor_profile.markets.values_list("code", flat=True)), ["si"])
        self.client.logout()
        self.client.login(username="marko", password="lozinka-marko-123")
        self.assertEqual(self.client.get("/panel/si/").status_code, 200)
        self.assertEqual(self.client.get("/panel/hr/").status_code, 403)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_editor_photo_reaches_quiz_on_one_market(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from finder.catalog import public_catalog
        from finder.models import Shoe

        self.editor("foto")
        self.client.login(username="foto", password="lozinka-ana-123")
        buf = io.BytesIO()
        Image.new("RGB", (24, 24), (1, 2, 3)).save(buf, format="PNG")
        photo = SimpleUploadedFile("release.png", buf.getvalue(), content_type="image/png")
        created = self.client.post(
            "/panel/rs/nova/",
            {
                "family_name": "FOTO PATIKA",
                "model_name": "FOTO PATIKA 1",
                "available": "on",
                "photo": photo,
                "variants-TOTAL_FORMS": "1",
                "variants-INITIAL_FORMS": "0",
                "variants-MIN_NUM_FORMS": "1",
                "variants-MAX_NUM_FORMS": "10",
                "variants-0-id": "",
                "variants-0-shoe": "",
                "variants-0-position": "1",
                "variants-0-gender": "men",
                "variants-0-color": "Crna",
                "variants-0-sku": "FOTO-1",
                "variants-0-store_url": "https://www.sportvision.rs/foto-patika",
                "place_road_comfort_soft": "main",
            },
        )
        shoe = Shoe.objects.get(market_id="rs", family_name="FOTO PATIKA")
        self.assertEqual(created.status_code, 302, created.content.decode()[:1000])
        self.assertTrue(shoe.photo)
        catalog = public_catalog("rs")
        product = next(item for item in catalog["products"] if item["key"] == shoe.key)
        self.assertTrue(product["image_src"].startswith("/media/"))
        self.assertIn(shoe.key, catalog["recommendations"]["road/comfort/soft"]["shoes"])
        self.assertContains(self.client.get("/rs/"), "FOTO PATIKA")
        self.assertNotContains(self.client.get("/hr/"), "FOTO PATIKA")
        self.assertNotContains(self.client.get("/si/"), "FOTO PATIKA")

        page = self.client.get(f"/panel/rs/{shoe.pk}/")
        self.assertContains(page, "data-photo-drop")
        self.assertContains(page, "Klikni ili prevuci sliku")
        self.assertContains(page, "panel-photos.js")

        cleared = self.client.post(
            f"/panel/rs/{shoe.pk}/",
            self._shoe_post_data(shoe) | {"clear_photo": "on"},
        )
        self.assertEqual(cleared.status_code, 302, cleared.content.decode()[:1000])
        shoe.refresh_from_db()
        self.assertFalse(bool(shoe.photo))
        self.assertEqual(shoe.filename, "")

    def test_quiz_uses_server_recommendations_without_hardcoded_trail_extra(self):
        script = Path(settings.BASE_DIR, "static", "app.js").read_text(encoding="utf-8")
        self.assertIn("Object.prototype.hasOwnProperty.call(finderConfig,'recommendations')", script)
        self.assertIn("if(server){const spec=server[path]||{};return {shoes:spec.shoes||[],extras:spec.extras||[]};}", script)
        croatia = self.client.get("/hr/")
        config = croatia.context["config"]["recommendations"]
        self.assertIn("trail/protection/technical", config)
        # Server config is authoritative: missing path must not invent blazeblast in JS when recommendations exist.
        self.assertIsInstance(config, dict)


class SyncCatalogGuardTests(TestCase):
    def test_default_sync_keeps_panel_edits_and_replace_is_idempotent(self):
        from finder.catalog import public_catalog
        from finder.models import Recommendation, RecommendationItem, Shoe, Variant
        from finder.store_sync import sync_market_from_links

        first = sync_market_from_links("si", scrape=False, download_missing_images=False, replace_catalog=True)
        self.assertTrue(first["catalog_replaced"])
        training = public_catalog("si")["recommendations"]["road/speed/training"]["shoes"]
        self.assertEqual(training[0], "megablast")
        shoe_count = Shoe.objects.filter(market_id="si").count()

        second = sync_market_from_links("si", scrape=False, download_missing_images=False, replace_catalog=True)
        self.assertTrue(second["catalog_replaced"])
        self.assertEqual(Shoe.objects.filter(market_id="si").count(), shoe_count)
        self.assertEqual(
            public_catalog("si")["recommendations"]["road/speed/training"]["shoes"][0],
            "megablast",
        )

        self.editor = self._editor()
        self.client.login(username="cuvar", password="lozinka-ana-123")
        created = self.client.post(
            "/panel/si/nova/",
            {
                "family_name": "SYNC SAFE",
                "model_name": "SYNC SAFE 1",
                "available": "on",
                "variants-TOTAL_FORMS": "1",
                "variants-INITIAL_FORMS": "0",
                "variants-MIN_NUM_FORMS": "0",
                "variants-MAX_NUM_FORMS": "1000",
                "variants-0-id": "",
                "variants-0-shoe": "",
                "variants-0-position": "1",
                "variants-0-gender": "unisex",
                "variants-0-color": "Zelena",
                "variants-0-sku": "SAFE-1",
                "variants-0-store_url": "https://www.sportvision.si/sync-safe",
                "place_road_comfort_soft": "main",
            },
        )
        custom = Shoe.objects.get(market_id="si", family_name="SYNC SAFE")
        self.assertEqual(created.status_code, 302, created.content.decode()[:1000])

        nimbus = Shoe.objects.get(market_id="si", key="gel-nimbus")
        variant = nimbus.variants.order_by("position", "id").first()
        original_url = variant.store_url
        variant.store_url = "https://www.sportvision.si/manual-nimbus"
        variant.color = "Crna"
        variant.save(update_fields=["store_url", "color"])

        soft = Recommendation.objects.get(market_id="si", path_id="road/comfort/soft")
        RecommendationItem.objects.filter(recommendation=soft, shoe=nimbus).delete()

        guarded = sync_market_from_links("si", scrape=False, download_missing_images=False, replace_catalog=False)
        self.assertFalse(guarded["catalog_replaced"])

        custom.refresh_from_db()
        variant.refresh_from_db()
        soft_keys = public_catalog("si")["recommendations"]["road/comfort/soft"]["shoes"]
        self.assertTrue(custom.available)
        self.assertEqual(custom.variants.get().sku, "SAFE-1")
        self.assertEqual(variant.store_url, "https://www.sportvision.si/manual-nimbus")
        self.assertEqual(variant.color, "Crna")
        self.assertIn(custom.key, soft_keys)
        self.assertNotIn("gel-nimbus", soft_keys)
        self.assertContains(self.client.get("/si/"), "SYNC SAFE")
        self.assertNotEqual(variant.store_url, original_url)
        self.assertEqual(Variant.objects.filter(shoe=nimbus, sku=variant.sku).count(), 1)

    def _editor(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group

        from finder.models import EditorProfile, Market

        user = get_user_model().objects.create_user("cuvar", password="lozinka-ana-123")
        group, _created = Group.objects.get_or_create(name="urednici")
        user.groups.add(group)
        profile = EditorProfile.objects.create(user=user)
        profile.markets.set(Market.objects.all())
        return user


class PanelExcelTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group

        from finder.models import EditorProfile, Market

        self.user = get_user_model().objects.create_user("excel", password="lozinka-ana-123")
        group, _created = Group.objects.get_or_create(name="urednici")
        self.user.groups.add(group)
        profile = EditorProfile.objects.create(user=self.user)
        profile.markets.set(Market.objects.all())
        self.client.login(username="excel", password="lozinka-ana-123")

    def test_export_reimport_is_noop_and_wrong_market_rejected(self):
        from finder.models import Market, Shoe, Variant
        from finder.panel_excel import apply_preview, build_preview, export_workbook

        market = Market.objects.get(pk="si")
        payload = export_workbook(market)
        preview = build_preview(market, payload)
        self.assertTrue(preview.ok, preview.errors)
        self.assertEqual(preview.change_count, 0)
        before = Shoe.objects.filter(market=market).count()
        apply_preview(market, preview)
        self.assertEqual(Shoe.objects.filter(market=market).count(), before)

        hr = Market.objects.get(pk="hr")
        foreign = build_preview(hr, payload)
        self.assertFalse(foreign.ok)
        self.assertTrue(any("ne pripada" in error.message for error in foreign.errors))

    def test_excel_add_change_disable_and_keeps_photo(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from openpyxl import Workbook, load_workbook
        from PIL import Image

        from finder.catalog import public_catalog
        from finder.models import Market, RecommendationItem, Shoe, Variant
        from finder.panel_excel import SHEET_PLACES, SHEET_SHOES, SHEET_VARIANTS, apply_preview, build_preview, export_workbook

        market = Market.objects.get(pk="rs")
        nimbus = Shoe.objects.get(market=market, key="gel-nimbus")
        buf = io.BytesIO()
        Image.new("RGB", (12, 12), (9, 8, 7)).save(buf, format="PNG")
        nimbus.photo.save("keep-nimbus.png", SimpleUploadedFile("keep-nimbus.png", buf.getvalue(), "image/png"), save=True)
        photo_name = nimbus.photo.name
        variant = nimbus.variants.order_by("position", "id").first()

        exported = export_workbook(market)
        wb = load_workbook(io.BytesIO(exported))
        shoes = wb[SHEET_SHOES]
        variants = wb[SHEET_VARIANTS]
        places = wb[SHEET_PLACES]

        shoes.append(["", "NOVO-1", "EXCEL PATIKA", "EXCEL PATIKA 1", "da"])
        for row in shoes.iter_rows(min_row=2, values_only=False):
            if row[0].value == nimbus.pk:
                row[4].value = "ne"
                break
        variants.append(["", "", "NOVO-1", 1, "unisex", "Crna", "EXCEL-1", "https://www.sportvision.rs/excel-1"])
        for row in variants.iter_rows(min_row=2, values_only=False):
            if row[0].value == variant.pk:
                row[6].value = "NIMBUS-EDIT"
                row[7].value = "https://www.sportvision.rs/nimbus-edit"
                break
        places.append(["", "NOVO-1", "road/comfort/soft", "glavni"])
        for row in places.iter_rows(min_row=2, values_only=False):
            if row[0].value == nimbus.pk and row[2].value == "road/comfort/soft":
                row[3].value = "ukloni"
                break

        out = io.BytesIO()
        wb.save(out)
        preview = build_preview(market, out.getvalue())
        self.assertTrue(preview.ok, [(e.sheet, e.row, e.column, e.message) for e in preview.errors])
        self.assertGreater(preview.change_count, 0)
        apply_preview(market, preview)

        nimbus.refresh_from_db()
        variant.refresh_from_db()
        custom = Shoe.objects.get(market=market, family_name="EXCEL PATIKA")
        self.assertFalse(nimbus.available)
        self.assertEqual(nimbus.photo.name, photo_name)
        self.assertEqual(variant.sku, "NIMBUS-EDIT")
        self.assertEqual(variant.store_url, "https://www.sportvision.rs/nimbus-edit")
        self.assertEqual(custom.variants.get().sku, "EXCEL-1")
        soft = public_catalog("rs")["recommendations"]["road/comfort/soft"]["shoes"]
        self.assertIn(custom.key, soft)
        self.assertNotIn("gel-nimbus", soft)
        self.assertContains(self.client.get("/rs/"), "EXCEL PATIKA")
        self.assertNotContains(self.client.get("/si/"), "EXCEL PATIKA")
        self.assertFalse(
            RecommendationItem.objects.filter(
                shoe=nimbus, recommendation__path_id="road/comfort/soft"
            ).exists()
        )

    def test_invalid_row_blocks_all_writes_and_guest_blocked(self):
        import io

        from openpyxl import load_workbook

        from finder.models import Market, Shoe
        from finder.panel_excel import SHEET_SHOES, build_preview, export_workbook

        market = Market.objects.get(pk="hr")
        before = list(Shoe.objects.filter(market=market).values_list("family_name", flat=True))
        wb = load_workbook(io.BytesIO(export_workbook(market)))
        wb[SHEET_SHOES].append(["", "NOVO-X", "LOSA", "LOSA 1", "možda"])
        buf = io.BytesIO()
        wb.save(buf)
        preview = build_preview(market, buf.getvalue())
        self.assertFalse(preview.ok)
        self.assertEqual(
            list(Shoe.objects.filter(market=market).values_list("family_name", flat=True)),
            before,
        )

        self.client.logout()
        denied = self.client.get("/panel/hr/uvoz/")
        self.assertRedirects(denied, "/panel/prijava/?next=/panel/hr/uvoz/")

    def test_cleared_recommendations_stay_empty_in_quiz(self):
        from finder.catalog import public_catalog
        from finder.models import Market, Recommendation, RecommendationItem

        market = Market.objects.get(pk="si")
        soft, _created = Recommendation.objects.get_or_create(
            market=market, path_id="road/comfort/soft"
        )
        RecommendationItem.objects.filter(recommendation=soft).delete()
        catalog = public_catalog("si")
        self.assertEqual(catalog["recommendations"]["road/comfort/soft"], {"shoes": [], "extras": []})
        page = self.client.get("/si/")
        self.assertEqual(page.context["config"]["recommendations"]["road/comfort/soft"]["shoes"], [])
        self.assertEqual(page.context["config"]["recommendations"]["road/comfort/soft"]["extras"], [])

    def test_list_search_and_export_buttons(self):
        page = self.client.get("/panel/rs/?q=nimbus")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "GEL-NIMBUS")
        self.assertContains(page, "Preuzmi katalog")
        self.assertContains(page, "Uvezi izmene")
        self.assertContains(page, "breadcrumbs")
        self.assertContains(page, "shoe-grid")
        self.assertNotContains(page, "AKTIVNO TRŽIŠTE")
        exported = self.client.get("/panel/rs/izvoz.xlsx")
        self.assertEqual(exported.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            exported["Content-Type"],
        )

    def test_list_filter_sort_and_pagination_query(self):
        page = self.client.get("/panel/rs/?status=on&sort=-name")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Primeni")
        self.assertTrue(page.context["page_obj"].paginator.count >= 1)
