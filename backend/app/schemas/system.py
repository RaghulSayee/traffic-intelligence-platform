from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response returned by the application health endpoint."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    """Response returned when required dependencies are available."""

    status: Literal["ready"]
    database: Literal["available"]
