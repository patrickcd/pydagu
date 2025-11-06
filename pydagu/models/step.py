"""Step configuration models"""

import re
from typing import Any, Literal, Self
from pydantic import BaseModel, Field, model_validator

from pydagu.models.base import Precondition
from pydagu.models.executor import ExecutorConfig


class RetryPolicy(BaseModel):
    """Retry policy for a step"""

    limit: int = Field(
        ge=0, description="Maximum number of retries", examples=[3, 5, 10]
    )
    intervalSec: int = Field(
        ge=0, description="Interval between retries in seconds", examples=[30, 60, 300]
    )


class ContinueOn(BaseModel):
    """Configuration for continuing execution on specific conditions"""

    failure: bool | None = Field(None, description="Continue on failure")
    skipped: bool | None = Field(None, description="Continue on skipped")


class ParallelConfig(BaseModel):
    """Configuration for parallel step execution"""

    items: list[str] = Field(
        description="Items to process in parallel",
        examples=[
            ["customers", "orders", "products"],
            ["file1.csv", "file2.csv", "file3.csv"],
        ],
    )
    maxConcurrent: int | None = Field(
        None, ge=1, description="Maximum concurrent items", examples=[2, 5, 10]
    )


class Step(BaseModel):
    """A step in the DAG"""

    model_config = {
        "json_schema_extra": {
            "anyOf": [{"required": ["command"]}, {"required": ["script"]}],
        }
    }

    name: str | None = Field(
        None, description="Step name", examples=["extract-data", "validate-environment"]
    )
    description: str | None = Field(
        None,
        description="Step description",
        examples=["Extract data from source database"],
    )
    command: str | None = Field(
        None,
        description="Command to execute",
        examples=["python extract.py --date=${DATE}", "echo 'Processing...'"],
    )
    script: str | None = Field(
        None,
        description="Script path to execute",
        examples=["./scripts/process.sh", "process.py"],
    )
    depends: str | list[str] | None = Field(
        None,
        description="Dependencies (step names)",
        examples=["validate-environment", ["extract", "transform"]],
    )
    output: str | None = Field(
        None,
        description="Output variable name",
        examples=["RAW_DATA_PATH", "RESULT_COUNT"],
    )
    params: str | list[str] | None = Field(
        None,
        description="Parameters for the step",
        examples=[
            "TYPE=${ITEM} INPUT=${RAW_DATA_PATH}",
            ["--verbose", "--config=prod"],
        ],
    )
    dir: str | None = Field(
        None, description="Working directory", examples=["/data/workspace", "./scripts"]
    )
    executor: ExecutorConfig | None = Field(
        None, description="Custom executor for this step"
    )
    continueOn: ContinueOn | None = Field(
        None, description="Continue execution conditions"
    )
    retryPolicy: RetryPolicy | None = Field(None, description="Retry policy")
    repeatPolicy: dict[str, Any] | None = Field(None, description="Repeat policy")
    mailOnError: bool | None = Field(None, description="Send email on error")
    preconditions: list[Precondition] | None = Field(
        None, description="Step-level preconditions"
    )
    signalOnStop: (
        Literal["SIGTERM", "SIGINT", "SIGKILL", "SIGHUP", "SIGQUIT"] | None
    ) = Field(
        None,
        description="Signal to send on stop",
        examples=["SIGTERM", "SIGKILL", "SIGINT"],
    )
    parallel: ParallelConfig | None = Field(
        None, description="Parallel execution configuration"
    )

    @model_validator(mode="after")
    def validate_step_has_action(self: Self) -> Self:
        """Validate that step has at least one of: command or script"""
        if not (self.command or self.script):
            raise ValueError(
                "Step must have at least one of: command or script. "
                "Examples: command='echo hello', script='./run.sh'"
            )
        return self

    @model_validator(mode="after")
    def validate_http_executor_command(self: Self) -> Self:
        """Validate that HTTP executor steps have command in 'METHOD URL' format"""
        if self.executor and self.executor.type == "http" and self.command:
            # HTTP executor requires command in format: "METHOD URL"
            # Valid methods: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
            # URL can be a literal or a Dagu parameter like ${WEBHOOK_URL}
            http_method_pattern = re.compile(
                r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(https?://\S+|\$\{[A-Z_]+\})",
                re.IGNORECASE,
            )
            if not http_method_pattern.match(self.command):
                raise ValueError(
                    f"HTTP executor command must be in format 'METHOD URL'. "
                    f"Got: '{self.command}'. "
                    f"Examples: 'GET https://api.example.com/data', "
                    f"'POST https://api.example.com/webhook', "
                    f"'POST ${{WEBHOOK_URL}}' (using Dagu parameter)"
                )
        return self
