from urllib.parse import urlsplit

from django.test import TestCase, override_settings

SIREN_ACCEPT = "application/vnd.siren+json"


class BrowserTests(TestCase):
    def test_serves_the_siren_browser_from_the_index(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        page = response.content.decode()
        self.assertRegex(
            page, r'href="/static/browser/browser(?:\.[0-9a-f]{12})?\.css"')
        self.assertRegex(
            page, r'src="/static/browser/browser(?:\.[0-9a-f]{12})?\.js"')
        self.assertIn('data-siren-root="/siren/"', page)

    @override_settings(SIRENITY_ROOT="/example-siren/")
    def test_exposes_the_configured_siren_root(self) -> None:
        response = self.client.get("/")

        self.assertContains(response, 'data-siren-root="/example-siren/"')

    def test_local_siren_adapter_supports_the_browser_navigation_smoke_path(self) -> None:
        category = self.client.post(
            "/api/records/categories",
            data={"title": "Browser smoke category",
                  "content_schema": {"type": "object"}},
            content_type="application/json",
        ).json()
        tag = self.client.post(
            "/api/records/tags",
            data={"name": "browser-smoke"},
            content_type="application/json",
        ).json()
        record = self.client.post(
            "/api/records",
            data={
                "title": "Browser smoke record",
                "content": {},
                "category_id": category["id"],
                "tag_ids": [tag["id"]],
                "resources": [],
            },
            content_type="application/json",
        ).json()

        root = self.client.get(
            "/siren/", headers={"accept": SIREN_ACCEPT}).json()
        collection_link = next(
            link
            for link in root["links"]
            if link["rel"] == ["collection"] and urlsplit(link["href"]).path == "/siren/records"
        )
        collection = self.client.get(
            urlsplit(collection_link["href"]).path,
            headers={"accept": SIREN_ACCEPT},
        ).json()
        item = next(
            entity for entity in collection["entities"] if entity["properties"]["id"] == record["id"])
        self_link = next(
            link for link in item["links"] if link["rel"] == ["self"])
        entity = self.client.get(
            urlsplit(self_link["href"]).path,
            headers={"accept": SIREN_ACCEPT},
        ).json()

        self.assertEqual(entity["class"], ["record"])
        self.assertEqual(entity["properties"]["title"], "Browser smoke record")
        self.assertGreaterEqual(
            {action["name"] for action in entity["actions"]},
            {"update_record", "delete_record"},
        )
