import asyncio

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from enclosure.core.asgi import application, mcp_application


def test_composite_application_serves_django_and_mcp() -> None:
    async def exercise():
        transport = httpx2.ASGITransport(app=application)
        async with (
            mcp_application.router.lifespan_context(mcp_application),
            httpx2.AsyncClient(
                transport=transport,
                base_url="http://localhost:8000",
            ) as http_client,
        ):
            rest_response = await http_client.get("/api/languages")
            async with (
                streamable_http_client(
                    "http://localhost:8000/mcp",
                    http_client=http_client,
                    terminate_on_close=False,
                ) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                initialization = await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool(
                    "get_language",
                    {"language_id": "python"},
                )
        return rest_response, initialization, tools, result

    rest_response, initialization, tools, result = asyncio.run(exercise())

    assert rest_response.status_code == 200
    assert initialization.server_info.name == "enclosure"
    assert "find_languages" in {tool.name for tool in tools.tools}
    assert result.is_error is False
    assert result.structured_content["properties"]["id"] == "python"
