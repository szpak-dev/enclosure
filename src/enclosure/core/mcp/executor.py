from dataclasses import dataclass
from http.cookies import SimpleCookie

from httpx import Client
from sirenity import SirenMcpExecution, SirenMcpOperation


@dataclass(frozen=True)
class SirenExecutor:
    client: Client

    def execute(self, operation: SirenMcpOperation) -> SirenMcpExecution:
        headers = {
            "accept": "application/json",
            **{name: str(value) for name, value in operation.header_values.items()},
        }
        if operation.cookie_values:
            cookie = SimpleCookie({name: str(value) for name, value in operation.cookie_values.items()})
            headers["cookie"] = "; ".join(morsel.OutputString() for morsel in cookie.values())

        response = self.client.request(
            operation.method,
            operation.dispatch_path,
            headers=headers,
            params=operation.query_values,
            json=operation.body,
        )
        result = response.json() if response.content else None
        base_url = f"{response.url.scheme}://{response.url.netloc.decode()}"

        return SirenMcpExecution(
            status=response.status_code,
            result=result,
            base_url=base_url,
            request_url=str(response.url),
            headers=dict(response.headers),
        )
