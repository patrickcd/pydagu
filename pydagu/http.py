# Functions for calling Dagu's HTTP API
import re

import httpx
from yaml import dump, Dumper, safe_load

from .models import Dag, StartDagRun, DagRunId, DagResponseMessage, DagRunResult


url_pattern = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")


class DaguHttpClient:
    def __init__(self, dag_name: str, url_root: str) -> None:
        self.dag_name = dag_name
        self.url_root = url_root.strip().rstrip("/")
        if not url_pattern.match(self.url_root):
            raise ValueError(f"Invalid URL root: {self.url_root}")

    def get_dag_spec(self) -> Dag:
        """Fetch a DAG from the Dagu HTTP API by its ID."""
        url = f"{self.url_root}/dags/{self.dag_name}/spec"
        response = httpx.get(url)
        response.raise_for_status()
        dag_data = response.json()
        dag_yaml = dag_data["spec"]
        dag_dict = safe_load(dag_yaml)
        return Dag.model_validate(dag_dict)

    def post_dag(self, dag: Dag) -> None | DagResponseMessage:
        """Post a DAG to the Dagu HTTP API"""
        url = f"{self.url_root}/dags"

        dagu_dict = dag.model_dump(exclude_unset=True, exclude_none=True)
        dag_yaml = dump(dagu_dict, Dumper=Dumper)

        body_json = {
            "name": self.dag_name,
            "spec": dag_yaml,
        }
        response = httpx.post(url, json=body_json)

        if response.status_code in (400, 409):
            return DagResponseMessage.model_validate(response.json())

        response.raise_for_status()
        return None

    def delete_dag(self) -> None:
        """Delete a DAG from the Dagu HTTP API by its name."""
        url = f"{self.url_root}/dags/{self.dag_name}"
        httpx.delete(url).raise_for_status()

    def start_dag_run(
        self, start_request: StartDagRun
    ) -> DagRunId | DagResponseMessage:
        """
        Start a DAG run via the Dagu HTTP API.

        Returns DagRunId unless StartDagRun.singleton is True and is already running,
        in which case it returns DagResponseMessage.
        """
        url = f"{self.url_root}/dags/{self.dag_name}/start"
        response = httpx.post(url, json=start_request.model_dump())
        response.raise_for_status()

        status_code = response.status_code
        if status_code in (200, 409):
            dag_run_data = response.json()
            if status_code == 409:
                return DagResponseMessage.model_validate(dag_run_data)
            else:
                return DagRunId.model_validate(dag_run_data)

        response.raise_for_status()
        raise httpx.HTTPError(f"Unexpected status code: {status_code}")

    def get_dag_run_status(self, dag_run_id: str) -> DagRunResult:
        """
        Get the status of a DAG run via the Dagu HTTP API.

        dag_run_id: The ID of the DAG run to fetch or "latest" for the most recent run.
        """
        url = f"{self.url_root}/dag-runs/{self.dag_name}/{dag_run_id}"
        response = httpx.get(url)
        response.raise_for_status()
        dag_run_data = response.json()
        return DagRunResult.model_validate(dag_run_data["dagRunDetails"])
