from __future__ import annotations

from typing import List

from app.modules.drawing.domain import PolylineEntity, TextEntity
from app.modules.drawing.geometry import to_drawing_units


class StirrupRenderer:
    def __init__(
        self,
        *,
        reference_vertical_scale: float = 6.0,
        marker_height_mm: float = 200.0,
        annotation_offset_mm: float = 200.0,
        short_zone_threshold_m: float = 0.5,
    ) -> None:
        self.reference_vertical_scale = reference_vertical_scale
        self.marker_height_mm = marker_height_mm
        self.annotation_offset_mm = annotation_offset_mm
        self.short_zone_threshold_m = short_zone_threshold_m

    def draw(self, document, context) -> None:
        payload = context.payload
        results = getattr(payload, "detailing_results", None)
        summary = getattr(results, "stirrups_summary", None)
        if not summary:
            return

        zones = summary.zone_segments or []
        if not zones:
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

        self._draw_zone_labels(document, context, zones, layer, center_y)

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

    def _draw_zone_labels(self, document, context, zones, layer: str, center_y: float) -> None:
        text_style = context.template.text_style("labels")
        offset = self._scaled_value(self.annotation_offset_mm, context)
        text_height = max(context.text_height_mm * 0.6, 60.0)
        units = document.units
        origin_x = context.origin[0]

        for zone in zones:
            count = self._safe_int(zone.estimated_count)
            spacing_cm = self._format_spacing(zone.spacing_m)
            start_m = float(getattr(zone, "start_m", 0.0))
            end_m = float(getattr(zone, "end_m", start_m))

            if count is None or spacing_cm is None or end_m <= start_m:
                continue

            center_m = (start_m + end_m) / 2.0
            center_x = origin_x + to_drawing_units(center_m, units)
            content = f"{count}E C/{spacing_cm}"
            zone_length = end_m - start_m
            is_short_zone = zone_length <= self.short_zone_threshold_m
            vertical_sign = 1.0 if is_short_zone else -1.0
            insert_point = (center_x, center_y + (vertical_sign * offset))
            document.add_entity(
                TextEntity(
                    layer=layer,
                    content=content,
                    insert=insert_point,
                    height=text_height,
                    style=text_style.name,
                    metadata={
                        "halign": 1,  # center
                        "align_point": insert_point,
                    },
                )
            )

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

    def _format_spacing(self, spacing_m: float | None) -> str | None:
        if spacing_m is None:
            return None
        try:
            spacing_cm = float(spacing_m) * 100.0
        except (TypeError, ValueError):
            return None
        if spacing_cm <= 0:
            return None
        formatted = f"{spacing_cm:.1f}".rstrip("0").rstrip(".")
        return formatted or "0"

    def _safe_int(self, value) -> int | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number <= 0:
            return None
        return int(round(number))

    def _scaled_value(self, value: float, context) -> float:
        reference = self.reference_vertical_scale or 1.0
        scale_factor = context.vertical_scale / reference if reference else context.vertical_scale
        scale_factor = max(scale_factor, 0.01)
        return value * scale_factor


__all__ = ["StirrupRenderer"]