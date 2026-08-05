from pydantic import BaseModel, Field


class DetectedStack(BaseModel):
    language: str = Field(description="Detected programming-language identifier.")
    language_version: str = Field(description="Detected programming-language version, when available.")
    package_manager: str = Field(description="Detected package-manager identifier.")


class DiscoveredProject(BaseModel):
    root: str = Field(description="Absolute path to the project directory.")
    stack: DetectedStack = Field(description="Technology stack detected in the project directory.")
