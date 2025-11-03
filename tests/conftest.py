"""Pytest configuration and fixtures for pydagu tests"""

import pytest


@pytest.fixture
def sample_dag_config():
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
def sample_step_config():
    """Sample step configuration for testing"""
    return {
        "name": "test-step",
        "command": "python test.py",
        "description": "Test step description",
        "depends": "previous-step",
    }
