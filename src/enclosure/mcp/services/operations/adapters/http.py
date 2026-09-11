from dataclasses import dataclass, field
from http.cookies import SimpleCookie

from django.core.handlers.wsgi import WSGIHandler
from django.core.wsgi import get_wsgi_application
from httpx import Client, WSGITransport
from sirenity import SirenMcpExecution, SirenMcpOperation
from wireup import injectable


@injectable
@dataclass(frozen=True)
class HttpSirenExecutor:
    _application: WSGIHandler = field(default_factory=get_wsgi_application, init=False, repr=False)

    def execute(self, operation: SirenMcpOperation) -> SirenMcpExecution:
        headers = {
            "accept": "application/json",
            **{name: str(value) for name, value in operation.header_values.items()},
        }
        if operation.cookie_values:
            cookie = SimpleCookie({name: str(value) for name, value in operation.cookie_values.items()})
            headers["cookie"] = "; ".join(morsel.OutputString() for morsel in cookie.values())

        with Client(
            transport=WSGITransport(app=self._application),
            base_url="http://localhost",
        ) as client:
            response = client.request(
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
