"""
Pydantic models for requests to the Dagu HTTP API.
"""

from pydantic import BaseModel


class StartDagRun(BaseModel):
    """Model for starting a DAG run via the Dagu HTTP API."""

    params: str | None = None
    dagRunId: str | None = None
    dagName: str | None = None
    singleton: bool | None = None
