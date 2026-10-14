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
            self.assertContains(response, "G-NYDZMQX8C8")
            self.assertContains(response, "G-G04L3G3962")
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
        self.assertIn("G-NYDZMQX8C8", script)
        self.assertIn("G-G04L3G3962", script)
        self.assertIn("korak_", script)
        self.assertIn("rezultat_", script)


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

        removed = self.client.post(f"/admin/finder/shoe/{shoe.pk}/delete/", {"post": "yes"})
        self.assertEqual(removed.status_code, 302)
        self.assertNotContains(self.client.get("/hr/"), "TEST PATIKA")
