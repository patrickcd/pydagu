"""Infrastructure configuration models"""

from typing import Literal
from pydantic import BaseModel, Field


class ContainerConfig(BaseModel):
    """Container configuration for steps"""

    image: str = Field(
        description="Container image to use",
        examples=["python:3.11-slim", "postgres:16", "alpine:latest"],
    )
    pullPolicy: Literal["always", "missing", "never"] | None = Field(
        None,
        description="Image pull policy",
        examples=["always", "missing", "never"],
    )
    env: list[str] | None = Field(
        None,
        description="Environment variables",
        examples=[["PYTHONUNBUFFERED=1", "DEBUG=true"]],
    )
    volumes: list[str] | None = Field(
        None,
        description="Volume mounts",
        examples=[["./data:/data", "./scripts:/scripts:ro"]],
    )


class SSHConfig(BaseModel):
    """SSH configuration for remote execution"""

    user: str = Field(
        description="SSH username", examples=["deploy", "admin", "ubuntu"]
    )
    host: str = Field(
        description="SSH host", examples=["production.example.com", "192.168.1.100"]
    )
    port: int | None = Field(
        22, description="SSH port (default: 22)", examples=[22, 2222]
    )
    key: str | None = Field(
        None,
        description="Path to SSH private key file",
        examples=["~/.ssh/deploy_key", "/etc/ssh/id_rsa"],
    )
    password: str | None = Field(
        None,
        description="SSH password (prefer keys for security)",
        examples=["${SSH_PASSWORD}"],
    )
    strictHostKey: bool | None = Field(
        True, description="Enable strict host key checking (default: true)"
    )
    knownHostFile: str | None = Field(
        "~/.ssh/known_hosts",
        description="Path to known_hosts file",
        examples=["~/.ssh/known_hosts", "/etc/ssh/known_hosts"],
    )


class LogConfig(BaseModel):
    """Logging configuration"""

    dir: str | None = Field(
        None, description="Log directory", examples=["/var/log/dagu", "./logs"]
    )
    prefix: str | None = Field(
        None, description="Log file prefix", examples=["dag-", "etl-"]
    )
