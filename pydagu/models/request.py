"""
Pydantic models for requests to the Dagu HTTP API.
"""

from .types import DaguBase


class StartDagRun(DaguBase):
    """Model for starting a DAG run via the Dagu HTTP API."""

    params: str | None = None
    dagRunId: str | None = None
    dagName: str | None = None
    singleton: bool | None = None
