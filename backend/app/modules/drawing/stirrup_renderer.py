from __future__ import annotations

from typing import List

from app.modules.drawing.domain import PolylineEntity
from app.modules.drawing.geometry import to_drawing_units


class StirrupRenderer:
    def __init__(
        self,
        *,
        reference_vertical_scale: float = 6.0,
        marker_height_mm: float = 200.0,
    ) -> None:
        self.reference_vertical_scale = reference_vertical_scale
        self.marker_height_mm = marker_height_mm

    def draw(self, document, context) -> None:
        payload = context.payload
        results = getattr(payload, "detailing_results", None)
        summary = getattr(results, "stirrups_summary", None)
        if not summary:
            return

        layer = context.layer("rebar_stirrups")
        layer_style = context.layer_style("rebar_stirrups")
        center_y = context.origin[1] + (context.beam_height_mm / 2.0)

        for start_x, end_x in self._reference_segments(document, context):
            document.add_entity(
                PolylineEntity(
                    layer=layer,
                    points=[(start_x, center_y), (end_x, center_y)],
                    color=layer_style.color if layer_style else None,
                )
            )

        marker_positions = self._marker_positions(summary, document, context)
        marker_height = self._scaled_value(self.marker_height_mm, context)
        if not marker_positions:
            return

        half_height = marker_height / 2.0
        for x_pos in marker_positions:
            document.add_entity(
                PolylineEntity(
                    layer=layer,
                    points=[(x_pos, center_y - half_height), (x_pos, center_y + half_height)],
                    color=layer_style.color if layer_style else None,
                )
            )

    def _reference_segments(self, document, context) -> List[tuple[float, float]]:
        units = document.units
        origin_x = context.origin[0]
        spans = context.payload.geometry.spans or []
        segments: List[tuple[float, float]] = []

        for span in spans:
            start_x = origin_x + to_drawing_units(float(span.start_m), units)
            end_x = origin_x + to_drawing_units(float(span.end_m), units)
            if end_x > start_x:
                segments.append((start_x, end_x))

        if not segments:
            total_length = to_drawing_units(context.payload.geometry.total_length_m, units)
            segments.append((origin_x, origin_x + total_length))

        return segments

    def _marker_positions(self, summary, document, context) -> List[float]:
        units = document.units
        origin_x = context.origin[0]
        zones = summary.zone_segments or []
        positions: List[float] = []

        for zone in zones:
            positions.append(origin_x + to_drawing_units(float(zone.start_m), units))
            positions.append(origin_x + to_drawing_units(float(zone.end_m), units))

        positions.sort()

        unique_positions: List[float] = []
        tolerance = 0.5
        for pos in positions:
            if not unique_positions or abs(pos - unique_positions[-1]) > tolerance:
                unique_positions.append(pos)

        return unique_positions

    def _scaled_value(self, value: float, context) -> float:
        reference = self.reference_vertical_scale or 1.0
        scale_factor = context.vertical_scale / reference if reference else context.vertical_scale
        scale_factor = max(scale_factor, 0.01)
        return value * scale_factor


__all__ = ["StirrupRenderer"]