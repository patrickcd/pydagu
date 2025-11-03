"""Tests for DAG validation using dagu CLI

This module contains tests that validate DAG configurations using the
local dagu CLI tool.
"""

import json
import subprocess
from pathlib import Path
import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from pydagu.models import Dag


# Test configuration
MAX_EXAMPLES = 5
OUTPUT_DIR = Path(__file__).parent / "generated_dags"


# Hypothesis strategies for generating valid cron expressions
@st.composite
def cron_field(draw, min_val, max_val, allow_names=None):
    """Generate a valid cron field value

    Args:
        draw: Hypothesis draw function
        min_val: Minimum numeric value
        max_val: Maximum numeric value
        allow_names: Optional list of named values (e.g., ['MON', 'TUE'])
    """
    choices = [
        st.just("*"),  # Any value
        st.integers(min_value=min_val, max_value=max_val).map(str),  # Single value
    ]

    # Range: start-end
    @st.composite
    def range_value(draw):
        start = draw(st.integers(min_value=min_val, max_value=max_val))
        end = draw(st.integers(min_value=start, max_value=max_val))
        return f"{start}-{end}"

    choices.append(range_value())

    # Step: */step or start-end/step
    @st.composite
    def step_value(draw):
        base = draw(st.sampled_from(["*", "range"]))
        if base == "*":
            step = draw(
                st.integers(min_value=1, max_value=max(1, (max_val - min_val) // 2))
            )
            return f"*/{step}"
        else:
            # For ranges with steps, ensure step is reasonable
            start = draw(st.integers(min_value=min_val, max_value=max_val))
            end = draw(st.integers(min_value=start, max_value=max_val))
            range_size = end - start
            if range_size > 0:
                step = draw(st.integers(min_value=1, max_value=max(1, range_size)))
                return f"{start}-{end}/{step}"
            else:
                return f"{start}"

    choices.append(step_value())

    # List: val1,val2,val3
    @st.composite
    def list_value(draw):
        values = draw(
            st.lists(
                st.integers(min_value=min_val, max_value=max_val),
                min_size=2,
                max_size=5,
                unique=True,
            )
        )
        return ",".join(map(str, sorted(values)))

    choices.append(list_value())

    # Named values (for month/weekday)
    if allow_names:
        choices.append(st.sampled_from(allow_names))

        # Named range
        @st.composite
        def named_range(draw):
            names = draw(
                st.lists(
                    st.sampled_from(allow_names), min_size=2, max_size=2, unique=True
                )
            )
            return f"{names[0]}-{names[1]}"

        choices.append(named_range())

    return draw(st.one_of(*choices))


@st.composite
def cron_expression(draw, include_year=False):
    """Generate a valid cron expression

    Format: minute hour day month weekday [year]

    Args:
        draw: Hypothesis draw function
        include_year: Whether to include optional year field
    """
    minute = draw(cron_field(0, 59))
    hour = draw(cron_field(0, 23))
    day = draw(cron_field(1, 31))
    month = draw(
        cron_field(
            1,
            12,
            allow_names=[
                "JAN",
                "FEB",
                "MAR",
                "APR",
                "MAY",
                "JUN",
                "JUL",
                "AUG",
                "SEP",
                "OCT",
                "NOV",
                "DEC",
            ],
        )
    )
    weekday = draw(
        cron_field(0, 6, allow_names=["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"])
    )

    parts = [minute, hour, day, month, weekday]

    if include_year and draw(st.booleans()):
        year = draw(cron_field(2020, 2030))
        parts.append(year)

    return " ".join(parts)


@pytest.fixture(scope="module", autouse=True)
def setup_output_dir():
    """Create output directory for generated DAG files"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    yield


@pytest.fixture
def yaml_file():
    """Fixture that provides a file path and cleans it up after the test"""
    files_to_cleanup = []

    def _create_file(dag: Dag, index: int, suffix: str = "") -> Path:
        """Save a DAG to a YAML file for reference

        Args:
            dag: The DAG model to save
            index: Test iteration index
            suffix: Optional suffix for the filename (e.g., "failed")

        Returns:
            Path to the saved file
        """
        filename = f"dag_{index:03d}{suffix}.yaml"
        filepath = OUTPUT_DIR / filename

        dag_dict = dag.model_dump(exclude_none=True)
        with open(filepath, "w") as f:
            yaml.dump(dag_dict, f, default_flow_style=False, sort_keys=False)

        files_to_cleanup.append(filepath)
        return filepath

    yield _create_file

    # Cleanup after test
    for filepath in files_to_cleanup:
        if filepath.exists():
            filepath.unlink()


def validate_dag_with_dagu(filepath: Path) -> tuple[bool, str]:
    """Validate a DAG using the local dagu CLI

    Args:
        filepath: Path to the YAML file to validate

    Returns:
        Tuple of (is_valid, message)
    """
    try:
        result = subprocess.run(
            ["dagu", "validate", str(filepath)],
            capture_output=True,
            text=True,
            timeout=10.0,
        )

        # dagu validate returns 0 on success
        if result.returncode == 0:
            return True, "Valid"
        else:
            # Return the error message from stderr or stdout
            error_msg = result.stderr.strip() or result.stdout.strip()
            return False, error_msg

    except subprocess.TimeoutExpired:
        return False, "Validation timed out"
    except FileNotFoundError:
        return False, "dagu command not found. Make sure dagu is installed and in PATH."
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


@pytest.mark.parametrize("iteration", range(MAX_EXAMPLES))
def test_generated_dag_validation(iteration, yaml_file):
    """Generate a random DAG and validate it via dagu CLI

    This test uses the Pydantic model's examples to generate random but valid
    DAG configurations, then validates them using dagu validate.
    """
    # Generate a DAG using model_validate with example data
    # In a real scenario, you'd use Schemathesis or Hypothesis here
    # For now, we'll create variations based on the examples

    dag_configs = [
        {
            "name": f"generated-dag-{iteration}",
            "description": f"Auto-generated DAG for testing iteration {iteration}",
            "schedule": ["0 2 * * *", "*/5 * * * *", "0 0 1 * *", None][iteration % 4],
            "tags": [["test", "generated"], ["production"], None][iteration % 3],
            "steps": [f"echo 'Step {i}'" for i in range((iteration % 3) + 1)],
            "maxActiveRuns": [1, 2, 3, None][iteration % 4],
            "timeoutSec": [3600, 7200, None][iteration % 3],
        },
        {
            "name": f"pipeline-{iteration}",
            "description": "ETL pipeline",
            "schedule": "0 3 * * *",
            "tags": ["etl", "automated"],
            "steps": [
                "python extract.py",
                "python transform.py",
                "python load.py",
            ],
            "maxActiveRuns": 1,
            "maxActiveSteps": 3,
        },
        {
            "name": f"simple-{iteration}",
            "steps": ["echo 'Hello World'"],
        },
    ]

    config = dag_configs[iteration % len(dag_configs)]

    # Customize config with iteration-specific values
    config["name"] = f"{config['name']}-{iteration}"

    # Create DAG model (this validates the structure)
    try:
        dag = Dag(**config)
    except Exception as e:
        pytest.fail(
            f"Failed to create DAG model: {e}\nConfig: {json.dumps(config, indent=2)}"
        )

    # Save the generated DAG
    saved_path = yaml_file(dag, iteration)
    print(f"\nGenerated DAG saved to: {saved_path}")

    # Validate using dagu CLI
    is_valid, message = validate_dag_with_dagu(saved_path)

    if not is_valid:
        # Save a copy with "failed" suffix for easier debugging
        failed_path = yaml_file(dag, iteration, suffix="_failed")
        pytest.fail(
            f"DAG validation failed with dagu CLI\n"
            f"Message: {message}\n"
            f"DAG saved to: {failed_path}\n"
            f"DAG content:\n{yaml.dump(dag.model_dump(exclude_none=True), default_flow_style=False)}"
        )

    print("✓ DAG validated successfully with dagu")


def test_dagu_cli_available():
    """Test that the dagu CLI is accessible"""
    try:
        result = subprocess.run(
            ["dagu", "version"], capture_output=True, text=True, timeout=5.0
        )

        # Just check that dagu command runs
        assert (
            result.returncode == 0
            or "dagu" in result.stdout.lower()
            or "dagu" in result.stderr.lower()
        ), "dagu command exists but may not be working correctly"

        print("\n✓ dagu CLI is available")
        if result.stdout.strip():
            print(f"  Version output: {result.stdout.strip()}")

    except FileNotFoundError:
        pytest.fail("dagu command not found. Make sure dagu is installed and in PATH.")
    except subprocess.TimeoutExpired:
        pytest.fail("dagu command timed out")
    except Exception as e:
        pytest.fail(f"Unexpected error testing dagu CLI: {e}")


@given(cron=cron_expression())
@settings(max_examples=20, deadline=None)
def test_cron_expression_generator(cron):
    """Test that our cron expression generator creates valid expressions"""
    print(f"\nGenerated cron: {cron}")

    # Create a minimal DAG with this schedule
    try:
        dag = Dag(name="cron-test", schedule=cron, steps=["echo 'test'"])
    except Exception as e:
        pytest.fail(f"Generated cron expression failed validation: {cron}\nError: {e}")

    # Verify the cron passed validation
    assert dag.schedule == cron
    print(f"✓ Valid cron expression: {cron}")


@pytest.mark.parametrize(
    "dag_name,dag_config",
    [
        ("minimal", {"name": "minimal-test", "steps": ["echo 'test'"]}),
        (
            "with-schedule",
            {
                "name": "scheduled-test",
                "schedule": "0 2 * * *",
                "steps": ["python script.py"],
            },
        ),
        (
            "with-tags",
            {
                "name": "tagged-test",
                "tags": ["test", "automated"],
                "steps": ["./run.sh"],
            },
        ),
        (
            "with-container",
            {
                "name": "container-test",
                "steps": ["python app.py"],
                "container": {
                    "image": "python:3.11-slim",
                    "pullPolicy": "missing",
                },
            },
        ),
    ],
)
def test_specific_dag_configurations(dag_name, dag_config, yaml_file):
    """Test specific DAG configurations using dagu CLI"""
    dag = Dag(**dag_config)

    # Use a stable index for specific tests
    index = hash(dag_name) % 1000

    # Save using the fixture
    filepath = yaml_file(dag, index, suffix=f"_specific_{dag_name}")

    print(f"\nTesting {dag_name} configuration...")
    is_valid, message = validate_dag_with_dagu(filepath)

    if not is_valid:
        pytest.fail(
            f"{dag_name} DAG validation failed\n"
            f"Message: {message}\n"
            f"Saved to: {filepath}"
        )

    print(f"✓ {dag_name} validated successfully")
