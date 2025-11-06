"""Fluent builder API for creating Dagu DAGs programmatically"""

from typing import Any, Literal
import yaml

from .models.base import Precondition
from .models.dag import Dag
from .models.step import Step, RetryPolicy, ContinueOn, ParallelConfig
from .models.executor import (
    ExecutorConfig,
    HTTPExecutorConfig,
    SSHExecutorConfig,
    MailExecutorConfig,
    DockerExecutorConfig,
    JQExecutorConfig,
    ShellExecutorConfig,
)
from .models.handlers import HandlerConfig, HandlerOn
from .models.notifications import MailOn, SMTPConfig
from .models.infrastructure import ContainerConfig, SSHConfig


class DagBuilder:
    """Fluent builder class for creating Dagu DAGs programmatically

    Example:
        >>> dag = (DagBuilder("my-dag")
        ...     .description("My ETL pipeline")
        ...     .schedule("0 2 * * *")
        ...     .add_tag("production")
        ...     .add_step(command="python extract.py")
        ...     .add_step(command="python transform.py", depends="extract")
        ...     .build())
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        schedule: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new DAG builder

        Args:
            name: DAG name
            description: DAG description
            schedule: Cron expression for scheduling
            **kwargs: Additional DAG configuration options
        """
        self._dag_config = {
            "name": name,
            "description": description,
            "schedule": schedule,
            "steps": [],
            **kwargs,
        }

    def description(self, desc: str) -> "DagBuilder":
        """Set the DAG description"""
        self._dag_config["description"] = desc
        return self

    def schedule(self, cron: str) -> "DagBuilder":
        """Set the DAG schedule using a cron expression

        Args:
            cron: Cron expression (e.g., "0 2 * * *" for daily at 2 AM)
        """
        self._dag_config["schedule"] = cron
        return self

    def add_tag(self, tag: str) -> "DagBuilder":
        """Add a tag to the DAG"""
        if "tags" not in self._dag_config:
            self._dag_config["tags"] = []
        self._dag_config["tags"].append(tag)
        return self

    def tags(self, *tags: str) -> "DagBuilder":
        """Set multiple tags for the DAG"""
        self._dag_config["tags"] = list(tags)
        return self

    def max_active_runs(self, limit: int) -> "DagBuilder":
        """Set maximum concurrent DAG runs"""
        self._dag_config["maxActiveRuns"] = limit
        return self

    def max_active_steps(self, limit: int) -> "DagBuilder":
        """Set maximum concurrent steps"""
        self._dag_config["maxActiveSteps"] = limit
        return self

    def timeout(self, seconds: int) -> "DagBuilder":
        """Set DAG execution timeout in seconds"""
        self._dag_config["timeoutSec"] = seconds
        return self

    def history_retention(self, days: int) -> "DagBuilder":
        """Set history retention period in days"""
        self._dag_config["histRetentionDays"] = days
        return self

    def add_param(self, key: str, value: str) -> "DagBuilder":
        """Add a parameter to the DAG"""
        if "params" not in self._dag_config:
            self._dag_config["params"] = []
        self._dag_config["params"].append({key: value})
        return self

    def add_env(self, key: str, value: str) -> "DagBuilder":
        """Add an environment variable to the DAG"""
        if "env" not in self._dag_config:
            self._dag_config["env"] = []
        self._dag_config["env"].append({key: value})
        return self

    def dotenv(self, *paths: str) -> "DagBuilder":
        """Set dotenv file paths"""
        self._dag_config["dotenv"] = list(paths)
        return self

    def container(
        self,
        image: str,
        pull_policy: Literal["always", "missing", "never"] | None = None,
        env: list[str] | None = None,
        volumes: list[str] | None = None,
    ) -> "DagBuilder":
        """Set default container configuration for all steps"""
        self._dag_config["container"] = ContainerConfig(
            image=image,
            pullPolicy=pull_policy,
            env=env,
            volumes=volumes,
        )
        return self

    def ssh_config(
        self,
        user: str,
        host: str,
        port: int = 22,
        key: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> "DagBuilder":
        """Set SSH configuration for the DAG"""
        self._dag_config["ssh"] = SSHConfig(
            user=user,
            host=host,
            port=port,
            key=key,
            password=password,
            **kwargs,
        )
        return self

    def smtp_config(
        self,
        host: str,
        port: str,
        username: str | None = None,
        password: str | None = None,
    ) -> "DagBuilder":
        """Set SMTP configuration for email notifications"""
        self._dag_config["smtp"] = SMTPConfig(
            host=host,
            port=port,
            username=username,
            password=password,
        )
        return self

    def mail_on_failure(self, enabled: bool = True) -> "DagBuilder":
        """Enable/disable email notifications on failure"""
        if "mailOn" not in self._dag_config:
            self._dag_config["mailOn"] = MailOn(failure=enabled, success=None)
        else:
            self._dag_config["mailOn"].failure = enabled
        return self

    def mail_on_success(self, enabled: bool = True) -> "DagBuilder":
        """Enable/disable email notifications on success"""
        if "mailOn" not in self._dag_config:
            self._dag_config["mailOn"] = MailOn(failure=None, success=enabled)
        else:
            self._dag_config["mailOn"].success = enabled
        return self

    def add_precondition(self, condition: str, expected: str) -> "DagBuilder":
        """Add a DAG-level precondition"""
        if "preconditions" not in self._dag_config:
            self._dag_config["preconditions"] = []
        self._dag_config["preconditions"].append(
            Precondition(condition=condition, expected=expected)
        )
        return self

    def on_success(
        self, command: str | None = None, executor: ExecutorConfig | None = None
    ) -> "DagBuilder":
        """Set success handler"""
        if "handlerOn" not in self._dag_config:
            self._dag_config["handlerOn"] = HandlerOn(
                success=None, failure=None, cancel=None, exit=None
            )
        self._dag_config["handlerOn"].success = HandlerConfig(
            command=command, executor=executor
        )
        return self

    def on_failure(
        self, command: str | None = None, executor: ExecutorConfig | None = None
    ) -> "DagBuilder":
        """Set failure handler"""
        if "handlerOn" not in self._dag_config:
            self._dag_config["handlerOn"] = HandlerOn(
                success=None, failure=None, cancel=None, exit=None
            )
        self._dag_config["handlerOn"].failure = HandlerConfig(
            command=command, executor=executor
        )
        return self

    def on_exit(
        self, command: str | None = None, executor: ExecutorConfig | None = None
    ) -> "DagBuilder":
        """Set exit handler"""
        if "handlerOn" not in self._dag_config:
            self._dag_config["handlerOn"] = HandlerOn(
                success=None, failure=None, cancel=None, exit=None
            )
        self._dag_config["handlerOn"].exit = HandlerConfig(
            command=command, executor=executor
        )
        return self

    def add_step(
        self,
        name: str | None = None,
        command: str | None = None,
        script: str | None = None,
        **kwargs: Any,
    ) -> "DagBuilder":
        """Add a step to the DAG

        Args:
            name: Step name
            command: Command to execute
            script: Script path to execute
            **kwargs: Additional step configuration (depends, output, params, etc.)
        """
        if not command and not script:
            raise ValueError("Either command or script must be provided for a step")
        step = Step(name=name, command=command, script=script, **kwargs)
        self._dag_config["steps"].append(step)
        return self

    def add_simple_step(self, command_or_script: str) -> "DagBuilder":
        """Add a simple step with just a command or script path"""
        self._dag_config["steps"].append(command_or_script)
        return self

    def add_step_models(self, *steps: Step) -> "DagBuilder":
        """Add one or more pre-built Step object to the DAG"""
        for step in steps:
            self._dag_config["steps"].append(step)
        return self

    def build(self) -> Dag:
        """Build and return the final DAG model"""
        return Dag(**self._dag_config)

    def to_yaml(self, exclude_none: bool = True) -> str:
        """Export the DAG to YAML format

        Args:
            exclude_none: Exclude None values from output
        """
        dag = self.build()
        dag_dict = dag.model_dump(exclude_none=exclude_none)
        return yaml.dump(dag_dict, default_flow_style=False, sort_keys=False)

    def to_dict(self, exclude_none: bool = True) -> dict[str, Any]:
        """Export the DAG to a dictionary

        Args:
            exclude_none: Exclude None values from output
        """
        dag = self.build()
        return dag.model_dump(exclude_none=exclude_none)

    def save(self, filepath: str, exclude_none: bool = True) -> None:
        """Save the DAG to a YAML file

        Args:
            filepath: Path to save the YAML file
            exclude_none: Exclude None values from output
        """
        with open(filepath, "w") as f:
            f.write(self.to_yaml(exclude_none=exclude_none))


class StepBuilder:
    """Builder for creating individual steps with complex configurations

    Example:
        >>> step = (StepBuilder("extract")
        ...     .command("python extract.py")
        ...     .depends_on("validate")
        ...     .retry(limit=3, interval=60)
        ...     .docker_executor(image="python:3.11")
        ...     .build())
    """

    def __init__(self, name: str | None = None):
        """Initialize a step builder

        Args:
            name: Step name
        """
        self._step_config: dict[str, Any] = {"name": name}

    def command(self, cmd: str) -> "StepBuilder":
        """Set the command to execute"""
        self._step_config["command"] = cmd
        return self

    def script(self, path: str) -> "StepBuilder":
        """Set the script path to execute"""
        self._step_config["script"] = path
        return self

    def description(self, desc: str) -> "StepBuilder":
        """Set the step description"""
        self._step_config["description"] = desc
        return self

    def depends_on(self, *steps: str) -> "StepBuilder":
        """Set step dependencies"""
        if len(steps) == 1:
            self._step_config["depends"] = steps[0]
        else:
            self._step_config["depends"] = list(steps)
        return self

    def output(self, var_name: str) -> "StepBuilder":
        """Set output variable name"""
        self._step_config["output"] = var_name
        return self

    def params(self, *params: str) -> "StepBuilder":
        """Set step parameters"""
        if len(params) == 1:
            self._step_config["params"] = params[0]
        else:
            self._step_config["params"] = list(params)
        return self

    def working_dir(self, path: str) -> "StepBuilder":
        """Set working directory"""
        self._step_config["dir"] = path
        return self

    def retry(self, limit: int, interval: int) -> "StepBuilder":
        """Set retry policy

        Args:
            limit: Maximum number of retries
            interval: Interval between retries in seconds
        """
        self._step_config["retryPolicy"] = RetryPolicy(
            limit=limit, intervalSec=interval
        )
        return self

    def continue_on_failure(self, enabled: bool = True) -> "StepBuilder":
        """Continue execution even if this step fails"""
        if "continueOn" not in self._step_config:
            self._step_config["continueOn"] = ContinueOn(failure=enabled, skipped=None)
        else:
            self._step_config["continueOn"].failure = enabled
        return self

    def parallel(
        self, items: list[str], max_concurrent: int | None = None
    ) -> "StepBuilder":
        """Set parallel execution configuration

        Args:
            items: Items to process in parallel
            max_concurrent: Maximum concurrent items
        """
        self._step_config["parallel"] = ParallelConfig(
            items=items, maxConcurrent=max_concurrent
        )
        return self

    def docker_executor(
        self,
        image: str,
        pull: bool | None = None,
        env: list[str] | dict[str, str] | None = None,
        volumes: list[str] | None = None,
        **kwargs: Any,
    ) -> "StepBuilder":
        """Set Docker executor for this step"""
        self._step_config["executor"] = ExecutorConfig(
            type="docker",
            config=DockerExecutorConfig(
                image=image, pull=pull, env=env, volumes=volumes, **kwargs
            ),
        )
        return self

    def http_executor(
        self,
        headers: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
        body: str | dict[str, Any] | None = None,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> "StepBuilder":
        """Set HTTP executor for this step"""
        self._step_config["executor"] = ExecutorConfig(
            type="http",
            config=HTTPExecutorConfig(
                headers=headers, query=query, body=body, timeout=timeout, **kwargs
            ),
        )
        return self

    def ssh_executor(
        self,
        user: str,
        host: str,
        port: int = 22,
        key: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> "StepBuilder":
        """Set SSH executor for this step"""
        self._step_config["executor"] = ExecutorConfig(
            type="ssh",
            config=SSHExecutorConfig(
                user=user, host=host, port=port, key=key, password=password, **kwargs
            ),
        )
        return self

    def mail_executor(
        self,
        to: str | list[str],
        subject: str | None = None,
        body: str | None = None,
        **kwargs: Any,
    ) -> "StepBuilder":
        """Set mail executor for this step"""
        self._step_config["executor"] = ExecutorConfig(
            type="mail",
            config=MailExecutorConfig(to=to, subject=subject, body=body, **kwargs),
        )
        return self

    def shell_executor(
        self,
        shell: str = "bash",
        env: dict[str, str] | None = None,
    ) -> "StepBuilder":
        """Set shell executor for this step"""
        self._step_config["executor"] = ExecutorConfig(
            type="shell",
            config=ShellExecutorConfig(shell=shell, env=env),  # nosec: B604
        )
        return self

    def jq_executor(
        self,
        query: str,
        raw: bool | None = None,
        compact: bool | None = None,
    ) -> "StepBuilder":
        """Set jq executor for this step"""
        self._step_config["executor"] = ExecutorConfig(
            type="jq",
            config=JQExecutorConfig(query=query, raw=raw, compact=compact),
        )
        return self

    def mail_on_error(self, enabled: bool = True) -> "StepBuilder":
        """Send email notification on step error"""
        self._step_config["mailOnError"] = enabled
        return self

    def add_precondition(self, condition: str, expected: str) -> "StepBuilder":
        """Add a step-level precondition"""
        if "preconditions" not in self._step_config:
            self._step_config["preconditions"] = []
        self._step_config["preconditions"].append(
            Precondition(condition=condition, expected=expected)
        )
        return self

    def build(self) -> Step:
        """Build and return the final Step model"""
        return Step(**self._step_config)
