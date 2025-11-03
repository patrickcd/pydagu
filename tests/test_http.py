import uuid
import time
from typing import Generator

import pytest

from pydagu.http import DaguHttpClient
from pydagu.builder import DagBuilder
from pydagu.models import StartDagRun, DagRunId, DagRunResult


@pytest.fixture
def dagu_client() -> Generator[DaguHttpClient, None, None]:
    dag_name = uuid.uuid4().hex[:39]
    client = DaguHttpClient(dag_name=dag_name, url_root="http://localhost:8080/api/v2/")
    yield client
    client.delete_dag()


def test_post_and_run_dag(dagu_client: DaguHttpClient):
    dag = (
        DagBuilder(dagu_client.dag_name)
        .add_step("step1", "echo 'Hello, World!'")
        .add_step("step2", "echo 'This is step 2'")
        .build()
    )

    create_response = dagu_client.post_dag(dag)

    assert create_response is None

    retrieved_dag = dagu_client.get_dag_spec()

    assert retrieved_dag.name == dag.name
    assert len(retrieved_dag.steps) == len(dag.steps)

    start_request = StartDagRun(dagName=dagu_client.dag_name)
    dag_run_id = dagu_client.start_dag_run(start_request)
    assert isinstance(dag_run_id, DagRunId)

    assert dag_run_id.dagRunId is not None

    dag_run_result = dagu_client.get_dag_run_status(dag_run_id.dagRunId)

    assert isinstance(dag_run_result, DagRunResult)
    assert dag_run_result.dagRunId == dag_run_id.dagRunId
    assert len(dag_run_result.nodes) == len(dag.steps)
    assert dag_run_result.statusLabel == "running"

    # Wait for DAG run to complete
    time.sleep(0.5)
    dag_run_result = dagu_client.get_dag_run_status(dag_run_id.dagRunId)
    assert dag_run_result.statusLabel == "succeeded"
