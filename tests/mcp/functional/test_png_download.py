import asyncio
import json
from base64 import b64decode
from hashlib import sha256

import pytest

from .test_runtime import ConfiguredApplication, PublicMcpClient


@pytest.mark.django_db(transaction=True)
def test_mcp_png_attacks_recover_to_complete_image_matching_rest_artifact() -> None:
    asyncio.run(verify_png_download())


async def verify_png_download() -> None:
    async with PublicMcpClient(ConfiguredApplication()).session() as (session, http):
        await session.initialize()
        catalogue = await session.list_tools()
        assert "download_diagram_svg" not in {tool.name for tool in catalogue.tools}
        operation = next(tool for tool in catalogue.tools if tool.name == "download_diagram_png")
        assert {"diagram_id", "expected_revision"} <= set(operation.input_schema["required"])
        missing = await session.call_tool(
            "download_diagram_png", {"diagram_id": "example-missing", "expected_revision": 1}
        )
        assert missing.is_error is True
        group = await http.post("/api/diagram-sets", json={"title": "Example PNG", "description": "Example export"})
        assert group.status_code == 201
        created = await http.post(
            f"/api/diagram-sets/{group.json()['id']}/diagrams",
            json={"title": "Example flow", "kind": "flowchart"},
        )
        assert created.status_code == 201
        diagram = created.json()
        arguments = {"diagram_id": diagram["id"], "expected_revision": diagram["revision"]}
        draft = await session.call_tool("download_diagram_png", arguments)
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
        stale = await session.call_tool("download_diagram_png", arguments)
        assert stale.is_error is True
        assert "changed" in stale.content[0].text
        arguments["expected_revision"] = diagram["revision"]
        invalid = await session.call_tool("download_diagram_png", {**arguments, "offset": -1})
        assert invalid.is_error is True
        detail_url = f"/api/diagrams/{diagram['id']}"
        before = (await http.get(detail_url)).json()
        rest = await http.get(
            f"{detail_url}/png",
            params={"expected_revision": diagram["revision"]},
            headers={"Accept": "application/json"},
        )
        assert rest.status_code == 200
        artifact = rest.json()
        detail = await session.call_tool("get_diagram", {"diagram_id": diagram["id"]})
        export = next(
            item for item in detail.structured_content["follow_ups"] if item["operation_id"] == "download_diagram_png"
        )
        assert export["arguments"]["expected_revision"] == diagram["revision"]
        result = await session.call_tool(export["operation_id"], export["arguments"])
        assert result.is_error is False
        assert result.structured_content["status"] == "ok"
        assert result.structured_content["follow_ups"] == []
        assert len(result.content) == 2
        assert result.content[0].type == "text"
        assert len(result.content[0].text.encode()) <= 16_384
        assert len(json.dumps(result.structured_content).encode()) <= 8_192
        image = result.content[1]
        assert image.type == "image"
        assert image.mime_type == "image/png"
        content = b64decode(image.data, validate=True)
        assert content == b64decode(artifact["content"], validate=True)
        assert result.structured_content["data"] == {
            name: value for name, value in artifact.items() if name != "content"
        }
        assert sha256(content).hexdigest() == artifact["content_revision"]
        assert (await http.get(detail_url)).json() == before
