import asyncio
import json
from hashlib import sha256

import pytest

from .test_runtime import ConfiguredApplication, PublicMcpClient


@pytest.mark.django_db(transaction=True)
def test_mcp_svg_attacks_recover_through_bounded_continuations_to_exact_rest_artifact() -> None:
    asyncio.run(verify_svg_download())


async def verify_svg_download() -> None:
    async with PublicMcpClient(ConfiguredApplication()).session() as (session, http):
        await session.initialize()
        catalogue = await session.list_tools()
        operation = next(tool for tool in catalogue.tools if tool.name == "download_diagram_svg")
        assert {"diagram_id", "expected_revision"} <= set(operation.input_schema["required"])
        missing = await session.call_tool(
            "download_diagram_svg", {"diagram_id": "example-missing", "expected_revision": 1}
        )
        assert missing.is_error is True
        group = await http.post("/api/diagram-sets", json={"title": "Example SVG", "description": "Example export"})
        assert group.status_code == 201
        created = await http.post(
            f"/api/diagram-sets/{group.json()['id']}/diagrams",
            json={"title": "Example flow", "kind": "flowchart"},
        )
        assert created.status_code == 201
        diagram = created.json()
        arguments = {"diagram_id": diagram["id"], "expected_revision": diagram["revision"]}
        draft = await session.call_tool("download_diagram_svg", arguments)
        assert draft.is_error is True
        assert "no source" in draft.content[0].text
        for operation_name, payload in (
            ("add_start", {"id": "example-start", "label": "Example start"}),
            ("add_end", {"id": "example-end", "label": "Example end"}),
            ("add_flow", {"id": "example-flow", "source_id": "example-start", "target_id": "example-end"}),
        ):
            changed = await http.post(
                f"/api/diagrams/{diagram['id']}/commands",
                json={"expected_revision": diagram["revision"], "operation": operation_name, "arguments": payload},
            )
            assert changed.status_code == 200
            diagram = changed.json()
        stale = await session.call_tool("download_diagram_svg", arguments)
        assert stale.is_error is True
        assert "changed" in stale.content[0].text
        arguments["expected_revision"] = diagram["revision"]
        invalid = await session.call_tool("download_diagram_svg", {**arguments, "offset": -1})
        assert invalid.is_error is True
        detail_url = f"/api/diagrams/{diagram['id']}"
        before = (await http.get(detail_url)).json()
        rest = await http.get(f"{detail_url}/svg", params={"expected_revision": diagram["revision"]})
        assert rest.status_code == 200
        artifact = rest.json()
        detail = await session.call_tool("get_diagram", {"diagram_id": diagram["id"]})
        export = next(
            item for item in detail.structured_content["follow_ups"] if item["operation_id"] == "download_diagram_svg"
        )
        assert export["arguments"]["expected_revision"] == diagram["revision"]
        page = await session.call_tool(export["operation_id"], export["arguments"])
        assert page.structured_content["status"] == "incomplete"
        assert page.structured_content["data"]["reason"] == "presentation_budget_exceeded"
        fragments: list[str] = []
        for _ in range(200):
            assert len(page.content[0].text.encode()) <= 16_384
            assert len(json.dumps(page.structured_content).encode()) <= 8_192
            body = page.structured_content
            if body["status"] == "ok":
                data = body["data"]
                assert data["content_revision"] == artifact["content_revision"]
                assert data["offset"] == len("".join(fragments))
                assert data["filename"] == artifact["filename"]
                fragments.append(data["content"])
                if not data["has_more"]:
                    assert body["follow_ups"] == []
                    break
            else:
                assert body["status"] == "incomplete"
                assert body["data"]["reason"] == "presentation_budget_exceeded"
            continuation = body["follow_ups"][0]
            assert continuation["operation_id"] == "download_diagram_svg"
            assert continuation["arguments"]["diagram_id"] == diagram["id"]
            assert continuation["arguments"]["expected_revision"] == diagram["revision"]
            page = await session.call_tool(continuation["operation_id"], continuation["arguments"])
        else:
            pytest.fail("SVG continuation did not terminate")
        content = "".join(fragments)
        assert content == artifact["content"]
        assert sha256(content.encode()).hexdigest() == artifact["content_revision"]
        assert (await http.get(detail_url)).json() == before
