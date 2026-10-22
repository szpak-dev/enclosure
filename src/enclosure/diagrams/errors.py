from enclosure.shared import DomainError


class DiagramsError(DomainError): ...


class DiagramRenderValidationError(DiagramsError):
    def __init__(
        self,
        code: str,
        message: str,
        details: str,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        detail = f" Details: {details}" if details else ""
        super().__init__(f"Mermaiden render validation failed [{code}]: {message}{detail}")
