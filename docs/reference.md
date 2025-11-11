# PyDagu Reference

PyDagu does two things:

1. It provides a set of Pydantic models for creating validated Dagu HTTP API data structures.
2. It provides an HTTP client for interacting with the Dagu API.

## Models

The models are located in the `pydagu.models` module. You can import them like this:

```python
from pydagu.models import Dag, Step, HTTPExecutorConfig, RetryPolicy
```

### Creating DAGs with Direct Model Instantiation

Models can be created directly using Pydantic constructors:

```python
from pydagu.models import Dag, Step, HTTPExecutorConfig, ExecutorConfig, RetryPolicy

dag = Dag(
    name="example-dag",
    description="An example DAG",
    schedule="0 2 * * *",  # Run daily at 2 AM
    tags=["production", "etl"],
    steps=[
        Step(
            name="echo-step",
            command="echo 'Hello, Dagu!'",
        ),
        Step(
            name="http-step",
            command="POST https://api.example.com/webhook",
            executor=ExecutorConfig(
                type="http",
                config=HTTPExecutorConfig(
                    headers={"Content-Type": "application/json"},
                    body='{"key": "value"}',
                    timeout=30,
                ),
            ),
            retryPolicy=RetryPolicy(limit=3, intervalSec=5),
            depends="echo-step",
        ),
    ],
)
```

### Creating DAGs with the Builder Interface

Or by using the fluent Builder interface for a more ergonomic experience:

```python
from pydagu.builder import DagBuilder, StepBuilder

dag = (
    DagBuilder("example-dag")
    .description("An example DAG")
    .schedule("0 2 * * *")  # Run daily at 2 AM
    .tags("production", "etl")
    .add_step("echo-step", "echo 'Hello, Dagu!'")
    .add_step_models(
        StepBuilder("http-step")
        .command("POST https://api.example.com/webhook")
        .http_executor(
            headers={"Content-Type": "application/json"},
            body={"key": "value"},  # Automatically serialized to JSON
            timeout=30,
        )
        .retry(limit=3, interval=5)
        .depends_on("echo-step")
        .build()
    )
    .build()
)
```

### Available Models

#### Core Models

- **`Dag`**: Main DAG definition with steps, schedule, and configuration
- **`Step`**: Individual step in a DAG workflow
- **`Precondition`**: Conditions that must be met before DAG/step execution

#### Step Configuration

- **`RetryPolicy`**: Retry configuration with limit and interval
- **`ContinueOn`**: Control workflow continuation on failure/skip
- **`ParallelConfig`**: Configuration for parallel step execution

#### Executors

- **`ExecutorConfig`**: Base executor configuration
- **`HTTPExecutorConfig`**: HTTP request executor with headers, body, timeout
- **`SSHExecutorConfig`**: SSH remote execution
- **`MailExecutorConfig`**: Send email notifications
- **`DockerExecutorConfig`**: Run steps in Docker containers
- **`JQExecutorConfig`**: JSON processing with jq
- **`ShellExecutorConfig`**: Shell execution with custom interpreters

#### Handlers and Notifications

- **`HandlerConfig`**: Event handler configuration
- **`HandlerOn`**: Handlers for success, failure, cancel, exit events
- **`MailOn`**: Email notification triggers
- **`SMTPConfig`**: SMTP server configuration

#### Infrastructure

- **`ContainerConfig`**: Docker container settings
- **`SSHConfig`**: SSH connection configuration
- **`LogConfig`**: Logging configuration

#### API Request/Response

- **`StartDagRun`**: Request to start a DAG run
- **`DagRunId`**: Response containing the DAG run ID
- **`DagResponseMessage`**: Error/status messages from the API
- **`DagRunResult`**: Complete DAG run status and results

## HTTP Client

The `DaguHttpClient` class provides methods for interacting with the Dagu HTTP API.

### Initialization

```python
from pydagu.http import DaguHttpClient

client = DaguHttpClient(
    dag_name="my-dag",
    url_root="http://localhost:8080/api/v2"
)
```

### Methods

#### `get_dag_spec() -> Dag`

Fetch a DAG specification from the Dagu server.

```python
dag = client.get_dag_spec()
print(f"DAG: {dag.name}, Steps: {len(dag.steps)}")
```

#### `post_dag(dag: Dag) -> None | DagResponseMessage`

Create a new DAG on the Dagu server. Returns `None` on success, or a `DagResponseMessage` with error details on failure (status 400 or 409).

```python
from pydagu.builder import DagBuilder

dag = DagBuilder("my-dag").add_step("step1", "echo 'Hello'").build()
response = client.post_dag(dag)

if response is None:
    print("DAG created successfully")
else:
    print(f"Error: {response.message}")
```

#### `update_dag(dag: Dag) -> None | DagResponseMessage`

Update an existing DAG on the Dagu server. Returns `None` on success, or a `DagResponseMessage` with error details on failure (status 400 or 409).

```python
# Modify the DAG
dag.description = "Updated description"
dag.steps.append(Step(name="new-step", command="echo 'New step'"))

response = client.update_dag(dag)
if response is None:
    print("DAG updated successfully")
```

#### `delete_dag() -> None`

Delete the DAG from the Dagu server.

```python
client.delete_dag()
print("DAG deleted")
```

#### `start_dag_run(start_request: StartDagRun) -> DagRunId | DagResponseMessage`

Start a DAG run. Returns a `DagRunId` on success, or a `DagResponseMessage` if the DAG is already running (when using singleton mode).

```python
from pydagu.models import StartDagRun

request = StartDagRun(dagName="my-dag", params={"ENV": "production"})
result = client.start_dag_run(request)

if isinstance(result, DagRunId):
    print(f"Started DAG run: {result.dagRunId}")
else:
    print(f"Could not start: {result.message}")
```

#### `get_dag_run_status(dag_run_id: str) -> DagRunResult`

Get the status of a DAG run. Use `"latest"` as the `dag_run_id` to fetch the most recent run.

```python
# Get specific run
status = client.get_dag_run_status("20240101-120000")
print(f"Status: {status.statusLabel}")

# Get latest run
latest = client.get_dag_run_status("latest")
print(f"Latest run status: {latest.statusLabel}")
for node in latest.nodes:
    print(f"  Step {node.step.name}: {node.statusLabel}")
```

## Builder API

### DagBuilder

The `DagBuilder` class provides a fluent interface for constructing DAGs.

#### Core Methods

- **`.description(desc: str)`**: Set DAG description
- **`.schedule(cron: str)`**: Set cron schedule (e.g., `"0 2 * * *"`)
- **`.add_tag(tag: str)`**: Add a single tag
- **`.tags(*tags: str)`**: Set multiple tags at once
- **`.max_active_runs(limit: int)`**: Set max concurrent runs
- **`.max_active_steps(limit: int)`**: Set max concurrent steps
- **`.timeout(seconds: int)`**: Set execution timeout
- **`.history_retention(days: int)`**: Set history retention period
- **`.delay(seconds: int)`**: Add delay before execution

#### Parameter and Environment Methods

- **`.add_param(name: str, value: str)`**: Add a parameter
- **`.add_env(name: str, value: str)`**: Add environment variable
- **`.add_dotenv(path: str)`**: Add .env file path

#### Step Methods

- **`.add_step(name: str, command: str, **kwargs)`\*\*: Add a simple step
- **`.add_simple_step(command_or_script: str)`**: Add minimal step
- **`.add_step_models(*steps: Step)`**: Add pre-built Step objects

#### Handler Methods

- **`.on_success(command: str, **kwargs)`\*\*: Add success handler
- **`.on_failure(command: str, **kwargs)`\*\*: Add failure handler
- **`.on_cancel(command: str, **kwargs)`\*\*: Add cancel handler
- **`.on_exit(command: str, **kwargs)`\*\*: Add exit handler

#### Build Method

- **`.build() -> Dag`**: Build and return the final DAG

### StepBuilder

The `StepBuilder` class provides a fluent interface for constructing steps.

#### Core Methods

- **`.command(cmd: str)`**: Set step command
- **`.script(path: str)`**: Set script path
- **`.description(desc: str)`**: Set step description
- **`.output(var: str)`**: Capture output to variable
- **`.directory(path: str)`**: Set working directory
- **`.depends_on(*deps: str)`**: Set dependencies

#### Executor Methods

- **`.http_executor(**kwargs)`\*\*: Configure HTTP executor
- **`.ssh_executor(**kwargs)`\*\*: Configure SSH executor
- **`.docker_executor(**kwargs)`\*\*: Configure Docker executor
- **`.mail_executor(**kwargs)`\*\*: Configure mail executor
- **`.jq_executor(**kwargs)`\*\*: Configure jq executor

#### Control Flow Methods

- **`.retry(limit: int, interval: int)`**: Set retry policy
- **`.repeat(enabled: bool, interval: int)`**: Set repeat configuration
- **`.continue_on_failure(enabled: bool)`**: Continue on failure
- **`.preconditions(*conditions)`**: Add preconditions
- **`.mail_on_error(enabled: bool)`**: Enable email on error
- **`.signal_on_stop(signal: str)`**: Set signal for stop

#### Build Method

- **`.build() -> Step`**: Build and return the final Step

## Complete Example

```python
from pydagu.http import DaguHttpClient
from pydagu.builder import DagBuilder, StepBuilder
from pydagu.models import StartDagRun

# Initialize client
client = DaguHttpClient(
    dag_name="etl-pipeline",
    url_root="http://localhost:8080/api/v2"
)

# Build a DAG
dag = (
    DagBuilder("etl-pipeline")
    .description("Daily ETL pipeline")
    .schedule("0 2 * * *")
    .tags("production", "etl")
    .max_active_runs(1)
    .add_param("DATE", "`date +%Y-%m-%d`")
    .add_step_models(
        StepBuilder("extract")
        .command("python extract.py")
        .output("EXTRACT_RESULT")
        .retry(limit=3, interval=30)
        .build(),

        StepBuilder("transform")
        .command("python transform.py")
        .depends_on("extract")
        .retry(limit=2, interval=60)
        .build(),

        StepBuilder("notify")
        .command("POST https://api.slack.com/webhook")
        .http_executor(
            headers={"Content-Type": "application/json"},
            body={"text": "ETL completed for ${DATE}"},
            timeout=10
        )
        .depends_on("transform")
        .build()
    )
    .on_failure(command="python alert_failure.py")
    .build()
)

# Create the DAG
response = client.post_dag(dag)
if response is None:
    print("DAG created successfully")

    # Start a run
    run_result = client.start_dag_run(StartDagRun(dagName="etl-pipeline"))
    if hasattr(run_result, 'dagRunId'):
        print(f"Started run: {run_result.dagRunId}")

        # Check status
        status = client.get_dag_run_status(run_result.dagRunId)
        print(f"Status: {status.statusLabel}")
else:
    print(f"Error creating DAG: {response.message}")
```

## Type Hints

All PyDagu code is fully typed with Python type hints and validated with mypy in strict mode. This provides excellent IDE support and catches many errors at development time.

```python
from pydagu.http import DaguHttpClient
from pydagu.models import Dag, DagRunId

client: DaguHttpClient = DaguHttpClient("my-dag", "http://localhost:8080/api/v2")
dag: Dag = client.get_dag_spec()
run_id: DagRunId | None = None  # Type-safe
```
