"""Handler configuration models"""

from pydantic import BaseModel, Field

from pydagu.models.executor import ExecutorConfig


class HandlerConfig(BaseModel):
    """Handler configuration for DAG events"""

    command: str | None = Field(
        None,
        description="Command to execute",
        examples=[
            "./scripts/notify-success.sh",
            "echo 'ETL completed successfully for ${DATE}'",
        ],
    )
    executor: ExecutorConfig | None = Field(
        None, description="Executor for the handler"
    )


class HandlerOn(BaseModel):
    """Handlers for different DAG lifecycle events"""

    success: HandlerConfig | None = Field(None, description="Handler on success")
    failure: HandlerConfig | None = Field(None, description="Handler on failure")
    cancel: HandlerConfig | None = Field(None, description="Handler on cancel")
    exit: HandlerConfig | None = Field(None, description="Handler on exit")
