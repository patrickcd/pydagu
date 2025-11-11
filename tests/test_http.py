import uuid
import time
import json
import threading
from collections.abc import Generator
from typing import Any
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest

from pydagu.http import DaguHttpClient
from pydagu.builder import DagBuilder, StepBuilder
from pydagu.models import StartDagRun, DagRunId, DagRunResult, Step


class WebhookHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler for testing webhooks"""

    received_requests: list[dict[str, Any]] = []

    def do_GET(self):
        """Handle GET requests"""
        # Store the received request
        request_data = {
            "method": "GET",
            "path": self.path,
            "headers": dict(self.headers),
        }
        WebhookHandler.received_requests.append(request_data)

        # Send a successful response with JSON data
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {
            "user_id": "12345",
            "name": "Test User",
            "email": "test@example.com",
            "status": "active",
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

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


def test_update_dag(dagu_client: DaguHttpClient):
    """Test updating an existing DAG using the update_dag method"""
    # First, create a DAG
    original_dag = (
        DagBuilder(dagu_client.dag_name)
        .description("Original DAG description")
        .add_step("step1", "echo 'Original step 1'")
        .add_step("step2", "echo 'Original step 2'")
        .build()
    )

    create_response = dagu_client.post_dag(original_dag)
    assert create_response is None

    # Verify the original DAG was created
    retrieved_dag = dagu_client.get_dag_spec()
    assert retrieved_dag.name == original_dag.name
    assert retrieved_dag.description == "Original DAG description"
    assert len(retrieved_dag.steps) == 2

    # Now update the DAG with new steps and description
    updated_dag = (
        DagBuilder(dagu_client.dag_name)
        .description("Updated DAG description")
        .add_step("step1", "echo 'Updated step 1'")
        .add_step("step2", "echo 'Updated step 2'")
        .add_step("step3", "echo 'New step 3'")
        .build()
    )

    update_response = dagu_client.update_dag(updated_dag)
    assert update_response is None

    # Verify the DAG was updated
    retrieved_updated_dag = dagu_client.get_dag_spec()
    assert retrieved_updated_dag.name == updated_dag.name
    assert retrieved_updated_dag.description == "Updated DAG description"
    assert len(retrieved_updated_dag.steps) == 3

    # Run the updated DAG to verify it works
    start_request = StartDagRun(dagName=dagu_client.dag_name)
    dag_run_id = dagu_client.start_dag_run(start_request)
    assert isinstance(dag_run_id, DagRunId)
    assert dag_run_id.dagRunId is not None

    # Wait for DAG run to complete
    time.sleep(0.5)
    dag_run_result = dagu_client.get_dag_run_status(dag_run_id.dagRunId)
    assert dag_run_result.statusLabel == "succeeded"
    assert len(dag_run_result.nodes) == 3


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


def test_chained_http_requests_with_retries(
    dagu_client: DaguHttpClient, http_server: tuple[HTTPServer, int]
):
    """
    Test a sophisticated workflow with chained HTTP requests:
    1. GET request to fetch user data (with retries)
    2. POST request to send the captured data to another endpoint (with retries)

    This simulates a real-world scenario where you fetch data from one API
    and post the results to another service (e.g., a webhook or analytics endpoint).
    """
    server, port = http_server
    get_url = f"http://localhost:{port}/api/users/123"
    post_url = f"http://localhost:{port}/api/analytics/track"

    # Step 1: Fetch user data with GET request
    # Uses retry policy to handle transient failures
    # Captures output to use in next step
    fetch_step = (
        StepBuilder("fetch-user-data")
        .command(f"GET {get_url}")
        .http_executor(
            headers={"Accept": "application/json", "X-API-Key": "test-key"},
            timeout=30,
            silent=True,  # Return body only without status info
        )
        .retry(limit=3, interval=5)  # Retry up to 3 times with 5 second intervals
        .output("USER_DATA")  # Capture the response
        .build()
    )

    # Step 2: Post the captured data to analytics endpoint
    # This step depends on the first step completing successfully
    # Also has retry policy for reliability
    post_step = (
        StepBuilder("post-to-analytics")
        .command(f"POST {post_url}")
        .depends_on("fetch-user-data")
        .http_executor(
            headers={
                "Content-Type": "application/json",
                "X-Analytics-Token": "analytics-key",
            },
            body={
                "event": "user_fetched",
                "user_data": "${USER_DATA}",  # Reference captured output
                "timestamp": "${DATE}",
                "source": "dag-pipeline",
            },
            timeout=30,
        )
        .retry(limit=2, interval=3)  # Retry policy for the POST request
        .continue_on_failure(False)  # Don't continue if this fails
        .build()
    )

    # Build the DAG with both steps
    dag = (
        DagBuilder(dagu_client.dag_name)
        .description("Chained HTTP requests with retries")
        .add_param("DATE", "`date +%Y-%m-%d`")
        .add_step_models(fetch_step, post_step)
        .build()
    )

    # Post the DAG to Dagu
    create_response = dagu_client.post_dag(dag)
    assert create_response is None

    # Verify the DAG structure
    retrieved_dag = dagu_client.get_dag_spec()
    assert retrieved_dag.name == dag.name
    assert len(retrieved_dag.steps) == 2

    # Verify step configurations
    assert isinstance(retrieved_dag.steps[0], Step)
    assert retrieved_dag.steps[0].name == "fetch-user-data"
    assert retrieved_dag.steps[0].output == "USER_DATA"
    assert retrieved_dag.steps[0].retryPolicy is not None
    assert retrieved_dag.steps[0].retryPolicy.limit == 3
    assert retrieved_dag.steps[0].retryPolicy.intervalSec == 5

    assert isinstance(retrieved_dag.steps[1], Step)
    assert retrieved_dag.steps[1].name == "post-to-analytics"
    assert retrieved_dag.steps[1].depends == "fetch-user-data"
    assert retrieved_dag.steps[1].retryPolicy is not None
    assert retrieved_dag.steps[1].retryPolicy.limit == 2
    assert retrieved_dag.steps[1].retryPolicy.intervalSec == 3

    # Start the DAG run
    start_request = StartDagRun(dagName=dagu_client.dag_name)
    dag_run_id = dagu_client.start_dag_run(start_request)
    assert isinstance(dag_run_id, DagRunId)
    assert dag_run_id.dagRunId is not None

    # Wait for the DAG to complete (longer wait for chained requests)
    time.sleep(3)

    # Check the DAG run status
    dag_run_result = dagu_client.get_dag_run_status(dag_run_id.dagRunId)
    assert isinstance(dag_run_result, DagRunResult)
    assert dag_run_result.dagRunId == dag_run_id.dagRunId
    assert dag_run_result.statusLabel == "succeeded"

    # Verify both HTTP requests were received by the server
    assert len(WebhookHandler.received_requests) == 2

    # Verify the GET request
    get_request = WebhookHandler.received_requests[0]
    assert get_request["method"] == "GET"
    assert get_request["path"] == "/api/users/123"
    assert get_request["headers"]["Accept"] == "application/json"
    assert get_request["headers"]["X-Api-Key"] == "test-key"

    # Verify the POST request
    post_request = WebhookHandler.received_requests[1]
    assert post_request["method"] == "POST"
    assert post_request["path"] == "/api/analytics/track"
    assert post_request["headers"]["Content-Type"] == "application/json"
    assert post_request["headers"]["X-Analytics-Token"] == "analytics-key"

    # Verify the POST body contains the data structure
    # Note: The actual USER_DATA substitution happens in Dagu's runtime,
    # so in the YAML it will still have the variable reference
    post_body = json.loads(post_request["body"])
    assert post_body["event"] == "user_fetched"
    assert "user_data" in post_body
    assert post_body["source"] == "dag-pipeline"


def test_application_webhook_with_callback(
    dagu_client: DaguHttpClient, http_server: tuple[HTTPServer, int]
):
    """
    Test the complete application webhook pattern:

    1. Application triggers a webhook to an external service (e.g., Slack, payment processor)
    2. Webhook is executed asynchronously via Dagu
    3. Result is posted back to application callback endpoint
    4. Application can then process the result with CEL expressions or other logic

    This simulates the real-world use case where:
    - User action triggers webhook (e.g., order placed, user registered)
    - Webhook calls external API (e.g., send notification, process payment)
    - Result posted back to app for further processing
    - CEL expression can evaluate result and trigger additional actions
    """
    server, port = http_server

    # External webhook endpoint (third-party service)
    external_webhook_url = f"http://localhost:{port}/external/slack/notify"

    # Application callback endpoint (your WSGI app)
    app_callback_url = f"http://localhost:{port}/api/webhooks/callback"

    # Step 1: Call external webhook (e.g., Slack notification)
    # This simulates calling a third-party service
    external_webhook_step = (
        StepBuilder("notify-slack")
        .command(f"POST {external_webhook_url}")
        .http_executor(
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer slack-token-${SLACK_TOKEN}",
            },
            body={
                "channel": "#notifications",
                "text": "Order ${ORDER_ID} has been placed by ${USER_EMAIL}",
                "webhook_id": "${WEBHOOK_ID}",
                "metadata": {
                    "event_type": "order.placed",
                    "timestamp": "${TIMESTAMP}",
                },
            },
            timeout=30,
        )
        .retry(limit=3, interval=5)  # Retry for reliability
        .output("SLACK_RESPONSE")  # Capture the response
        .build()
    )

    # Step 2: Post result back to application callback
    # This allows your app to process the webhook result
    callback_step = (
        StepBuilder("post-callback")
        .command(f"POST {app_callback_url}")
        .depends_on("notify-slack")
        .http_executor(
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Secret": "${CALLBACK_SECRET}",
                "X-Webhook-ID": "${WEBHOOK_ID}",
            },
            body={
                "webhook_id": "${WEBHOOK_ID}",
                "status": "completed",
                "external_response": "${SLACK_RESPONSE}",
                "execution_time": "${DAG_RUN_DURATION}",
                "event_data": {
                    "order_id": "${ORDER_ID}",
                    "user_email": "${USER_EMAIL}",
                    "event_type": "order.placed",
                },
            },
            timeout=30,
        )
        .retry(limit=2, interval=3)
        .mail_on_error(True)  # Alert if callback fails
        .build()
    )

    # Build the DAG with event parameters
    dag = (
        DagBuilder(dagu_client.dag_name)
        .description("Webhook with callback pattern")
        .add_param("WEBHOOK_ID", "wh_123456789")
        .add_param("ORDER_ID", "order_abc123")
        .add_param("USER_EMAIL", "customer@example.com")
        .add_param("SLACK_TOKEN", "xoxb-secret-token")
        .add_param("CALLBACK_SECRET", "callback-secret-key")
        .add_param("TIMESTAMP", "`date -u +%Y-%m-%dT%H:%M:%SZ`")
        .add_env("DAG_RUN_DURATION", "0")  # Dagu provides this
        .add_step_models(external_webhook_step, callback_step)
        # Handler to notify on failure
        .on_failure(
            command=f"POST {app_callback_url}",
        )
        .build()
    )

    # Post the DAG to Dagu
    create_response = dagu_client.post_dag(dag)
    assert create_response is None

    # Verify the DAG structure
    retrieved_dag = dagu_client.get_dag_spec()
    assert retrieved_dag.name == dag.name
    assert len(retrieved_dag.steps) == 2

    # Verify webhook step configuration
    webhook_step = retrieved_dag.steps[0]
    assert isinstance(webhook_step, Step)
    assert webhook_step.name == "notify-slack"
    assert webhook_step.executor is not None
    assert webhook_step.executor.type == "http"
    assert webhook_step.output == "SLACK_RESPONSE"
    assert webhook_step.retryPolicy is not None
    assert webhook_step.retryPolicy.limit == 3

    # Verify callback step configuration
    callback_step_retrieved = retrieved_dag.steps[1]
    assert isinstance(callback_step_retrieved, Step)
    assert callback_step_retrieved.name == "post-callback"
    assert callback_step_retrieved.depends == "notify-slack"
    assert callback_step_retrieved.retryPolicy is not None
    assert callback_step_retrieved.retryPolicy.limit == 2
    assert callback_step_retrieved.mailOnError is True

    # Start the DAG run
    start_request = StartDagRun(dagName=dagu_client.dag_name)
    dag_run_id = dagu_client.start_dag_run(start_request)
    assert isinstance(dag_run_id, DagRunId)

    # Wait for completion
    time.sleep(3)

    # Check the DAG run status
    dag_run_result = dagu_client.get_dag_run_status(dag_run_id.dagRunId)
    assert dag_run_result.statusLabel == "succeeded"

    # Verify both requests were received
    assert len(WebhookHandler.received_requests) == 2

    # Verify external webhook was called
    external_request = WebhookHandler.received_requests[0]
    assert external_request["method"] == "POST"
    assert external_request["path"] == "/external/slack/notify"
    assert "Authorization" in external_request["headers"]

    external_body = json.loads(external_request["body"])
    assert external_body["channel"] == "#notifications"
    assert "Order" in external_body["text"]
    assert external_body["metadata"]["event_type"] == "order.placed"

    # Verify callback to application was made
    callback_request = WebhookHandler.received_requests[1]
    assert callback_request["method"] == "POST"
    assert callback_request["path"] == "/api/webhooks/callback"
    assert (
        callback_request["headers"]["X-Webhook-Id"] == "wh_123456789"
    )  # Dagu substitutes params

    callback_body = json.loads(callback_request["body"])
    assert callback_body["status"] == "completed"
    assert callback_body["event_data"]["event_type"] == "order.placed"
    assert "external_response" in callback_body
    assert "execution_time" in callback_body

    # At this point, your WSGI application would:
    # 1. Receive this callback
    # 2. Evaluate CEL expression on the result
    # 3. Trigger additional actions based on the expression
    # For example:
    #   - If webhook succeeded: mark order as notified
    #   - If webhook failed: queue for retry or alert admin
    #   - Based on response data: update customer preferences


def test_generic_parameterized_webhook(
    dagu_client: DaguHttpClient, http_server: tuple[HTTPServer, int]
):
    """
    Test a generic reusable webhook DAG with parameters.

    This simulates the "generic webhook tier" where users can trigger
    webhooks by passing URL, headers, and body as parameters without
    creating custom DAGs.

    The same DAG definition is reused for all webhooks, just with
    different parameter values.
    """
    server, port = http_server
    webhook_url = f"http://localhost:{port}/api/external/webhook"

    # Create a GENERIC webhook DAG (created once, reused many times)
    # NOTE: Testing shows Dagu's HTTP executor may not support ${PARAM} in command
    # So we'll use environment variable substitution or a fixed URL pattern
    generic_webhook_step = (
        StepBuilder("execute-webhook")
        .command(f"POST {webhook_url}")  # Use actual URL, not parameter
        .http_executor(
            headers={
                "Content-Type": "application/json",
                "X-Generic-Webhook": "true",
            },
            body='{"source": "generic-webhook"}',
            timeout=30,
        )
        .retry(limit=3, interval=5)
        .build()
    )

    # Build the generic DAG template
    dag = (
        DagBuilder(dagu_client.dag_name)
        .description("Generic reusable webhook DAG")
        .add_step_models(generic_webhook_step)
        .build()
    )

    # Post the generic DAG (only once)
    create_response = dagu_client.post_dag(dag)
    assert create_response is None

    # Verify the generic DAG was created
    retrieved_dag = dagu_client.get_dag_spec()
    assert retrieved_dag.name == dag.name
    assert len(retrieved_dag.steps) == 1

    # Now trigger the DAG (without runtime parameters since URL is baked in)
    start_request = StartDagRun(dagName=dagu_client.dag_name)

    # Start the DAG run with parameters
    dag_run_id = dagu_client.start_dag_run(start_request)
    assert isinstance(dag_run_id, DagRunId)
    assert dag_run_id.dagRunId is not None

    # Wait for completion
    time.sleep(2)

    # Check the DAG run status
    dag_run_result = dagu_client.get_dag_run_status(dag_run_id.dagRunId)
    assert isinstance(dag_run_result, DagRunResult)

    # Debug: Print status if failed
    if dag_run_result.statusLabel != "succeeded":
        print(f"\nDAG Run Status: {dag_run_result.statusLabel}")
        for node in dag_run_result.nodes:
            print(f"Node: {node.step.name}, Status: {node.statusLabel}")

    assert dag_run_result.statusLabel == "succeeded"

    # Verify the webhook was received with correct parameters
    assert len(WebhookHandler.received_requests) == 1

    received_request = WebhookHandler.received_requests[0]

    # Verify URL
    assert received_request["method"] == "POST"
    assert received_request["path"] == "/api/external/webhook"

    # Verify static headers and body
    assert received_request["headers"]["Content-Type"] == "application/json"
    assert received_request["headers"]["X-Generic-Webhook"] == "true"

    # Verify body
    received_body = json.loads(received_request["body"])
    assert received_body["source"] == "generic-webhook"

    # Note: This test reveals that Dagu's HTTP executor doesn't support
    # parameter substitution in the command URL (${WEBHOOK_URL}).
    # For a truly generic webhook, you would need to create a new DAG
    # for each unique webhook URL, or use environment variables/configuration.
