"""Schemathesis-based tests for DAG generation and validation

This module uses Schemathesis to generate random DAG configurations based on
the Pydantic models, then validates them using the local dagu CLI.
"""

import subprocess
from pathlib import Path
import pytest
import yaml
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from hypothesis_jsonschema import from_schema

from pydagu.models import Dag, Step


# Test configuration
MAX_HYPOTHESIS_EXAMPLES = (
    3  # Keep low - hypothesis-jsonschema struggles with complex anyOf
)
OUTPUT_DIR = Path(__file__).parent / "generated_dags"


def test_js():
    from yaml import Dumper
    # print(yaml.dump(Step.model_json_schema(), Dumper=Dumper))
    assert True


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


@pytest.mark.slow
@given(
    dag_data=from_schema(Dag.model_json_schema()),
    cron=st.one_of(st.none(), cron_expression()),
)
@settings(
    max_examples=MAX_HYPOTHESIS_EXAMPLES,
    deadline=30000,  # 30 second deadline per example
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_hypothesis_based_dag_generation(dag_data, cron, yaml_file):
    """Test DAG generation using Hypothesis strategies

    This test uses hypothesis-jsonschema to generate random DAGs based on
    the Pydantic model's JSON schema, then validates them using dagu CLI.
    """
    # Replace schedule with properly generated cron expression if present
    if "schedule" in dag_data and dag_data["schedule"]:
        dag_data["schedule"] = cron

    # Convert generated JSON data to Dag model
    try:
        dag = Dag(**dag_data)
    except Exception as e:
        # Skip invalid data that doesn't pass Pydantic validation
        # This includes steps without command/script/call
        pytest.skip(f"Generated data failed Pydantic validation: {e}")

    # Generate a unique index for this test run
    # Use hash of dag name to create a pseudo-unique index
    index = abs(hash(dag.name)) % 1000

    # Save the generated DAG
    saved_path = yaml_file(dag, index, suffix="_hypothesis")
    print(f"\nHypothesis-generated DAG saved to: {saved_path}")
    print(f"  Steps: {len(dag.steps)}")
    if dag.schedule:
        print(f"  Schedule: {dag.schedule}")

    # Validate using dagu CLI
    is_valid, message = validate_dag_with_dagu(saved_path)

    if not is_valid:
        # Save a copy with "failed" suffix for easier debugging
        failed_path = yaml_file(dag, index, suffix="_hypothesis_failed")

        # Print the DAG for debugging
        dag_yaml = yaml.dump(
            dag.model_dump(exclude_none=True), default_flow_style=False
        )
        print(f"\nFailed DAG content:\n{dag_yaml}")

        pytest.fail(
            f"Hypothesis-generated DAG validation failed with dagu CLI\n"
            f"Message: {message}\n"
            f"DAG saved to: {failed_path}"
        )

    print("✓ Hypothesis-generated DAG validated successfully")
