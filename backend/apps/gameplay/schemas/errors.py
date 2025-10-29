from typing import Literal, Annotated, Union, Optional
from pydantic import BaseModel, Discriminator


class ErrorBase(BaseModel):
    type: str
    message: str
    side: Optional[Literal['side_a', 'side_b']] = None


class EnergyError(ErrorBase): # More broadly resource error?
    type: Literal["error_energy"] = "error_energy"
    message: str = "Not enough energy."


class TargetError(ErrorBase): # More broadly action error?
    type: Literal["error_target"] = "error_target"
    message: str = "Invalid target."


GameError = Annotated[
    Union[
        EnergyError,
        TargetError,
    ],
    Discriminator('type')
]