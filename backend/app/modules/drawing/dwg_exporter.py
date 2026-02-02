from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path
from typing import Any, Sequence

_EZDXF_MODULE: Any | None = None
_DXF_UNITS: Any | None = None
LINEWEIGHT_MAP: dict[float, int] = {}


def _ensure_ezdxf():
    global _EZDXF_MODULE, _DXF_UNITS, LINEWEIGHT_MAP
    if _EZDXF_MODULE is None or _DXF_UNITS is None:
        try:
            _EZDXF_MODULE = importlib.import_module("ezdxf")
            _DXF_UNITS = importlib.import_module("ezdxf.units")
            const_mod = importlib.import_module("ezdxf.lldxf.const")
            LINEWEIGHT_MAP = dict(getattr(const_mod, "LINEWEIGHT_TO_DXU", {}))
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("ezdxf no está instalado en el entorno actual") from exc
    return _EZDXF_MODULE, _DXF_UNITS

from app.modules.drawing.domain import (
    DimensionEntity,
    DrawingDocument,
    DrawingEntity,
    HatchEntity,
    LineEntity,
    PolylineEntity,
    TextEntity,
)

EXPORT_DIR = Path(os.getenv("DRAWING_EXPORT_DIR", Path(tempfile.gettempdir()) / "exports"))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class DWGExporter:
    def __init__(self, *, version: str = "R2018") -> None:
        self.version = version

    def export(
        self,
        document: DrawingDocument,
        filename: str | None = None,
        output_dir: Path | None = None,
    ) -> Path:
        ezdxf_mod, dxf_units_mod = _ensure_ezdxf()
        target_dir = Path(output_dir) if output_dir else EXPORT_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_name = filename or f"drawing_{document.metadata.get('beam', {}).get('beam_label', 'beam')}.dxf"
        target_path = target_dir / safe_name

        dxf_doc = ezdxf_mod.new(self.version)
        dxf_doc.units = dxf_units_mod.MM
        self._configure_layers(dxf_doc, document)
        msp = dxf_doc.modelspace()

        for entity in document.entities:
            self._add_entity(msp, entity)

        dxf_doc.saveas(target_path)
        return target_path

    def _add_entity(self, msp, entity: DrawingEntity) -> None:
        if isinstance(entity, PolylineEntity):
            msp.add_lwpolyline(entity.points, format="xy", dxfattribs=self._attribs(entity))
        elif isinstance(entity, LineEntity):
            msp.add_line(entity.start, entity.end, dxfattribs=self._attribs(entity))
        elif isinstance(entity, TextEntity):
            msp.add_text(entity.content, height=entity.height, dxfattribs={
                "layer": entity.layer,
                "style": entity.style,
                "rotation": entity.rotation,
            }).set_pos(entity.insert)
        elif isinstance(entity, HatchEntity):
            hatch = msp.add_hatch(pattern=entity.pattern, color=7)
            hatch.paths.add_polyline_path(entity.boundary, is_closed=True)
            hatch.dxf.layer = entity.layer
            hatch.dxf.pattern_scale = entity.scale
        elif isinstance(entity, DimensionEntity):
            dim = msp.add_linear_dim(
                base_point=entity.start,
                p1=entity.start,
                p2=entity.end,
                distance=entity.offset,
                override={"dimclrd": 4},
            )
            if entity.text_override:
                dim.override("dimtxt", 0)
                dim.set_text(entity.text_override)
            dim.render()

    def _configure_layers(self, dxf_doc, document: DrawingDocument) -> None:
        for entity in document.entities:
            layer = entity.layer
            if layer not in dxf_doc.layers:
                dxf_doc.layers.add(name=layer, color=7)

    def _attribs(self, entity) -> dict:
        attribs = {"layer": entity.layer}
        if getattr(entity, "color", None):
            attribs["color"] = entity.color
        if getattr(entity, "lineweight", None) and LINEWEIGHT_MAP:
            attribs["lineweight"] = LINEWEIGHT_MAP.get(entity.lineweight, 25)
        return attribs


__all__ = ["DWGExporter", "EXPORT_DIR"]
