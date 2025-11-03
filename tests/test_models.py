"""Tests for Pydantic models"""

import pytest
from pydantic import ValidationError

from pydagu.models import (
    Dag,
    Step,
    Precondition,
    RetryPolicy,
    ParallelConfig,
    ExecutorConfig,
    HTTPExecutorConfig,
    ContainerConfig,
    SMTPConfig,
)


# DAG Model Tests


def test_minimal_dag():
    """Test creating a minimal valid DAG"""
    dag = Dag(name="test-dag", steps=["echo 'Hello'"])
    assert dag.name == "test-dag"
    assert len(dag.steps) == 1


@pytest.mark.parametrize(
    "schedule",
    [
        "0 2 * * *",  # Daily at 2 AM
        "*/5 * * * *",  # Every 5 minutes
        "0 0 1 * *",  # First day of month
        "0 9-17 * * MON-FRI",  # Weekdays 9 AM to 5 PM (range in hour)
        "0 0 * * 0",  # Every Sunday
        "0 0 * * SUN",  # Every Sunday (named)
        "15 2 * * 1-5",  # Weekdays at 2:15 AM
        "0 */4 * * *",  # Every 4 hours
        "0 0 1,15 * *",  # 1st and 15th of month
        "30 8-18/2 * * *",  # Every 2 hours from 8 AM to 6 PM (range with step)
    ],
)
def test_dag_schedule_validation_valid(schedule):
    """Test that valid cron schedules are accepted"""
    dag = Dag(name="test", schedule=schedule, steps=["echo test"])
    assert dag.schedule == schedule


@pytest.mark.parametrize(
    "schedule",
    [
        "invalid cron",
        "* * * *",  # Too few fields
    ],
)
def test_dag_schedule_validation_invalid(schedule):
    """Test that invalid cron expressions are rejected"""
    with pytest.raises(ValidationError):
        Dag(name="test", schedule=schedule, steps=["echo test"])


def test_dag_with_tags():
    """Test DAG with tags"""
    dag = Dag(
        name="test-dag",
        tags=["production", "etl", "critical"],
        steps=["test"],
    )
    assert len(dag.tags) == 3
    assert "production" in dag.tags


def test_dag_with_execution_settings():
    """Test DAG with execution settings"""
    dag = Dag(
        name="test-dag",
        maxActiveRuns=2,
        maxActiveSteps=5,
        timeoutSec=3600,
        histRetentionDays=30,
        steps=["test"],
    )
    assert dag.maxActiveRuns == 2
    assert dag.maxActiveSteps == 5
    assert dag.timeoutSec == 3600
    assert dag.histRetentionDays == 30


def test_dag_with_container():
    """Test DAG with container configuration"""
    dag = Dag(
        name="test-dag",
        container=ContainerConfig(
            image="python:3.11",
            pullPolicy="always",
            env=["DEBUG=1"],
        ),
        steps=["test"],
    )
    assert dag.container.image == "python:3.11"
    assert dag.container.pullPolicy == "always"


def test_dag_model_dump():
    """Test exporting DAG to dictionary"""
    dag = Dag(
        name="test-dag",
        description="Test description",
        tags=["test"],
        steps=["echo 'test'"],
    )
    dag_dict = dag.model_dump(exclude_none=True)
    assert dag_dict["name"] == "test-dag"
    assert dag_dict["description"] == "Test description"
    assert "tags" in dag_dict


# Step Model Tests


def test_minimal_step():
    """Test creating a minimal step"""
    step = Step(command="echo 'Hello'")
    assert step.command == "echo 'Hello'"


@pytest.mark.parametrize(
    "depends",
    [
        "previous",
        ["step1", "step2"],
    ],
)
def test_step_with_dependencies(depends):
    """Test step with dependencies"""
    step = Step(command="test", depends=depends)
    assert step.depends == depends


def test_step_with_retry_policy():
    """Test step with retry policy"""
    step = Step(
        command="test",
        retryPolicy=RetryPolicy(limit=3, intervalSec=60),
    )
    assert step.retryPolicy.limit == 3
    assert step.retryPolicy.intervalSec == 60


def test_step_with_parallel_config():
    """Test step with parallel execution"""
    step = Step(
        command="process ${ITEM}",
        parallel=ParallelConfig(
            items=["a", "b", "c"],
            maxConcurrent=2,
        ),
    )
    assert len(step.parallel.items) == 3
    assert step.parallel.maxConcurrent == 2


def test_step_with_executor():
    """Test step with custom executor"""
    step = Step(
        command="test",
        executor=ExecutorConfig(
            type="docker",
            config={"image": "python:3.11"},
        ),
    )
    assert step.executor.type == "docker"


# Executor Model Tests


@pytest.mark.parametrize(
    "exec_type",
    ["shell", "http", "jq", "ssh", "mail", "docker"],
)
def test_executor_type_validation_valid(exec_type):
    """Test that valid executor types are accepted"""
    executor = ExecutorConfig(type=exec_type)
    assert executor.type == exec_type.lower()


def test_executor_invalid_type():
    """Test that invalid executor type is rejected"""
    with pytest.raises(ValidationError):
        ExecutorConfig(type="invalid")


def test_http_executor_config():
    """Test HTTP executor configuration"""
    config = HTTPExecutorConfig(
        headers={"Authorization": "Bearer token"},
        query={"page": "1"},
        body={"key": "value"},
        timeout=30,
    )
    assert config.headers["Authorization"] == "Bearer token"
    assert config.timeout == 30


# Precondition Model Tests


def test_precondition():
    """Test creating a precondition"""
    precondition = Precondition(
        condition="`date +%u`",
        expected="re:[1-5]",
    )
    assert precondition.condition == "`date +%u`"
    assert precondition.expected == "re:[1-5]"


# Notification Model Tests


def test_smtp_config():
    """Test SMTP configuration"""
    smtp = SMTPConfig(
        host="smtp.example.com",
        port="587",
        username="user@example.com",
        password="secret",
    )
    assert smtp.host == "smtp.example.com"
    assert smtp.port == "587"
    assert smtp.username == "user@example.com"


# Validation Edge Cases


def test_dag_without_name():
    """Test that DAG without name fails validation"""
    with pytest.raises(ValidationError):
        Dag(steps=["test"])


def test_dag_without_steps():
    """Test that DAG without steps fails validation"""
    with pytest.raises(ValidationError):
        Dag(name="test")


def test_negative_timeout():
    """Test that negative timeout is rejected"""
    with pytest.raises(ValidationError):
        Dag(name="test", timeoutSec=-1, steps=["test"])


def test_negative_retry_limit():
    """Test that negative retry limit is rejected"""
    with pytest.raises(ValidationError):
        RetryPolicy(limit=-1, intervalSec=60)


def test_empty_parallel_items():
    """Test that empty parallel items list is allowed (validation depends on usage)"""
    # ParallelConfig doesn't have min_length constraint, so empty list is technically valid
    # In practice, Dagu would handle this at runtime
    config = ParallelConfig(items=[])
    assert config.items == []


def test_invalid_max_concurrent():
    """Test that invalid maxConcurrent values are rejected"""
    with pytest.raises(ValidationError):
        ParallelConfig(items=["a", "b"], maxConcurrent=0)

    with pytest.raises(ValidationError):
        ParallelConfig(items=["a", "b"], maxConcurrent=-1)


# Step Dependency Validation Tests


def test_step_dependency_validation_valid():
    """Test that valid step dependencies are accepted"""

    # Valid single dependency
    dag1 = Dag(
        name="valid-deps",
        steps=[
            {"name": "step1", "command": "echo 1"},
            {"name": "step2", "command": "echo 2", "depends": "step1"},
        ],
    )
    assert dag1 is not None

    # Valid list dependency
    dag2 = Dag(
        name="valid-list-deps",
        steps=[
            {"name": "step1", "command": "echo 1"},
            {"name": "step2", "command": "echo 2"},
            {"name": "step3", "command": "echo 3", "depends": ["step1", "step2"]},
        ],
    )
    assert dag2 is not None

    # Valid auto-numbered dependency
    dag3 = Dag(
        name="valid-auto-deps",
        steps=["echo step1", {"command": "echo step2", "depends": "1"}],
    )
    assert dag3 is not None


def test_step_dependency_validation_invalid():
    """Test that invalid step dependencies are rejected"""

    # Invalid single dependency
    with pytest.raises(ValidationError, match="invalid dependency"):
        Dag(
            name="invalid-deps",
            steps=[
                {"name": "step1", "command": "echo 1"},
                {"name": "step2", "command": "echo 2", "depends": "nonexistent"},
            ],
        )

    # Invalid dependency in list
    with pytest.raises(ValidationError, match="invalid dependency"):
        Dag(
            name="invalid-list-deps",
            steps=[
                {"name": "step1", "command": "echo 1"},
                {"name": "step2", "command": "echo 2", "depends": ["step1", "missing"]},
            ],
        )


def test_step_requires_command_or_script():
    """Test that a step must have either command or script"""

    # Valid with command
    step1 = Step(command="echo hello")
    assert step1.command == "echo hello"

    # Valid with script
    step2 = Step(script="./run.sh")
    assert step2.script == "./run.sh"

    # Invalid - neither command nor script
    with pytest.raises(
        ValidationError, match="must have at least one of: command or script"
    ):
        Step(name="empty-step")
