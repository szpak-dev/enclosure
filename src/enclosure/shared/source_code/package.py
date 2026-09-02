from pydantic import BaseModel, field_validator

from .errors import SourceCodeError


class CodePackage(BaseModel):
    """Keeps map of relative paths to file content. File tree is rendered.

    Raises:
        ValueError: in case anything wrong with a path

    Returns:
        dict[str, str]: paths to strings
    """

    files: dict[str, str]

    @field_validator("files")
    @classmethod
    def validate_file_paths(cls, files: dict[str, str]) -> dict[str, str]:
        for path in files:
            cls._validate_file_path(path)
        return files

    @staticmethod
    def _validate_file_path(path: str) -> None:
        if not path:
            raise SourceCodeError("Code package file path cannot be empty.")

        if "\\" in path:
            raise SourceCodeError(f"Code package path must use POSIX separators: {path!r}")

        if path.startswith("/"):
            raise SourceCodeError(f"Code package path must be relative: {path!r}")

        if path.endswith("/"):
            raise SourceCodeError(f"Code package path must point to a file: {path!r}")

        parts = path.split("/")

        if any(part in {"", ".", ".."} for part in parts):
            raise SourceCodeError(f"Code package path contains an invalid segment: {path!r}")


class SourceCodePackage(BaseModel):
    """CodePackage but knows what particular language it carries. File tree is rendered.

    Raises:
        ValueError: in case anything wrong with a path

    Returns:
        dict[str, str]: paths to strings
    """

    language: str
    package: CodePackage
