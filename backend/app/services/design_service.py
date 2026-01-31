from sqlalchemy.orm import Session, selectinload

from app import models
from app.schemas.design import DespieceVigaCreate, DespieceVigaUpdate, DesignCreate


def _attach_despiece(design: models.Design, despiece_data: DespieceVigaCreate | None) -> None:
    if despiece_data is None:
        return

    if design.beam_despiece is None:
        design.beam_despiece = models.DespieceViga(**despiece_data.model_dump())
    else:
        for key, value in despiece_data.model_dump().items():
            setattr(design.beam_despiece, key, value)


def create_design(db: Session, *, design_in: DesignCreate, user_id: int) -> models.Design:
    payload = design_in.model_dump(exclude={"despiece_viga"})
    design = models.Design(**payload, user_id=user_id)
    _attach_despiece(design, design_in.despiece_viga)
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


def list_designs(db: Session, *, user_id: int) -> list[models.Design]:
    return (
        db.query(models.Design)
        .options(selectinload(models.Design.beam_despiece))
        .filter(models.Design.user_id == user_id)
        .all()
    )


def get_design(db: Session, *, design_id: int, user_id: int) -> models.Design | None:
    return (
        db.query(models.Design)
        .options(selectinload(models.Design.beam_despiece))
        .filter(models.Design.id == design_id, models.Design.user_id == user_id)
        .first()
    )


def update_despiece_for_design(
    db: Session,
    *,
    design_id: int,
    user_id: int,
    despiece_in: DespieceVigaUpdate,
) -> models.DespieceViga | None:
    design = get_design(db, design_id=design_id, user_id=user_id)
    if design is None:
        return None

    data = despiece_in.model_dump(exclude_unset=True)
    if not data:
        return design.beam_despiece

    if design.beam_despiece is None:
        design.beam_despiece = models.DespieceViga(design_id=design.id)

    for key, value in data.items():
        setattr(design.beam_despiece, key, value)

    db.add(design)
    db.commit()
    db.refresh(design.beam_despiece)
    return design.beam_despiece


def delete_despiece_for_design(db: Session, *, design_id: int, user_id: int) -> bool:
    design = get_design(db, design_id=design_id, user_id=user_id)
    if design is None or design.beam_despiece is None:
        return False

    db.delete(design.beam_despiece)
    db.commit()
    return True
