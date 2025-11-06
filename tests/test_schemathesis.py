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

from pydagu.models import Dag


# Test configuration
MAX_HYPOTHESIS_EXAMPLES = 10

OUTPUT_DIR = Path(__file__).parent / "generated_dags"


# Custom text strategy that avoids control characters and invalid unicode
@st.composite
def valid_text(draw, min_size=0, max_size=None):
    """Generate valid printable text (ASCII + common unicode, no control chars)"""
    # Use a restricted alphabet that avoids problematic unicode
    alphabet = st.characters(
        blacklist_categories=("Cc", "Cs"),  # Control and surrogate characters
        blacklist_characters="\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f",
    )
    return draw(st.text(alphabet=alphabet, min_size=min_size, max_size=max_size or 20))


@st.composite
def dag_name_strategy(draw):
    """Generate a valid DAG name (alphanumeric, dashes, dots, underscores)"""
    # dagu requires: alphanumeric characters, dashes, dots, and underscores only
    return draw(st.from_regex(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,49}", fullmatch=True))


@st.composite
def command_text(draw):
    """Generate valid command/script text that won't be empty after YAML processing

    This avoids special YAML characters that could cause issues when used alone,
    and ensures the text is meaningful as a command.
    """
    # Use a strategy that generates actual command-like strings
    # Either use a predefined safe command or generate alphanumeric text
    return draw(
        st.one_of(
            # Predefined safe commands
            st.sampled_from(
                [
                    "echo hello",
                    "ls",
                    "pwd",
                    "./script.sh",
                    "python main.py",
                    "node index.js",
                    "bash run.sh",
                ]
            ),
            # Or generate alphanumeric command-like strings with common separators
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("L", "N"),  # Letters and numbers
                    whitelist_characters=" -./_",  # Common command separators
                ),
                min_size=2,
                max_size=50,
            ).filter(lambda s: s and s.strip() and not s.isspace()),
        )
    )


@st.composite
def step_strategy(draw):
    """Generate a valid Step with either command or script"""
    # Decide which action to use
    use_command = draw(st.booleans())

    # Generate non-empty, non-whitespace command/script
    action_text = draw(command_text())

    step_dict = {"command" if use_command else "script": action_text}

    # Optional fields
    if draw(st.booleans()):
        step_dict["description"] = draw(valid_text(max_size=100))
    if draw(st.booleans()):
        step_dict["dir"] = draw(valid_text(max_size=50))

    return step_dict


@st.composite
def steps_with_unique_names(draw):
    """Generate a list of steps with unique names"""
    num_steps = draw(st.integers(min_value=1, max_value=5))
    steps = []

    for i in range(num_steps):
        step_dict = draw(step_strategy())
        # Assign a unique name based on index
        step_dict["name"] = f"step-{i}"
        steps.append(step_dict)

    return steps


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

        # Named range - ensure proper ordering by using indices
        @st.composite
        def named_range(draw):
            indices = draw(
                st.lists(
                    st.integers(min_value=0, max_value=len(allow_names) - 1),
                    min_size=2,
                    max_size=2,
                    unique=True,
                )
            )
            # Sort to ensure start <= end
            start_idx, end_idx = sorted(indices)
            return f"{allow_names[start_idx]}-{allow_names[end_idx]}"

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
    counter = {"value": 0}  # Mutable counter to track file indices

    def _create_file(dag: Dag, suffix: str = "") -> Path:
        """Save a DAG to a YAML file for reference

        Args:
            dag: The DAG model to save
            suffix: Optional suffix for the filename (e.g., "failed")

        Returns:
            Path to the saved file
        """
        index = counter["value"]
        counter["value"] += 1

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
    dag_name=dag_name_strategy(),
    steps_data=steps_with_unique_names(),
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
def test_dag_generation(dag_name, steps_data, cron, yaml_file):
    """Test DAG generation using Hypothesis strategies

    This test uses custom Hypothesis strategies to generate valid DAGs with:
    - Valid character sets (no control characters or invalid unicode)
    - Steps that always have either command or script
    """
    # Build the DAG data from our controlled strategies
    dag_data = {
        "name": dag_name,
        "steps": steps_data,
    }

    # Add cron schedule if provided
    if cron is not None:
        dag_data["schedule"] = cron

    # Convert generated JSON data to Dag model
    dag = Dag(**dag_data)

    # Save the generated DAG
    saved_path = yaml_file(dag, suffix="_hypothesis")

    # Validate using dagu CLI
    is_valid, message = validate_dag_with_dagu(saved_path)

    if not is_valid:
        # Save a copy with "failed" suffix for easier debugging
        failed_path = yaml_file(dag, suffix="_hypothesis_failed")

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
