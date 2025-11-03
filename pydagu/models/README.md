# Pydagu Models

This package contains Pydantic models for validating Dagu DAG configurations.

## Package Structure

```
pydagu/models/
├── __init__.py           # Package exports
├── base.py               # Base models and common types
├── dag.py                # Main DAG model
├── step.py               # Step configuration models
├── executor.py           # Executor type models
├── handlers.py           # Event handler models
├── notifications.py      # Email/notification models
└── infrastructure.py     # Container, SSH, and logging models
```

## Module Organization

### `base.py`
Common base types used across multiple modules:
- `Precondition` - Conditions that must be met before execution

### `dag.py`
Main DAG model:
- `Dag` - Complete DAG definition with validation

### `step.py`
Step-related models:
- `Step` - Individual DAG step configuration
- `RetryPolicy` - Retry behavior configuration
- `ContinueOn` - Execution continuation rules
- `ParallelConfig` - Parallel execution settings

### `executor.py`
Executor configurations for different backends:
- `ExecutorConfig` - Base executor with type validation
- `HTTPExecutorConfig` - HTTP request executor
- `SSHExecutorConfig` - SSH remote execution
- `MailExecutorConfig` - Email sending executor
- `DockerExecutorConfig` - Docker container executor
- `JQExecutorConfig` - JSON processing executor
- `ShellExecutorConfig` - Shell command executor

### `handlers.py`
Lifecycle event handlers:
- `HandlerConfig` - Individual handler configuration
- `HandlerOn` - Handlers for success/failure/exit events

### `notifications.py`
Email notification settings:
- `MailOn` - Notification trigger configuration
- `SMTPConfig` - SMTP server settings

### `infrastructure.py`
Infrastructure and deployment settings:
- `ContainerConfig` - Container/Docker settings
- `SSHConfig` - SSH connection configuration
- `LogConfig` - Logging configuration

## Usage

```python
from pydagu.models import Dag
import yaml

# Load and validate
with open("dag.yaml") as f:
    dag_data = yaml.safe_load(f)
    dag = Dag(**dag_data)

# Access typed fields
print(dag.schedule)  # str | None with cron validation
print(dag.steps)     # list[str | Step]
```

## Design Principles

1. **Logical grouping** - Related models are grouped in the same module
2. **Minimal dependencies** - Each module imports only what it needs
3. **Type safety** - Full type hints using Python 3.12+ syntax
4. **Validation** - Field validators for complex formats (cron, executor types)
5. **Documentation** - Each model and field has descriptive docstrings
