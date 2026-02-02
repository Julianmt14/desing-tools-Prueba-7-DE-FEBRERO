from __future__ import annotations

from pathlib import Path
import importlib

svg2rlg = None
renderPDF = None

from app.modules.drawing.domain import DrawingDocument
from app.modules.drawing.preview_renderer import render_svg


class PDFExporter:
    def __init__(self, *, fallback_to_svg: bool = True) -> None:
        self.fallback_to_svg = fallback_to_svg

    def export(self, document: DrawingDocument, target_path: Path) -> Path:
        _load_dependencies()
        if svg2rlg is None or renderPDF is None:
            if not self.fallback_to_svg:
                raise RuntimeError("svglib/reportlab no están disponibles")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(render_svg(document), encoding="utf-8")
            return target_path

        svg_content = render_svg(document)
        temp_svg = target_path.with_suffix(".svg")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_svg.write_text(svg_content, encoding="utf-8")
        drawing = svg2rlg(str(temp_svg))
        renderPDF(drawing, str(target_path))
        temp_svg.unlink(missing_ok=True)
        return target_path


def _load_dependencies() -> None:
    global svg2rlg, renderPDF
    if svg2rlg is not None and renderPDF is not None:
        return
    try:
        svg2rlg = getattr(importlib.import_module("svglib.svglib"), "svg2rlg")
        renderPDF_module = importlib.import_module("reportlab.graphics.renderPDF")
        renderPDF = getattr(renderPDF_module, "drawToFile")
    except ModuleNotFoundError:  # pragma: no cover
        svg2rlg = None
        renderPDF = None


__all__ = ["PDFExporter"]
