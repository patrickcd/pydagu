import uuid
import time
import json
import threading
from typing import Generator
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest

from pydagu.http import DaguHttpClient
from pydagu.builder import DagBuilder, StepBuilder
from pydagu.models import StartDagRun, DagRunId, DagRunResult


class WebhookHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler for testing webhooks"""

    received_requests = []

    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get("Content-Length", 0))
        body = (
            self.rfile.read(content_length).decode("utf-8")
            if content_length > 0
            else ""
        )

        # Store the received request
        request_data = {
            "method": "POST",
            "path": self.path,
            "headers": dict(self.headers),
            "body": body,
        }
        WebhookHandler.received_requests.append(request_data)

        # Send a successful response
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {"status": "received", "message": "Webhook received successfully"}
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def log_message(self, format, *args):
        """Suppress default logging to avoid cluttering test output"""
        pass


@pytest.fixture
def http_server() -> Generator[tuple[HTTPServer, int], None, None]:
    """Start a simple HTTP server for testing webhooks"""
    # Reset the received requests
    WebhookHandler.received_requests = []

    # Create the server on an available port
    server = HTTPServer(("localhost", 0), WebhookHandler)
    port = server.server_address[1]

    # Start server in a background thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    yield server, port

    # Cleanup
    server.shutdown()
    server.server_close()


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


def test_webhook_dag(dagu_client: DaguHttpClient, http_server: tuple[HTTPServer, int]):
    """
    Test posting a DAG for executing a webhook. It required parameters for the url, headers, and payload.

    Then run a http server (pytest fixture) to receive the webhook and verify it was received correctly.
    """
    server, port = http_server
    webhook_url = f"http://localhost:{port}/webhook/test"

    # Build a DAG with a webhook step using the HTTP executor
    webhook_payload = {"event": "test_event", "data": {"message": "Hello from Dagu!"}}

    step = (
        StepBuilder("send_webhook")
        .command(f"POST {webhook_url}")  # HTTP executor requires "METHOD URL" format
        .http_executor(
            headers={
                "Content-Type": "application/json",
                "X-Test-Header": "test-value",
                "Authorization": "Bearer test-token",
            },
            body=webhook_payload,  # Dict is automatically converted to JSON string
            timeout=10,
        )
        .build()
    )

    dag = (
        DagBuilder(dagu_client.dag_name)
        .description("Test webhook DAG")
        .add_step_models(step)
        .build()
    )

    # Post the DAG to Dagu
    create_response = dagu_client.post_dag(dag)
    assert create_response is None

    # Verify the DAG was created
    retrieved_dag = dagu_client.get_dag_spec()
    assert retrieved_dag.name == dag.name
    assert len(retrieved_dag.steps) == 1

    # Start the DAG run
    start_request = StartDagRun(dagName=dagu_client.dag_name)
    dag_run_id = dagu_client.start_dag_run(start_request)
    assert isinstance(dag_run_id, DagRunId)
    assert dag_run_id.dagRunId is not None

    # Wait for the DAG to complete
    time.sleep(2)

    # Check the DAG run status
    dag_run_result = dagu_client.get_dag_run_status(dag_run_id.dagRunId)
    assert isinstance(dag_run_result, DagRunResult)
    assert dag_run_result.dagRunId == dag_run_id.dagRunId
    assert (
        dag_run_result.statusLabel == "succeeded"
    )  # Verify the webhook was received by the HTTP server
    assert len(WebhookHandler.received_requests) == 1

    received_request = WebhookHandler.received_requests[0]
    assert received_request["method"] == "POST"
    assert received_request["path"] == "/webhook/test"
    assert received_request["headers"]["Content-Type"] == "application/json"
    assert received_request["headers"]["X-Test-Header"] == "test-value"
    assert received_request["headers"]["Authorization"] == "Bearer test-token"

    # Verify the payload
    received_body = json.loads(received_request["body"])
    assert received_body == webhook_payload
    assert received_body["event"] == "test_event"
    assert received_body["data"]["message"] == "Hello from Dagu!"


def test_http_executor_validation():
    """Test that HTTP executor validates command format and body serialization"""
    from pydantic import ValidationError

    # Test 1: Invalid command format (missing METHOD)
    with pytest.raises(
        ValidationError, match="HTTP executor command must be in format"
    ):
        StepBuilder("invalid_step").command(
            "https://api.example.com/webhook"
        ).http_executor().build()

    # Test 2: Invalid command format (no URL)
    with pytest.raises(
        ValidationError, match="HTTP executor command must be in format"
    ):
        StepBuilder("invalid_step").command("POST").http_executor().build()

    # Test 3: Valid command formats should work
    valid_commands = [
        "GET https://api.example.com/data",
        "POST https://api.example.com/webhook",
        "PUT https://api.example.com/resource",
        "DELETE https://api.example.com/resource",
        "PATCH https://api.example.com/resource",
        "get http://localhost:8080/test",  # Case insensitive
    ]

    for cmd in valid_commands:
        step = StepBuilder("valid_step").command(cmd).http_executor().build()
        assert step.command == cmd

    # Test 4: Body dict is automatically converted to JSON string
    step = (
        StepBuilder("test_body")
        .command("POST https://api.example.com/webhook")
        .http_executor(body={"key": "value", "number": 123})
        .build()
    )
    assert step.executor.config.body == '{"key": "value", "number": 123}'

    # Test 5: Body string is preserved
    step = (
        StepBuilder("test_body")
        .command("POST https://api.example.com/webhook")
        .http_executor(body='{"already": "json"}')
        .build()
    )
    assert step.executor.config.body == '{"already": "json"}'
