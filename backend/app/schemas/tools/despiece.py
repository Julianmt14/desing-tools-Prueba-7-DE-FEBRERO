from pydantic import BaseModel

from app.schemas.design import DespieceVigaCreate


class BeamDetailPayload(DespieceVigaCreate):
    pass


class BeamPresetResponse(BaseModel):
    fc_options: list[str]
    fy_options: list[str]
    hook_options: list[str]
    max_bar_lengths: list[str]
