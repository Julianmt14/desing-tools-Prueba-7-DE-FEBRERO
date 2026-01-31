from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.tools.despiece import BeamDetailPayload, BeamPresetResponse
from app.schemas.design import (
    DesignCreate,
    DesignRead,
    DespieceVigaCreate,
    DespieceVigaRead,
    DespieceVigaUpdate,
)
from app.services import design_service
from app import models

router = APIRouter(prefix="/tools/despiece", tags=["tools: despiece de vigas"])


@router.get("/presets", response_model=BeamPresetResponse)
def get_presets():
    return BeamPresetResponse(
        fc_options=["21 MPa (3000 psi)", "24 MPa (3500 psi)", "28 MPa (4000 psi)"],
        fy_options=["420 MPa (Grado 60)", "520 MPa (Grado 75)"],
        hook_options=["Estándar 90°", "Sísmico 135°"],
        max_bar_lengths=["6m", "9m", "12m"],
    )


@router.post("/designs", response_model=DesignRead, status_code=status.HTTP_201_CREATED)
def create_beam_design(
    *,
    payload: BeamDetailPayload,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    despiece_fields = set(DespieceVigaCreate.model_fields.keys())
    despiece_payload = DespieceVigaCreate(**payload.model_dump(include=despiece_fields))
    settings_data = payload.model_dump(exclude=despiece_fields)

    design_in = DesignCreate(
        title=f"Despiece {payload.beam_label}",
        description=f"Proyecto {payload.project_name}",
        design_type="beam_detailing",
        settings=settings_data,
        despiece_viga=despiece_payload,
    )
    return design_service.create_design(db, design_in=design_in, user_id=current_user.id)


@router.get("/designs/{design_id}", response_model=DespieceVigaRead)
def get_beam_despiece(
    *,
    design_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    design = design_service.get_design(db, design_id=design_id, user_id=current_user.id)
    if design is None or design.beam_despiece is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despiece no encontrado")
    return design.beam_despiece


@router.put("/designs/{design_id}", response_model=DespieceVigaRead)
def update_beam_despiece(
    *,
    design_id: int,
    payload: DespieceVigaUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    updated = design_service.update_despiece_for_design(
        db,
        design_id=design_id,
        user_id=current_user.id,
        despiece_in=payload,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despiece no encontrado")
    return updated


@router.delete("/designs/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_beam_despiece(
    *,
    design_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    deleted = design_service.delete_despiece_for_design(
        db,
        design_id=design_id,
        user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despiece no encontrado")
