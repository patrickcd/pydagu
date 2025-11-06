"""
Pydantic models for Dagu HTTP API responses.
"""

from datetime import datetime

from pydantic import BaseModel

from .types import EmptyStrToNone


class DagRunId(BaseModel):
    """Model for DAG run ID response from the Dagu HTTP API."""

    dagRunId: str


class DagResponseMessage(BaseModel):
    """Model for DAG start response from the Dagu HTTP API."""

    code: str
    message: str


class DagSubRun(BaseModel):
    """
    Model for DAG run sub-run response from the Dagu HTTP API.

    """

    dagRunId: str
    name: str
    status: int
    statusLabel: str


class DagNodeStep(BaseModel):
    """
    Model for DAG run node step response from the Dagu HTTP API.

    """

    name: str
    command: str | None = None
    run: str | None = None
    params: str | None = None


class DagRunNode(BaseModel):
    """
    Model for DAG run node response from the Dagu HTTP API.

    """

    step: DagNodeStep
    status: int
    statusLabel: str
    startedAt: datetime | EmptyStrToNone = None
    finishedAt: datetime | EmptyStrToNone = None
    retryCount: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    subRuns: list[DagSubRun] | None = None


class DagRunResult(BaseModel):
    """
    Model for DAG run result response from the Dagu HTTP API.

    """

    dagRunId: str
    name: str
    status: int
    statusLabel: str
    startedAt: datetime | EmptyStrToNone = None
    finishedAt: datetime | EmptyStrToNone = None
    params: str | None = None
    nodes: list[DagRunNode]


__all__ = ["DagRunId", "DagResponseMessage", "DagRunResult"]
