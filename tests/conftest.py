"""Pytest configuration and fixtures for pydagu tests"""

import pathlib

import pytest
import yaml


@pytest.fixture
def sample_dag_config() -> dict:
    """Sample DAG configuration for testing"""
    return {
        "name": "test-dag",
        "description": "Test DAG description",
        "schedule": "0 2 * * *",
        "tags": ["test", "example"],
        "maxActiveRuns": 1,
        "steps": ["echo 'Hello'", "echo 'World'"],
    }


@pytest.fixture
def sample_step_config() -> dict:
    """Sample step configuration for testing"""
    return {
        "name": "test-step",
        "command": "python test.py",
        "description": "Test step description",
        "depends": "previous-step",
    }


@pytest.fixture(scope="session")
def dagu_example_text() -> str:
    """Yaml extracted from Dagu example file"""
    example_path = pathlib.Path(__file__).parent / "dagu-example.yaml"
    return example_path.read_text()


@pytest.fixture
def dagu_example(dagu_example_text) -> dict:
    """Yaml extracted from Dagu example file"""
    return yaml.safe_load(dagu_example_text)
