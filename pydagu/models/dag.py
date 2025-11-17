"""Main DAG model"""

import re
from typing import Self

from pydantic import Field, field_validator, model_validator, BaseModel, ConfigDict

from .base import Precondition
from .step import Step
from .handlers import HandlerOn
from .notifications import MailOn, SMTPConfig
from .infrastructure import ContainerConfig, SSHConfig


# Pattern that matches: *, single values, ranges, steps, lists, and combinations
# Examples: *, 5, 1-5, */5, 1-10/2, 1,5,10, MON-FRI
CRON_PATTERN = re.compile(r"^(\*|[\w-]+)(\/\d+)?$|^[\w-]+(,[\w-]+)+$")


class Dag(BaseModel):
    """Dagu DAG (Directed Acyclic Graph) definition"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="DAG name",
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$",
        examples=["production-etl", "daily-backup", "data-pipeline"],
    )
    description: str | None = Field(
        "",
        description="DAG description",
        examples=["Daily ETL pipeline for production data"],
    )
    tags: list[str] | None = Field(
        None,
        description="Tags for categorization",
        examples=[["production", "etl", "critical"]],
    )
    schedule: str | None = Field(
        None,
        description="Cron expression for scheduling",
        pattern=r"^[\w*,/-]+\s+[\w*,/-]+\s+[\w*,/-]+\s+[\w*,/-]+\s+[\w*,/-]+(\s+[\w*,/-]+)?$",
        examples=["0 2 * * *", "*/5 * * * *", "0 0 1 * *", "0 9-17 * * MON-FRI"],
    )

    # Execution settings
    maxActiveRuns: int | None = Field(
        None, ge=1, description="Maximum concurrent DAG runs", examples=[1, 3, 5]
    )
    maxActiveSteps: int | None = Field(
        None, ge=1, description="Maximum concurrent steps", examples=[3, 5, 10]
    )
    timeoutSec: int | None = Field(
        None, ge=0, description="Timeout in seconds", examples=[3600, 7200, 14400]
    )
    delay: int | None = Field(
        None, ge=0, description="Delay before execution", examples=[0, 30, 60]
    )
    histRetentionDays: int | None = Field(
        None, ge=0, description="History retention in days", examples=[30, 90, 365]
    )

    # Parameters and environment
    params: list[str | dict[str, str]] | None = Field(
        None,
        description="DAG parameters",
        examples=[[{"DATE": "`date +%Y-%m-%d`"}, {"ENVIRONMENT": "production"}]],
    )
    env: list[str | dict[str, str]] | None = Field(
        None,
        description="Environment variables",
        examples=[[{"DATA_DIR": "/data/etl"}, {"LOG_LEVEL": "info"}]],
    )
    dotenv: list[str] | None = Field(
        None,
        description="Paths to .env files",
        examples=[["/etc/dagu/production.env", ".env"]],
    )

    # Container configuration
    container: ContainerConfig | None = Field(
        None, description="Default container configuration"
    )

    # Preconditions
    preconditions: list[Precondition] | None = Field(
        None, description="DAG-level preconditions"
    )

    # Steps
    steps: list[str | Step] = Field(
        ...,
        min_length=1,
        description="DAG steps (at least one required)",
        examples=[["./scripts/validate.sh", "python process.py"]],
    )

    # Handlers
    handlerOn: HandlerOn | None = Field(None, description="Event handlers")

    # Notifications
    mailOn: MailOn | None = Field(None, description="Email notification triggers")
    smtp: SMTPConfig | None = Field(None, description="SMTP configuration")

    # SSH configuration
    ssh: SSHConfig | None = Field(
        None, description="SSH configuration for remote execution"
    )

    # Additional settings
    logDir: str | None = Field(
        None, description="Log directory", examples=["/var/log/dagu", "./logs"]
    )
    restartWaitSec: int | None = Field(
        None, ge=0, description="Wait time before restart", examples=[10, 30, 60]
    )

    @field_validator("schedule")
    @classmethod
    def validate_cron_expression(cls, v: str | None) -> str | None:
        """Validate cron field structure - ensures proper syntax for each field"""
        if v is None:
            return v

        # Field pattern already enforces 5 or 6 fields
        # Validate each field has proper cron syntax structure
        fields = v.split()
        for i, field in enumerate(fields):
            if not CRON_PATTERN.match(field):
                field_names = ["minute", "hour", "day", "month", "weekday", "year"]
                raise ValueError(
                    f"Invalid cron expression: '{v}'. "
                    f"Invalid {field_names[i]} field: '{field}'. "
                    "Expected format: 'minute hour day month weekday [year]'"
                )

        return v

    @model_validator(mode="after")
    def validate_unique_step_names(self: Self) -> Self:
        """Validate that all named steps have unique names"""
        step_names = []
        for i, step in enumerate(self.steps):
            if isinstance(step, Step) and step.name:
                step_names.append((step.name, i))

        # Check for duplicates
        seen = set()
        for name, index in step_names:
            if name in seen:
                raise ValueError(
                    f"Step name must be unique. Duplicate name found: '{name}'"
                )
            seen.add(name)

        return self

    @model_validator(mode="after")
    def validate_step_dependencies(self: Self) -> Self:
        """Validate that all step dependencies reference defined steps"""
        # Build a set of valid step names
        step_names = set()
        for i, step in enumerate(self.steps):
            if isinstance(step, str):
                # String steps don't have explicit names, they're auto-numbered
                step_names.add(str(i + 1))
            elif isinstance(step, Step):
                if step.name:
                    step_names.add(step.name)
                else:
                    # If no name, dagu auto-generates based on position
                    step_names.add(str(i + 1))

        # Check each step's dependencies
        for i, step in enumerate(self.steps):
            if isinstance(step, str):
                continue

            if not step.depends:
                continue

            # depends can be a string or list of strings
            depends_list = (
                [step.depends] if isinstance(step.depends, str) else step.depends
            )

            for dep in depends_list:
                if dep not in step_names:
                    step_identifier = step.name if step.name else f"step at index {i}"
                    raise ValueError(
                        f"Step '{step_identifier}' has invalid dependency '{dep}'. "
                        f"Available steps: {', '.join(sorted(step_names))}"
                    )

        return self
