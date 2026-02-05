from __future__ import annotations

from pathlib import Path
from typing import cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.schemas.drawing_export import DrawingExportJobCreate, DrawingExportJobRead
from app.services import design_service, drawing_export_service

router = APIRouter(prefix="/drawing/exports", tags=["drawing-exports"])


@router.post("", response_model=DrawingExportJobRead, status_code=status.HTTP_202_ACCEPTED)
@router.post("/", response_model=DrawingExportJobRead, status_code=status.HTTP_202_ACCEPTED)
def enqueue_drawing_export(
    *,
    export_in: DrawingExportJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    if export_in.design_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="design_id es obligatorio para exportar",
        )
    user_id = cast(int, current_user.id)
    design = design_service.get_design(
        db,
        design_id=export_in.design_id,
        user_id=user_id,
    )
    if design is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el diseño solicitado.")

    request = export_in.model_copy(update={"locale": drawing_export_service.coerce_locale(export_in.locale)})
    job = drawing_export_service.create_export_job(
        db,
        design=design,
        request=request,
        user_id=user_id,
    )
    background_tasks.add_task(drawing_export_service.process_export_job, str(job.job_id))
    return drawing_export_service.serialize_export_job(job)


@router.get("/{job_id}", response_model=DrawingExportJobRead)
def get_export_job(
    *,
    job_id: str,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    job = drawing_export_service.get_job_for_user(
        db,
        job_id=job_id,
        user_id=user_id,
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el job solicitado.")

    return drawing_export_service.serialize_export_job(job)


@router.get("/{job_id}/download")
def download_export_file(
    *,
    job_id: str,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Descargar el archivo exportado."""
    user_id = cast(int, current_user.id)
    job = drawing_export_service.get_job_for_user(
        db,
        job_id=job_id,
        user_id=user_id,
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el job solicitado.")
    
    if job.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo aún no está listo.")
    
    if not job.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay archivo disponible.")
    
    file_path = Path(job.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El archivo ya no existe en el servidor.")
    
    # Determinar el tipo MIME
    mime_types = {
        ".dxf": "application/dxf",
        ".dwg": "application/acad",
        ".pdf": "application/pdf",
        ".svg": "image/svg+xml",
    }
    media_type = mime_types.get(file_path.suffix.lower(), "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
    )
