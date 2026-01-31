from fastapi import APIRouter, Depends

from app.api import deps
from app.schemas.user import UserRead
from app import models

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: models.User = Depends(deps.get_current_user)):
    return current_user
