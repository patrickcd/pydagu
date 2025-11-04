"""Executor configuration models"""

import json
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class HTTPExecutorConfig(BaseModel):
    """Configuration for HTTP executor"""

    headers: dict[str, str] | None = Field(
        None,
        description="Request headers",
        examples=[
            {"Authorization": "Bearer token", "Content-Type": "application/json"}
        ],
    )
    query: dict[str, str] | None = Field(
        None,
        description="URL query parameters",
        examples=[{"page": "1", "limit": "100"}],
    )
    body: str | dict[str, Any] | None = Field(
        None, description="Request body", examples=[{"name": "value", "id": 123}]
    )
    timeout: int | None = Field(
        None, ge=0, description="Timeout in seconds", examples=[30, 60, 120]
    )
    silent: bool | None = Field(
        None, description="Return body only without status info"
    )
    skipTLSVerify: bool | None = Field(
        None, description="Skip TLS certificate verification"
    )

    @field_validator("body", mode="before")
    @classmethod
    def serialize_body_to_json(cls, v: Any) -> str | None:
        """Convert dict body to JSON string automatically for Dagu compatibility"""
        if v is None:
            return None
        if isinstance(v, dict):
            return json.dumps(v)
        if isinstance(v, str):
            return v
        # For other types, try to serialize them
        return json.dumps(v)


class SSHExecutorConfig(BaseModel):
    """Configuration for SSH executor"""

    user: str | None = Field(
        None, description="SSH username", examples=["deploy", "admin", "ubuntu"]
    )
    host: str | None = Field(
        None,
        description="SSH host",
        examples=["production.example.com", "192.168.1.100"],
    )
    port: int | None = Field(22, description="SSH port", examples=[22, 2222])
    key: str | None = Field(
        None,
        description="Path to SSH private key",
        examples=["~/.ssh/deploy_key", "/etc/ssh/id_rsa"],
    )
    password: str | None = Field(
        None, description="SSH password", examples=["${SSH_PASSWORD}"]
    )
    strictHostKey: bool | None = Field(True, description="Strict host key checking")
    knownHostFile: str | None = Field(
        None, description="Path to known_hosts file", examples=["~/.ssh/known_hosts"]
    )


class MailExecutorConfig(BaseModel):
    """Configuration for mail executor"""

    to: str | list[str] | None = Field(
        None,
        description="Email recipient(s)",
        examples=["data-team@example.com", ["admin@example.com", "alerts@example.com"]],
    )
    from_: str | None = Field(
        None,
        alias="from",
        description="Email sender",
        examples=["etl-notifications@company.com"],
    )
    subject: str | None = Field(
        None,
        description="Email subject",
        examples=["ETL Failed - ${DATE}", "Pipeline Alert"],
    )
    body: str | None = Field(
        None, description="Email body", examples=["Check logs at ${DAG_RUN_LOG_FILE}"]
    )
    attachLogs: bool | None = Field(None, description="Attach execution logs to email")
    smtp: dict[str, Any] | None = Field(None, description="SMTP configuration override")


class DockerExecutorConfig(BaseModel):
    """Configuration for Docker executor"""

    image: str | None = Field(
        None,
        description="Docker image to use",
        examples=["postgres:16", "python:3.11-slim"],
    )
    container: str | None = Field(
        None, description="Container name", examples=["etl-worker", "db-backup"]
    )
    pull: bool | None = Field(None, description="Pull image before running")
    autoRemove: bool | None = Field(
        None, description="Automatically remove container after execution"
    )
    env: list[str] | dict[str, str] | None = Field(
        None,
        description="Environment variables",
        examples=[{"PGPASSWORD": "${DB_PASSWORD}"}, ["DEBUG=1", "LOG_LEVEL=info"]],
    )
    volumes: list[str] | None = Field(
        None,
        description="Volume mounts",
        examples=[["./data:/data", "./scripts:/scripts:ro"]],
    )
    network: str | None = Field(
        None,
        description="Docker network",
        examples=["bridge", "host", "custom-network"],
    )
    user: str | None = Field(
        None, description="User to run as", examples=["1000:1000", "nobody"]
    )
    workdir: str | None = Field(
        None, description="Working directory", examples=["/app", "/data"]
    )


class JQExecutorConfig(BaseModel):
    """Configuration for jq (JSON processor) executor"""

    query: str | None = Field(
        None,
        description="jq query expression",
        examples=[".data[] | select(.active)", ".results[0].name"],
    )
    raw: bool | None = Field(None, description="Output raw strings, not JSON")
    compact: bool | None = Field(None, description="Compact output")


class ShellExecutorConfig(BaseModel):
    """Configuration for shell executor"""

    shell: str | None = Field(
        None,
        description="Shell to use (e.g., bash, sh, zsh)",
        examples=["bash", "sh", "zsh"],
    )
    env: dict[str, str] | None = Field(
        None,
        description="Environment variables",
        examples=[{"PATH": "/usr/local/bin:$PATH", "DEBUG": "1"}],
    )


class ExecutorConfig(BaseModel):
    """Executor configuration for a step"""

    type: Literal["docker", "http", "jq", "mail", "shell", "ssh"] = Field(
        description="Executor type",
        examples=["docker", "http", "ssh", "mail", "shell", "jq"],
    )
    config: (
        HTTPExecutorConfig
        | SSHExecutorConfig
        | MailExecutorConfig
        | DockerExecutorConfig
        | JQExecutorConfig
        | ShellExecutorConfig
        | dict[str, Any]
        | None
    ) = Field(None, description="Executor-specific configuration")
