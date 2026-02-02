from __future__ import annotations

import importlib
import io
from typing import Tuple

_SVGWRITE = None

from app.modules.drawing.domain import (
    DimensionEntity,
    DrawingDocument,
    DrawingEntity,
    HatchEntity,
    LineEntity,
    PolylineEntity,
    TextEntity,
)


def _ensure_svgwrite():
    global _SVGWRITE
    if _SVGWRITE is None:
        try:
            _SVGWRITE = importlib.import_module("svgwrite")
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("svgwrite no está instalado en el entorno actual") from exc
    return _SVGWRITE


def render_svg(document: DrawingDocument) -> str:
    svgwrite = _ensure_svgwrite()
    width = max((point[0] for entity in document.entities for point in _points(entity)), default=1000) + 100
    height = max((point[1] for entity in document.entities for point in _points(entity)), default=400) + 100
    svg = svgwrite.Drawing(size=(f"{width}px", f"{height}px"))
    for entity in document.entities:
        if isinstance(entity, PolylineEntity):
            svg.add(
                svgwrite.shapes.Polyline(
                    points=list(entity.points),
                    fill="none",
                    stroke=_layer_color(entity.layer),
                    stroke_width=_lineweight(entity.lineweight),
                )
            )
        elif isinstance(entity, LineEntity):
            svg.add(
                svgwrite.shapes.Line(
                    start=entity.start,
                    end=entity.end,
                    stroke=_layer_color(entity.layer),
                    stroke_width=_lineweight(entity.lineweight),
                )
            )
        elif isinstance(entity, TextEntity):
            svg.add(
                svgwrite.text.Text(
                    entity.content,
                    insert=entity.insert,
                    fill=_layer_color(entity.layer),
                    font_size=f"{entity.height}px",
                )
            )
        elif isinstance(entity, HatchEntity):
            svg.add(
                svgwrite.shapes.Polygon(
                    points=list(entity.boundary),
                    fill="#dddddd",
                    stroke="none",
                )
            )
        elif isinstance(entity, DimensionEntity):
            svg.add(
                svgwrite.shapes.Line(
                    start=entity.start,
                    end=entity.end,
                    stroke="#888",
                    stroke_width=1,
                )
            )
            if entity.text_override:
                svg.add(
                    svgwrite.text.Text(
                        entity.text_override,
                        insert=((entity.start[0] + entity.end[0]) / 2, entity.start[1] - 5),
                        fill="#555",
                        font_size="10px",
                    )
                )
    buffer = io.StringIO()
    svg.write(buffer)
    return buffer.getvalue()


def _layer_color(layer: str) -> str:
    palette = {
        "C-VIGA": "#222222",
        "C-VIGA-HATCH": "#999999",
        "C-APOYO": "#555555",
        "C-EJES": "#1f77b4",
        "A-REB-MAIN": "#d62728",
        "A-REB-EST": "#ff7f0e",
        "C-COTAS": "#9467bd",
        "C-TEXT": "#111111",
        "A-CART": "#222222",
    }
    return palette.get(layer, "#333333")


def _lineweight(value: float | None) -> float:
    if value is None:
        return 1.0
    return max(0.5, value)


def _points(entity: DrawingEntity) -> Tuple[Tuple[float, float], ...]:
    def _clean(points):
        return tuple(point for point in points if point is not None)

    if isinstance(entity, PolylineEntity):
        return _clean(entity.points)
    if isinstance(entity, LineEntity):
        return _clean((entity.start, entity.end))
    if isinstance(entity, HatchEntity):
        return _clean(entity.boundary)
    if isinstance(entity, DimensionEntity):
        return _clean((entity.start, entity.end))
    if isinstance(entity, TextEntity):
        return _clean((entity.insert,))
    return tuple()


__all__ = ["render_svg"]
