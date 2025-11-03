"""Base models and common types"""

from pydantic import BaseModel, Field


class Precondition(BaseModel):
    """Precondition that must be met before DAG execution"""

    condition: str = Field(
        examples=["`date +%u`", "test -f /data/ready.flag", "$STATUS"]
    )
    expected: str = Field(examples=["re:[1-5]", "0", "success"])
