import argparse
import asyncio
import json
from base64 import b64decode
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from enclosure.security.services.actors import (
    Actor,
    ActorKind,
    AuthenticationMethod,
    DjangoSignedBearerIdentityProvider,
)


async def verify(base_url: str, diagram_id: str, output: Path) -> None:
    actor = Actor(
        id="runtime-png-verification",
        kind=ActorKind.SERVICE,
        authentication_method=AuthenticationMethod.BEARER,
        permissions=("security.invoke_read",),
        session_id=str(uuid4()),
    )
    token = DjangoSignedBearerIdentityProvider().issue(actor)
    async with httpx2.AsyncClient(base_url=base_url, timeout=120, headers={"Authorization": f"Bearer {token}"}) as http:
        detail_url = f"/api/diagrams/{diagram_id}"
        before = await http.get(detail_url, headers={"Accept": "application/json"})
        before.raise_for_status()
        diagram = before.json()
        revision = diagram["revision"]
        query = {"expected_revision": revision}
        binary = await http.get(f"{detail_url}/png", params=query, headers={"Accept": "image/png"})
        binary.raise_for_status()
        assert binary.headers["content-type"] == "image/png"
        assert "attachment" in binary.headers["content-disposition"]
        assert binary.content[:8] == b"\x89PNG\r\n\x1a\n"
        encoded = await http.get(f"{detail_url}/png", params=query, headers={"Accept": "application/json"})
        encoded.raise_for_status()
        artifact = encoded.json()
        assert binary.content == b64decode(artifact["content"], validate=True)
        assert sha256(binary.content).hexdigest() == artifact["content_revision"]
        assert artifact["total_bytes"] == len(binary.content)
        assert artifact["width"] == int.from_bytes(binary.content[16:20], "big")
        assert artifact["height"] == int.from_bytes(binary.content[20:24], "big")
        for response in (binary, encoded):
            assert "Accept" in response.headers["vary"]
        stale = await http.get(f"{detail_url}/png", params={"expected_revision": revision - 1})
        assert stale.status_code == 422
        assert (await http.get(f"{detail_url}/svg", params=query)).status_code == 404
        async with (
            streamable_http_client(f"{base_url}/mcp", http_client=http, terminate_on_close=False) as streams,
            ClientSession(*streams) as session,
        ):
            await session.initialize()
            catalogue = await session.list_tools()
            assert "download_diagram_svg" not in {tool.name for tool in catalogue.tools}
            result = await session.call_tool(
                "download_diagram_png", {"diagram_id": diagram_id, "expected_revision": revision}
            )
            assert result.is_error is False
            assert len(result.content) == 2
            assert result.content[1].type == "image"
            assert result.content[1].mime_type == "image/png"
            assert b64decode(result.content[1].data, validate=True) == binary.content
            assert len(json.dumps(result.structured_content).encode()) <= 8_192
        after = await http.get(detail_url, headers={"Accept": "application/json"})
        assert after.json() == diagram
        output.write_bytes(binary.content)
        print(json.dumps({name: value for name, value in artifact.items() if name != "content"}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("diagram_id")
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    asyncio.run(verify(arguments.base_url, arguments.diagram_id, arguments.output))
