# Tests

This directory contains the test suite for pydagu.

## Test Structure

- `test_models.py` - Tests for Pydantic model validation
- `test_builder.py` - Tests for DagBuilder and StepBuilder fluent APIs
- `test_schemathesis.py` - Schemathesis-based generative tests with API validation
- `conftest.py` - Pytest fixtures and configuration
- `generated_dags/` - Directory for generated DAG YAML files (created during tests)

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test modules
```bash
pytest tests/test_models.py
pytest tests/test_builder.py
pytest tests/test_schemathesis.py
```

### Run with verbose output
```bash
pytest -v
```

### Skip slow tests
```bash
pytest -m "not slow"
```

### Run only integration tests
```bash
pytest -m integration
```

## Schemathesis Tests

The `test_schemathesis.py` module generates random DAG configurations and validates them against the Dagu API.

### Features:
- **Generates 10 DAG configurations** (configurable via `MAX_EXAMPLES`)
- **Validates against API**: Posts to `https://re.postrfp.com/dagu/api/v2/dags/validate`
- **Saves DAGs to disk**: All generated DAGs are saved to `tests/generated_dags/`
- **Failure debugging**: Failed DAGs are saved with `_failed` suffix

### Running Schemathesis tests:
```bash
# Run generative tests
pytest tests/test_schemathesis.py

# Run with specific number of examples (via pytest parametrize)
pytest tests/test_schemathesis.py::test_generated_dag_validation

# Run specific configuration tests
pytest tests/test_schemathesis.py::test_specific_dag_configurations

# Test API connectivity first
pytest tests/test_schemathesis.py::test_api_connectivity
```

### Output:
Generated DAG files will be in `tests/generated_dags/`:
- `dag_000.yaml`, `dag_001.yaml`, etc. - Successfully validated DAGs
- `dag_000_failed.yaml` - DAGs that failed validation (for debugging)
- `specific_minimal.yaml`, etc. - Specific test configurations

### Customization:
Edit `test_schemathesis.py` to:
- Change `MAX_EXAMPLES` constant to generate more/fewer DAGs
- Modify `VALIDATION_API_URL` to point to different endpoint
- Add custom DAG configurations to `dag_configs` list
- Implement Hypothesis-based random generation

## Dependencies

Core testing dependencies:
```bash
pip install pytest pytest-cov
```

For Schemathesis tests:
```bash
pip install httpx pyyaml hypothesis
```

For future Hypothesis-based generation:
```bash
pip install hypothesis-jsonschema
```

## Test Coverage

Generate coverage report:
```bash
pytest --cov=pydagu --cov-report=html
```

View report:
```bash
open htmlcov/index.html
```
