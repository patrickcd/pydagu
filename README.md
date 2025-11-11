# pydagu

[![PyPI version](https://badge.fury.io/py/pydagu.svg)](https://badge.fury.io/py/pydagu)
[![Tests](https://github.com/yourusername/pydagu/actions/workflows/test.yml/badge.svg)](https://github.com/yourusername/pydagu/actions/workflows/test.yml)
[![Python Versions](https://img.shields.io/pypi/pyversions/pydagu.svg)](https://pypi.org/project/pydagu/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python client library for [Dagu](https://github.com/dagu-org/dagu) - providing type-safe DAG creation and HTTP API interaction with Pydantic validation.

## Features

- 🎯 **Type-safe**: Built with Pydantic models for full type safety and validation
- 🏗️ **Builder Pattern**: Fluent API for constructing DAGs and steps
- 🔌 **HTTP Client**: Complete client for Dagu's HTTP API
- 🔄 **Webhook Support**: Built-in patterns for webhook integration
- ✅ **Well-tested**: Comprehensive test suite with 95%+ coverage
- 📝 **Examples**: Production-ready integration examples

## Installation

```bash
pip install pydagu
```

## Prerequisites

You need a running [Dagu server](https://github.com/dagu-org/dagu) to run the tests. Install Dagu:

```bash
# macOS
brew install dagu-org/brew/dagu

# Linux
curl -L https://github.com/dagu-org/dagu/releases/latest/download/dagu_linux_amd64.tar.gz | tar xz
sudo mv dagu /usr/local/bin/

# Start the server
dagu server
```

## Quick Start

### Create and Run a Simple DAG

```python
from pydagu.builder import DagBuilder, StepBuilder
from pydagu.http import DaguHttpClient
from pydagu.models.request import StartDagRun

# Initialize client
client = DaguHttpClient(
    dag_name="my-first-dag",
    url_root="http://localhost:8080/api/v2/"
)

# Build a DAG
dag = (
    DagBuilder("my-first-dag")
    .description("My first DAG with pydagu")
    .add_step_models(
        StepBuilder("hello-world")
        .command("echo 'Hello from pydagu!'")
        .build()
    )
    .build()
)

# Post the DAG to Dagu
client.post_dag(dag)

# Start a run
dag_run_id = client.start_dag_run(StartDagRun(dagName=dag.name))

# Check status
status = client.get_dag_run_status(dag_run_id.dagRunId)
print(f"Status: {status.statusLabel}")
```

### HTTP Executor with Retry

```python
from pydagu.builder import StepBuilder

step = (
    StepBuilder("api-call")
    .command("POST https://api.example.com/webhook")
    .http_executor(
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer ${API_TOKEN}"
        },
        body={"event": "user.created", "user_id": "123"},
        timeout=30
    )
    .retry(limit=3, interval=5)
    .build()
)
```

### Chained Steps with Dependencies

```python
from pydagu.builder import DagBuilder, StepBuilder

dag = (
    DagBuilder("data-pipeline")
    .add_step_models(
        StepBuilder("extract")
        .command("python extract_data.py")
        .output("EXTRACTED_FILE")
        .build(),

        StepBuilder("transform")
        .command("python transform_data.py ${EXTRACTED_FILE}")
        .depends_on("extract")
        .output("TRANSFORMED_FILE")
        .build(),

        StepBuilder("load")
        .command("python load_data.py ${TRANSFORMED_FILE}")
        .depends_on("transform")
        .build()
    )
    .build()
)
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/pydagu.git
cd pydagu

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests (requires Dagu server running)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=pydagu --cov-report=html
```

## Documentation

- [PyDagu Reference](https://github.com/patrickcd/pydagu/blob/main/docs/reference.md)
- [Dagu Documentation](https://docs.dagu.cloud/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Related Projects

- [Dagu](https://github.com/dagu-org/dagu) - The underlying DAG execution engine
- [Airflow](https://airflow.apache.org/) - Alternative workflow orchestration platform
