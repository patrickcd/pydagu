from typing import Annotated, TypeAlias

from pydantic import BeforeValidator, BaseModel, ConfigDict


def _empty_str_to_none(v: str | None) -> None:
    if v is None:
        return None
    if v == "":
        return None
    raise ValueError(
        "Value is not empty"
    )  # Not str or None, Fall to next type. e.g. Decimal, or a non-empty str


EmptyStrToNone: TypeAlias = Annotated[None, BeforeValidator(_empty_str_to_none)]


class DaguBase(BaseModel):
    """
    Dagu expects that serialized models do not include None or unset fields.
    """

    model_config = ConfigDict(exclude_none=True, exclude_unset=True)
