import re
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.modules.drawing import BeamDrawingService
from app.modules.drawing.domain import DrawingDocument
from app.modules.drawing.drawing_service import serialize_document
from app.modules.drawing.dwg_exporter import DWGExporter
from app.modules.drawing.pdf_exporter import PDFExporter
from app.modules.drawing.preview_renderer import render_svg
from app.schemas.design import DesignCreate, DesignRead
from app.modules.drawing.templates import list_templates
from app.modules.drawing.schemas import BeamDrawingPayload, DrawingExportRequest
from app.services import design_service
from app import models

router = APIRouter(prefix="/designs", tags=["designs"])

DOWNLOAD_ROOT = Path.home() / "Downloads" / "Despieces"
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_-]+")


@router.get("/", response_model=list[DesignRead])
def list_designs(
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    return design_service.list_designs(db, user_id=user_id)


@router.post("/", response_model=DesignRead, status_code=status.HTTP_201_CREATED)
def create_design(
    *,
    design_in: DesignCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    return design_service.create_design(db, design_in=design_in, user_id=user_id)


@router.get("/drawing-templates")
def list_drawing_templates():
    return list_templates()

@router.get("/{design_id}/drawing-payload", response_model=BeamDrawingPayload)
def get_design_drawing_payload(
    *,
    design_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    design = design_service.get_design(db, design_id=design_id, user_id=user_id)
    if design is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el diseño solicitado.",
        )

    try:
        return design_service.build_beam_drawing_payload(design)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{design_id}/drawing-document")
def get_design_drawing_document(
    *,
    design_id: int,
    template: str | None = None,
    locale: str | None = None,
    scale: float | None = None,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    design = design_service.get_design(db, design_id=design_id, user_id=user_id)
    if design is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el diseño solicitado.",
        )

    try:
        payload = design_service.build_beam_drawing_payload(design)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    service = BeamDrawingService(template_key=template)
    request = None
    if template or locale or scale:
        request = DrawingExportRequest(
            design_id=design_id,
            template=template or "beam/default",
            locale=_coerce_locale(locale),
            scale=scale or 50.0,
        )
    document = service.render_document(
        payload,
        template_override=template,
        locale=locale,
        export_request=request,
    )
    return serialize_document(document)


@router.post("/{design_id}/export")
def export_design_drawing(
    *,
    design_id: int,
    export_in: DrawingExportRequest,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    design = design_service.get_design(db, design_id=design_id, user_id=user_id)
    if design is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el diseño solicitado.",
        )

    try:
        payload = design_service.build_beam_drawing_payload(design)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    request = export_in.model_copy(update={"design_id": design_id})
    service = BeamDrawingService(template_key=request.template)
    document = service.render_document(payload, export_request=request)

    destination_dir = _prepare_destination_dir(payload.metadata.project_name)
    filename = _build_export_filename(payload.metadata.beam_label, request.format)

    try:
        file_path = _save_document_to_disk(document, request, destination_dir, filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    response = {
        "format": request.format,
        "template": request.template,
        "scale": request.scale,
        "locale": request.locale,
        "path": str(file_path),
    }

    if request.include_preview and request.format == "svg":
        try:
            response["preview"] = file_path.read_text(encoding="utf-8")
        except OSError:
            response["preview"] = None

    return response


def _coerce_locale(locale: str | None) -> Literal["es-CO", "en-US"]:
    return "en-US" if locale == "en-US" else "es-CO"


def _prepare_destination_dir(project_name: str) -> Path:
    folder_name = _slugify(project_name or "Proyecto")
    destination = DOWNLOAD_ROOT / folder_name
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def _build_export_filename(beam_label: str, draw_format: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(beam_label or "viga")
    extension = _format_extension(draw_format)
    return f"{slug}_{timestamp}.{extension}"


def _format_extension(draw_format: str) -> str:
    mapping = {
        "dwg": "dwg",
        "dxf": "dxf",
        "pdf": "pdf",
        "svg": "svg",
    }
    return mapping.get(draw_format, "dwg")


def _save_document_to_disk(
    document: DrawingDocument,
    request: DrawingExportRequest,
    destination_dir: Path,
    filename: str,
) -> Path:
    if request.format in {"dwg", "dxf"}:
        exporter = DWGExporter()
        return exporter.export(document, filename=filename, output_dir=destination_dir)

    if request.format == "pdf":
        exporter = PDFExporter()
        target_path = destination_dir / filename
        return exporter.export(document, target_path)

    if request.format == "svg":
        target_path = destination_dir / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(render_svg(document), encoding="utf-8")
        return target_path

    raise RuntimeError(f"Formato no soportado: {request.format}")


def _slugify(value: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", value.strip()) if value else ""
    cleaned = cleaned.strip("_")
    return cleaned or "archivo"
