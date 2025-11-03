"""Notification configuration models"""

from pydantic import BaseModel, Field


class MailOn(BaseModel):
    """Email notification configuration"""

    failure: bool | None = Field(None, description="Send email on failure")
    success: bool | None = Field(None, description="Send email on success")


class SMTPConfig(BaseModel):
    """SMTP configuration for email notifications"""

    host: str = Field(
        description="SMTP server host",
        examples=["smtp.gmail.com", "smtp.company.com", "localhost"],
    )
    port: str = Field(description="SMTP server port", examples=["587", "465", "25"])
    username: str | None = Field(
        None, description="SMTP username", examples=["user@example.com"]
    )
    password: str | None = Field(
        None, description="SMTP password", examples=["${SMTP_PASSWORD}"]
    )
