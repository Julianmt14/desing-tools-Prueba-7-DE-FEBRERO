from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.design import DesignCreate, DesignRead
from app.services import design_service
from app import models

router = APIRouter(prefix="/designs", tags=["designs"])


@router.get("/", response_model=list[DesignRead])
def list_designs(
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    return design_service.list_designs(db, user_id=current_user.id)


@router.post("/", response_model=DesignRead, status_code=status.HTTP_201_CREATED)
def create_design(
    *,
    design_in: DesignCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    return design_service.create_design(db, design_in=design_in, user_id=current_user.id)
