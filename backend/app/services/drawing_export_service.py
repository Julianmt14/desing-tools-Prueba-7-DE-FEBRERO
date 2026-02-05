from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

from sqlalchemy.orm import Session, selectinload

from app import models
from app.core.database import SessionLocal
from app.modules.drawing import BeamDrawingService
from app.modules.drawing.domain import DrawingDocument
from app.modules.drawing.dwg_exporter import DWGExporter
from app.modules.drawing.pdf_exporter import PDFExporter
from app.modules.drawing.preview_renderer import render_svg
from app.modules.drawing.schemas.drawing import BeamDrawingPayload, DrawingExportRequest
from app.services import design_service

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

DOWNLOAD_ROOT = Path.home() / "Downloads" / "Despieces"
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
_RETENTION_DAYS = 14
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_-]+")


@dataclass(slots=True)
class ExportFileResult:
    file_path: Path
    preview_path: Path | None = None
    inline_preview: str | None = None


def coerce_locale(locale: str | None) -> Literal["es-CO", "en-US"]:
    return "en-US" if locale == "en-US" else "es-CO"


def prepare_destination_dir(project_name: str | None) -> Path:
    folder_name = _slugify(project_name or "Proyecto")
    destination = DOWNLOAD_ROOT / folder_name
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def build_export_filename(beam_label: str | None, draw_format: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(beam_label or "viga")
    extension = _format_extension(draw_format)
    return f"{slug}_{timestamp}.{extension}"


def generate_export_for_design(
    design: models.Design,
    request: DrawingExportRequest,
) -> ExportFileResult:
    logger.info(
        "[Export] Generando plano | design_id=%s format=%s template=%s scale=1:%s",
        design.id,
        request.format,
        request.template,
        request.scale,
    )
    payload = design_service.build_beam_drawing_payload(design)
    document = _render_document(payload, request)
    destination_dir = prepare_destination_dir(payload.metadata.project_name)
    filename = build_export_filename(payload.metadata.beam_label, request.format)
    file_path = _save_document_to_disk(document, request, destination_dir, filename)
    preview_path: Path | None = None
    inline_preview: str | None = None

    if request.include_preview:
        if request.format == "svg":
            preview_path = file_path
            inline_preview = _safe_read(preview_path)
        else:
            preview_name = Path(filename).with_suffix(".svg").name
            preview_path = destination_dir / preview_name
            preview_path.write_text(render_svg(document), encoding="utf-8")

    logger.info(
        "[Export] Plano generado | design_id=%s format=%s path=%s",
        design.id,
        request.format,
        file_path,
    )
    return ExportFileResult(file_path=file_path, preview_path=preview_path, inline_preview=inline_preview)


def create_export_job(
    db: Session,
    *,
    design: models.Design,
    request: DrawingExportRequest,
    user_id: int,
) -> models.DesignExport:
    logger.info(
        "[Export] Creando job | design_id=%s user_id=%s template=%s format=%s",
        design.id,
        user_id,
        request.template,
        request.format,
    )
    job = models.DesignExport(
        job_id=str(uuid.uuid4()),
        design_id=design.id,
        user_id=user_id,
        template=request.template,
        format=request.format,
        scale=request.scale,
        locale=request.locale,
        include_preview=request.include_preview,
        status="queued",
        expires_at=datetime.now(timezone.utc) + timedelta(days=_RETENTION_DAYS),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("[Export] Job encolado | job_id=%s status=%s", job.job_id, job.status)
    return job


def get_job_for_user(db: Session, *, job_id: str, user_id: int) -> models.DesignExport | None:
    return (
        db.query(models.DesignExport)
        .options(selectinload(models.DesignExport.design))
        .filter(models.DesignExport.job_id == job_id, models.DesignExport.user_id == user_id)
        .first()
    )


def serialize_export_job(job: models.DesignExport) -> dict:
    job_id_str = str(job.job_id) if job.job_id else None
    return {
        "job_id": job.job_id,
        "design_id": job.design_id,
        "format": job.format,
        "template": job.template,
        "scale": job.scale,
        "locale": job.locale,
        "include_preview": job.include_preview,
        "status": job.status,
        "file_path": job.file_path,
        "preview_path": job.preview_path,
        "download_url": _path_to_url(job.file_path, job_id_str),
        "preview_url": _path_to_url(job.preview_path, job_id_str),
        "expires_at": job.expires_at,
        "message": job.message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def process_export_job(job_id: str) -> None:
    db = SessionLocal()
    job: Optional[models.DesignExport] = None
    try:
        job = (
            db.query(models.DesignExport)
            .options(selectinload(models.DesignExport.design).selectinload(models.Design.beam_despiece))
            .filter(models.DesignExport.job_id == job_id)
            .first()
        )
        if job is None:
            logger.warning("No se encontró el job de exportación %s", job_id)
            return

        job.status = "processing"
        job.message = None
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        logger.info("[Export] Job en ejecución | job_id=%s", job.job_id)

        design = job.design
        if design is None:
            raise RuntimeError("El diseño asociado a la exportación ya no existe")

        request = DrawingExportRequest(
            design_id=job.design_id,
            format=job.format,
            template=job.template,
            scale=job.scale,
            locale=job.locale,
            include_preview=job.include_preview,
        )
        result = generate_export_for_design(design, request)
        job.file_path = str(result.file_path)
        job.preview_path = str(result.preview_path) if result.preview_path else None
        job.status = "completed"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("[Export] Job completado | job_id=%s output=%s", job.job_id, job.file_path)
    except Exception as exc:  # pragma: no cover - fallbacks de runtime
        logger.exception("Falló el job de exportación %s", job_id)
        db.rollback()
        if job is not None:
            job.status = "failed"
            job.message = str(exc)
            job.updated_at = datetime.now(timezone.utc)
            db.add(job)
            db.commit()
    finally:
        db.close()


def _render_document(payload: BeamDrawingPayload, request: DrawingExportRequest) -> DrawingDocument:
    service = BeamDrawingService(template_key=request.template)
    return service.render_document(payload, export_request=request)


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


def _path_to_url(path_str: str | None, job_id: str | None = None) -> str | None:
    """Genera la URL de descarga a través de la API."""
    if not path_str or not job_id:
        return None
    # Retorna la URL relativa del endpoint de descarga
    return f"/api/v1/drawing/exports/{job_id}/download"


def _format_extension(draw_format: str) -> str:
    mapping = {
        "dwg": "dwg",
        "dxf": "dxf",
        "pdf": "pdf",
        "svg": "svg",
    }
    return mapping.get(draw_format, "dwg")


def _slugify(value: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", value.strip()) if value else ""
    cleaned = cleaned.strip("_")
    return cleaned or "archivo"


def _safe_read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


__all__ = [
    "ExportFileResult",
    "DOWNLOAD_ROOT",
    "build_export_filename",
    "coerce_locale",
    "create_export_job",
    "generate_export_for_design",
    "get_job_for_user",
    "prepare_destination_dir",
    "process_export_job",
    "serialize_export_job",
]
