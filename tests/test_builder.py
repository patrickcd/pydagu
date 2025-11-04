"""Tests for DagBuilder and StepBuilder using examples"""

from pydagu.builder import DagBuilder, StepBuilder
from pydagu.models import Dag, Step


# DagBuilder Tests
def test_simple_dag():
    """Create a simple DAG with basic configuration"""
    dag = (
        DagBuilder("simple-etl")
        .description("Simple ETL pipeline")
        .schedule("0 2 * * *")
        .add_tag("production")
        .add_tag("etl")
        .add_step(command="python extract.py", name="extract")
        .add_step(command="python transform.py", name="transform", depends="extract")
        .add_step(command="python load.py", depends="transform", name="load")
        .build()
    )

    assert isinstance(dag, Dag)
    assert dag.name == "simple-etl"
    assert dag.description == "Simple ETL pipeline"
    assert dag.schedule == "0 2 * * *"
    assert dag.tags == ["production", "etl"]
    assert len(dag.steps) == 3


def test_complex_dag():
    """Create a complex DAG with advanced features"""
    dag = (
        DagBuilder("production-etl")
        .description("Daily ETL pipeline for production data")
        .schedule("0 2 * * *")
        .tags("production", "etl", "critical")
        .max_active_runs(1)
        .max_active_steps(5)
        .timeout(7200)
        .history_retention(90)
        # Parameters and environment
        .add_param("DATE", "`date +%Y-%m-%d`")
        .add_param("ENVIRONMENT", "production")
        .add_env("DATA_DIR", "/data/etl")
        .add_env("LOG_LEVEL", "info")
        .dotenv("/etc/dagu/production.env")
        # Container configuration
        .container(
            image="python:3.11-slim",
            pull_policy="missing",
            env=["PYTHONUNBUFFERED=1"],
            volumes=["./data:/data", "./scripts:/scripts:ro"],
        )
        # Preconditions
        .add_precondition(condition="`date +%u`", expected="re:[1-5]")
        # Steps
        .add_step(name="validate", command="python validate_env.py")
        .add_step(
            name="extract",
            command="python extract.py --date=${DATE}",
            depends="validate",
            output="RAW_DATA_PATH",
        )
        .add_simple_step(
            "python transform.py ${RAW_DATA_PATH}",
        )
        # Handlers
        .on_success(command="./scripts/notify-success.sh")
        .on_failure(command="./scripts/notify-failure.sh")
        .on_exit(command="./scripts/cleanup.sh ${DATE}")
        # Notifications
        .mail_on_failure()
        .smtp_config(
            host="smtp.company.com",
            port="587",
            username="etl-notifications@company.com",
        )
        .build()
    )

    assert isinstance(dag, Dag)
    assert dag.name == "production-etl"
    assert dag.description == "Daily ETL pipeline for production data"
    assert dag.tags == ["production", "etl", "critical"]
    assert dag.maxActiveRuns == 1
    assert dag.maxActiveSteps == 5
    assert dag.timeoutSec == 7200
    assert dag.histRetentionDays == 90
    assert len(dag.steps) == 3
    assert dag.container is not None
    assert dag.container.image == "python:3.11-slim"
    assert dag.handlerOn is not None
    assert dag.handlerOn.success is not None
    assert dag.handlerOn.failure is not None
    assert dag.handlerOn.exit is not None
    assert dag.mailOn is not None
    assert dag.mailOn.failure is True
    assert dag.smtp is not None
    assert dag.smtp.host == "smtp.company.com"


def test_export_to_yaml():
    """Test exporting DAG to YAML"""
    builder = (
        DagBuilder("export-example")
        .description("Example DAG for YAML export")
        .schedule("0 * * * *")
        .add_tag("example")
        .add_step(command="echo 'Hello World'", name="step-1")
        .add_step(command="echo 'Goodbye'", depends="step-1")
    )

    yaml_output = builder.to_yaml()
    assert isinstance(yaml_output, str)
    assert "name: export-example" in yaml_output
    assert "schedule: 0 * * * *" in yaml_output
    assert "tags:" in yaml_output
    assert "example" in yaml_output

    dag = builder.build()
    assert dag.name == "export-example"


def test_to_dict():
    """Test exporting DAG to dictionary"""
    builder = (
        DagBuilder("dict-example")
        .description("Test dictionary export")
        .add_tag("test")
        .add_simple_step("echo 'test'")
    )

    dag_dict = builder.to_dict()
    assert isinstance(dag_dict, dict)
    assert dag_dict["name"] == "dict-example"
    assert dag_dict["description"] == "Test dictionary export"
    assert "test" in dag_dict["tags"]


def test_ssh_and_mail_config():
    """Test SSH and email configurations"""
    dag = (
        DagBuilder("remote-execution")
        .description("DAG with remote execution via SSH")
        .schedule("0 4 * * *")
        .ssh_config(
            user="deploy",
            host="production.example.com",
            port=22,
            key="~/.ssh/deploy_key",
        )
        .mail_on_failure()
        .mail_on_success(False)
        .smtp_config(
            host="smtp.gmail.com",
            port="587",
            username="notifications@example.com",
        )
        .add_simple_step("python remote_task.py")
        .build()
    )

    assert dag.name == "remote-execution"
    assert dag.ssh is not None
    assert dag.ssh.user == "deploy"
    assert dag.ssh.host == "production.example.com"
    assert dag.ssh.port == 22
    assert dag.smtp is not None
    assert dag.smtp.host == "smtp.gmail.com"
    assert dag.smtp.port == "587"
    assert dag.mailOn is not None
    assert dag.mailOn.failure is True
    assert dag.mailOn.success is False


def test_container_config():
    """Test container configuration"""
    dag = (
        DagBuilder("container-dag")
        .container(
            image="python:3.11-slim",
            pull_policy="always",
            env=["DEBUG=1", "LOG_LEVEL=info"],
            volumes=["./data:/data:ro"],
        )
        .add_simple_step("python script.py")
        .build()
    )

    assert dag.container is not None
    assert dag.container.image == "python:3.11-slim"
    assert dag.container.pullPolicy == "always"
    assert dag.container.env == ["DEBUG=1", "LOG_LEVEL=info"]
    assert dag.container.volumes == ["./data:/data:ro"]


def test_preconditions():
    """Test adding preconditions"""
    dag = (
        DagBuilder("precondition-dag")
        .add_precondition(condition="`date +%u`", expected="re:[1-5]")
        .add_precondition(condition="test -f /data/ready", expected="0")
        .add_simple_step("process.sh")
        .build()
    )

    assert dag.preconditions is not None
    assert len(dag.preconditions) == 2
    assert dag.preconditions[0].condition == "`date +%u`"
    assert dag.preconditions[0].expected == "re:[1-5]"


# StepBuilder Tests
def test_simple_step_with_retry():
    """Create a simple step with retry policy"""
    step = (
        StepBuilder("extract-data")
        .command("python extract.py --date=${DATE}")
        .description("Extract data from source database")
        .retry(limit=3, interval=300)
        .output("RAW_DATA_PATH")
        .build()
    )

    assert isinstance(step, Step)
    assert step.name == "extract-data"
    assert step.command == "python extract.py --date=${DATE}"
    assert step.description == "Extract data from source database"
    assert step.retryPolicy is not None
    assert step.retryPolicy.limit == 3
    assert step.retryPolicy.intervalSec == 300
    assert step.output == "RAW_DATA_PATH"


def test_step_with_docker_executor():
    """Create a step with Docker executor"""
    step = (
        StepBuilder("transform-data")
        .command("python transform.py ${RAW_DATA_PATH}")
        .depends_on("extract-data")
        .docker_executor(
            image="python:3.11-slim",
            env={"PYTHONUNBUFFERED": "1"},
            volumes=["./data:/data"],
        )
        .retry(limit=2, interval=60)
        .build()
    )

    assert step.name == "transform-data"
    assert step.depends == "extract-data"
    assert step.executor is not None
    assert step.executor.type == "docker"
    assert step.executor.config is not None


def test_step_with_parallel_execution():
    """Create a step with parallel execution"""
    step = (
        StepBuilder("process-parallel")
        .command("python process.py --type=${ITEM}")
        .depends_on("transform-data")
        .parallel(items=["customers", "orders", "products"], max_concurrent=2)
        .continue_on_failure(False)
        .build()
    )

    assert step.name == "process-parallel"
    assert step.parallel is not None
    assert step.parallel.items == ["customers", "orders", "products"]
    assert step.parallel.maxConcurrent == 2
    assert step.continueOn is not None
    assert step.continueOn.failure is False


def test_step_with_http_executor():
    """Create a step with HTTP executor"""
    step = (
        StepBuilder("notify-webhook")
        .command("POST https://api.example.com/notify")
        .http_executor(
            headers={"Authorization": "Bearer ${API_TOKEN}"},
            body={"status": "completed", "date": "${DATE}"},
            timeout=30,
        )
        .build()
    )

    assert step.name == "notify-webhook"
    assert step.executor is not None
    assert step.executor.type == "http"
    assert step.executor.config is not None


def test_step_with_ssh_executor():
    """Create a step with SSH executor"""
    step = (
        StepBuilder("remote-backup")
        .command("./backup.sh")
        .ssh_executor(
            user="deploy",
            host="backup.example.com",
            key="~/.ssh/backup_key",
        )
        .retry(limit=3, interval=120)
        .mail_on_error()
        .build()
    )

    assert step.name == "remote-backup"
    assert step.executor is not None
    assert step.executor.type == "ssh"
    assert step.mailOnError is True
    assert step.retryPolicy is not None


def test_step_with_mail_executor():
    """Create a step with mail executor"""
    step = (
        StepBuilder("send-notification")
        .mail_executor(
            to=["admin@example.com", "alerts@example.com"],
            subject="Pipeline Completed",
            body="The ETL pipeline has completed successfully.",
        )
        .command("echo 'Notification sent'")
        .build()
    )

    assert step.name == "send-notification"
    assert step.executor is not None
    assert step.executor.type == "mail"


def test_step_with_shell_executor():
    """Create a step with shell executor"""
    step = (
        StepBuilder("run-script")
        .script("./process.sh")
        .shell_executor(
            shell="bash",
            env={"PATH": "/usr/local/bin:$PATH", "DEBUG": "1"},  # nosec: B604
        )
        .build()
    )

    assert step.name == "run-script"
    assert step.script == "./process.sh"
    assert step.executor is not None
    assert step.executor.type == "shell"


def test_step_with_jq_executor():
    """Create a step with jq executor"""
    step = (
        StepBuilder("parse-json")
        .jq_executor(
            query=".data[] | select(.active)",
            raw=True,
            compact=False,
        )
        .command("`.name`")
        .build()
    )

    assert step.name == "parse-json"
    assert step.executor is not None
    assert step.executor.type == "jq"


def test_step_with_multiple_dependencies():
    """Create a step with multiple dependencies"""
    step = (
        StepBuilder("aggregate")
        .command("python aggregate.py")
        .depends_on("extract", "transform", "validate")
        .build()
    )

    assert step.name == "aggregate"
    assert step.depends == ["extract", "transform", "validate"]


def test_step_with_params():
    """Create a step with parameters"""
    step = (
        StepBuilder("parameterized")
        .command("python process.py")
        .params("--verbose", "--config=prod", "--date=${DATE}")
        .build()
    )

    assert step.name == "parameterized"
    assert step.params == ["--verbose", "--config=prod", "--date=${DATE}"]


def test_step_with_working_dir():
    """Create a step with working directory"""
    step = (
        StepBuilder("build-project")
        .command("make build")
        .working_dir("/app/src")
        .build()
    )

    assert step.name == "build-project"
    assert step.dir == "/app/src"


def test_step_with_precondition():
    """Create a step with preconditions"""
    step = (
        StepBuilder("conditional-step")
        .command("python process.py")
        .add_precondition(condition="test -f /data/input.csv", expected="0")
        .build()
    )

    assert step.name == "conditional-step"
    assert step.preconditions is not None
    assert len(step.preconditions) == 1
    assert step.preconditions[0].condition == "test -f /data/input.csv"


def test_dag_with_prebuilt_steps():
    """Build a DAG using pre-built steps from StepBuilder"""
    extract_step = (
        StepBuilder("extract-data")
        .command("python extract.py --date=${DATE}")
        .retry(limit=3, interval=300)
        .output("RAW_DATA_PATH")
        .build()
    )

    transform_step = (
        StepBuilder("transform-data")
        .command("python transform.py ${RAW_DATA_PATH}")
        .depends_on("extract-data")
        .docker_executor(image="python:3.11-slim")
        .build()
    )

    dag = (
        DagBuilder("advanced-pipeline")
        .description("Pipeline with advanced step configurations")
        .schedule("0 3 * * *")
        .add_tag("advanced")
        .add_step_models(extract_step, transform_step)
        .build()
    )

    assert len(dag.steps) == 2
    assert all(isinstance(step, Step) for step in dag.steps)
    assert dag.steps[0].name == "extract-data"
    assert dag.steps[1].name == "transform-data"


def test_save_to_file(tmp_path):
    """Test saving DAG to YAML file"""
    output_file = tmp_path / "test_dag.yaml"

    builder = (
        DagBuilder("test-save")
        .description("Test saving to file")
        .add_simple_step("echo 'test'")
    )

    builder.save(str(output_file))

    assert output_file.exists()
    content = output_file.read_text()
    assert "name: test-save" in content
    assert "description: Test saving to file" in content
