from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

from app.modules.drawing.domain import LineEntity, PolylineEntity, TextEntity
from app.modules.drawing.geometry import to_drawing_units
from app.schemas.tools.despiece import RebarDetail


@dataclass(slots=True)
class _PreparedBar:
    bar: RebarDetail
    start_x: float
    end_x: float
    key: int
    quantity: int
    family_id: str
    lane_index: int = 0
    y: float = 0.0


@dataclass(slots=True)
class _GroupAccumulator:
    bar: RebarDetail
    start_x: float
    end_x: float
    quantity: int
    family_id: str


class RebarDrawer:
    def __init__(
        self,
        *,
        top_line_offset_mm: float = 320.0,
        bottom_line_offset_mm: float = 320.0,
        lane_spacing_mm: float = 320.0,
        family_spacing_mm: float = 90.0,
        reference_vertical_scale: float = 6.0,
    ) -> None:
        self.top_line_offset_mm = top_line_offset_mm
        self.bottom_line_offset_mm = bottom_line_offset_mm
        self.lane_spacing_mm = lane_spacing_mm
        self.family_spacing_mm = family_spacing_mm
        self.reference_vertical_scale = reference_vertical_scale

    def draw(self, document, context) -> None:
        results = context.payload.detailing_results
        if not results:
            return

        layer_main = context.layer("rebar_main")
        layer_style = context.layer_style("rebar_main")
        text_style = context.template.text_style("labels")
        lane_spacing = self._lane_spacing(context)
        family_spacing = self._family_spacing(context)

        top_segments = self._prepare_segments(results.top_bars, document, context)
        bottom_segments = self._prepare_segments(results.bottom_bars, document, context)

        self._draw_group(
            document,
            context,
            top_segments,
            base_y=self._base_line_y(context, position="top"),
            direction=-1.0,
            lane_spacing=lane_spacing,
            family_spacing=family_spacing,
            layer=layer_main,
            layer_style=layer_style,
            text_style=text_style,
            position="top",
        )
        self._draw_group(
            document,
            context,
            bottom_segments,
            base_y=self._base_line_y(context, position="bottom"),
            direction=1.0,
            lane_spacing=lane_spacing,
            family_spacing=family_spacing,
            layer=layer_main,
            layer_style=layer_style,
            text_style=text_style,
            position="bottom",
        )

    def _prepare_segments(self, bars, document, context) -> List[_PreparedBar]:
        if not bars:
            return []
        origin_x = context.origin[0]
        grouped: Dict[tuple, _GroupAccumulator] = {}

        for bar in bars:
            if bar.start_m is None or bar.end_m is None:
                continue

            start_x = origin_x + to_drawing_units(bar.start_m, document.units)
            end_x = origin_x + to_drawing_units(bar.end_m, document.units)
            if end_x < start_x:
                start_x, end_x = end_x, start_x

            quantity = int(bar.quantity or 1)
            key = (
                bar.diameter,
                round(bar.start_m or 0.0, 4),
                round(bar.end_m or 0.0, 4),
                round(bar.length_m or 0.0, 4),
                bar.hook_type or "",
            )

            existing = grouped.get(key)
            if existing:
                existing.quantity += quantity
            else:
                grouped[key] = _GroupAccumulator(
                    bar=bar,
                    start_x=start_x,
                    end_x=end_x,
                    quantity=quantity,
                    family_id=self._family_id(bar),
                )

        prepared: List[_PreparedBar] = []
        for idx, accumulator in enumerate(
            sorted(grouped.values(), key=lambda item: (item.start_x, item.end_x))
        ):
            prepared.append(
                _PreparedBar(
                    bar=accumulator.bar,
                    start_x=accumulator.start_x,
                    end_x=accumulator.end_x,
                    key=idx,
                    quantity=accumulator.quantity,
                    family_id=accumulator.family_id,
                )
            )

        return prepared

    def _draw_group(
        self,
        document,
        context,
        segments: List[_PreparedBar],
        *,
        base_y: float,
        direction: float,
        lane_spacing: float,
        family_spacing: float,
        layer: str,
        layer_style,
        text_style,
        position: str,
    ) -> None:
        if not segments:
            return

        assignments = self._assign_lanes(segments)
        family_stack_assignments = self._assign_family_stacks(segments)
        text_layer = context.layer("text")
        text_offset = (12.0 if position == "top" else -18.0) * context.vertical_scale
        family_terminals: Dict[str, Dict[str, _PreparedBar]] = {}
        for segment in segments:
            family = family_terminals.setdefault(segment.family_id, {})
            start_segment = family.get("start")
            if start_segment is None or segment.start_x < start_segment.start_x:
                family["start"] = segment
            end_segment = family.get("end")
            if end_segment is None or segment.end_x > end_segment.end_x:
                family["end"] = segment
        family_base_lane: Dict[str, int] = {}
        for segment in segments:
            lane_index = assignments.get(segment.key, 0)
            current_base = family_base_lane.get(segment.family_id)
            if current_base is None or lane_index < current_base:
                family_base_lane[segment.family_id] = lane_index

        geometry = context.payload.geometry
        for segment in segments:
            lane_index = assignments.get(segment.key, 0)
            family_base = family_base_lane.get(segment.family_id, lane_index)
            stack_index = family_stack_assignments.get(segment.key)
            if stack_index is None:
                stack_index = max(0, lane_index - family_base)
            offset = lane_spacing * family_base + family_spacing * stack_index
            y = base_y + direction * offset
            segment.lane_index = lane_index
            segment.y = y
            bar = segment.bar
            terminals = family_terminals.get(segment.family_id, {})
            force_start = terminals.get("start") is segment
            force_end = terminals.get("end") is segment
            document.add_entity(
                LineEntity(
                    layer=layer,
                    start=(segment.start_x, y),
                    end=(segment.end_x, y),
                    color=layer_style.color if layer_style else None,
                )
            )

            self._draw_hooks(
                document,
                context,
                segment,
                layer=layer,
                layer_style=layer_style,
                direction=direction,
                geometry=geometry,
                draw_start=force_start,
                draw_end=force_end,
            )

            label = f"{segment.quantity}Φ{bar.diameter} L={bar.length_m:.2f}m"
            mid_x = (segment.start_x + segment.end_x) / 2.0
            text_position = (mid_x, y + text_offset)
            document.add_entity(
                TextEntity(
                    layer=text_layer,
                    content=label,
                    insert=text_position,
                    height=context.text_height_mm,
                    style=text_style.name,
                    metadata={
                        "halign": 1,
                        "valign": 2,
                        "align": "MIDDLE",
                        "align_point": text_position,
                    },
                )
            )

    def _assign_lanes(self, segments: List[_PreparedBar]) -> Dict[int, int]:
        assignments: Dict[int, int] = {}
        lane_ends: List[float] = []
        tolerance = 1e-3
        for item in sorted(segments, key=lambda s: (s.start_x, s.end_x)):
            lane_idx = None
            for idx, current_end in enumerate(lane_ends):
                if item.start_x >= current_end - tolerance:
                    lane_idx = idx
                    lane_ends[idx] = item.end_x
                    break
            if lane_idx is None:
                lane_ends.append(item.end_x)
                lane_idx = len(lane_ends) - 1
            assignments[item.key] = lane_idx
        return assignments

    def _assign_family_stacks(self, segments: List[_PreparedBar]) -> Dict[int, int]:
        stacks: Dict[int, int] = {}
        families: Dict[str, List[_PreparedBar]] = defaultdict(list)
        for segment in segments:
            families[segment.family_id].append(segment)

        for family_segments in families.values():
            if len(family_segments) <= 1:
                continue
            family_assignments = self._assign_lanes(family_segments)
            if not family_assignments:
                continue
            min_lane = min(family_assignments.values())
            for seg in family_segments:
                stacks[seg.key] = family_assignments.get(seg.key, min_lane) - min_lane
        return stacks

    def _lane_spacing(self, context) -> float:
        spacing = self._scaled_value(self.lane_spacing_mm, context)
        return max(spacing, 1.0)

    def _family_spacing(self, context) -> float:
        spacing = self._scaled_value(self.family_spacing_mm, context)
        return max(spacing, 0.0)

    def _base_line_y(self, context, *, position: str) -> float:
        base_offset = self.top_line_offset_mm if position == "top" else self.bottom_line_offset_mm
        offset_mm = self._scaled_value(base_offset, context)
        if position == "top":
            return context.origin[1] + context.beam_height_mm - offset_mm
        return context.origin[1] + offset_mm

    def _scaled_value(self, value: float, context) -> float:
        reference = self.reference_vertical_scale or 1.0
        scale_factor = context.vertical_scale / reference if reference else context.vertical_scale
        scale_factor = max(scale_factor, 0.01)
        return value * scale_factor

    @staticmethod
    def _family_id(bar: RebarDetail) -> str:
        identifier = bar.id or ""
        return re.sub(r"-S\d+$", "", identifier)

    def _draw_hooks(
        self,
        document,
        context,
        segment: _PreparedBar,
        *,
        layer: str,
        layer_style,
        direction: float,
        geometry,
        draw_start: bool,
        draw_end: bool,
    ) -> None:
        bar = segment.bar
        hook_type = (bar.hook_type or "").strip()
        if hook_type not in {"90", "135", "180"}:
            return

        should_draw_start = draw_start and (
            self._is_near_support(bar.start_m, geometry, position="start")
            or self._notes_force_hook(bar, position="start")
        )
        should_draw_end = draw_end and (
            self._is_near_support(bar.end_m, geometry, position="end")
            or self._notes_force_hook(bar, position="end")
        )

        if not should_draw_start and not should_draw_end:
            return

        hook_length = self._hook_length_mm(bar, context)
        if hook_length <= 0:
            return

        vertical_clearance = self.lane_spacing_mm - self.family_spacing_mm
        vertical_amplitude = min(vertical_clearance * 0.4, 80.0)
        vertical_amplitude = self._scaled_value(vertical_amplitude, context)
        y = segment.y

        actions = []
        if should_draw_start:
            actions.append((segment.start_x, 1))
        if should_draw_end:
            actions.append((segment.end_x, -1))

        for origin_x, orientation in actions:
            vector = self._hook_vector(hook_type, orientation)
            dx = hook_length * vector[0]
            dy = hook_length * vector[1] * direction
            dy = max(min(dy, vertical_amplitude), -vertical_amplitude)
            document.add_entity(
                PolylineEntity(
                    layer=layer,
                    points=[
                        (origin_x, y),
                        (origin_x + dx * 0.35, y + dy * 0.5),
                        (origin_x + dx, y + dy),
                    ],
                    color=layer_style.color if layer_style else None,
                )
            )

            hook_text = f"{hook_length:.0f}"
            text_layer = context.layer("text")
            text_style = context.template.text_style("labels")
            text_pos = (origin_x + dx * 0.65, y + dy * 1.15)
            document.add_entity(
                TextEntity(
                    layer=text_layer,
                    content=hook_text,
                    insert=text_pos,
                    height=context.text_height_mm,
                    style=text_style.name,
                )
            )

    @staticmethod
    def _hook_vector(hook_type: str, orientation: int) -> tuple[float, float]:
        if hook_type == "180":
            return (-orientation, 0.0)
        if hook_type == "90":
            return (0.0, orientation)
        # 135 default
        return (-orientation * 0.45, orientation * 0.85)

    def _hook_length_mm(self, bar: RebarDetail, context) -> float:
        length_m = self._lookup_hook_length_m(bar)
        if length_m <= 0:
            return 0.0
        units = getattr(context.payload, "drawing_units", None)
        scale = getattr(units, "scale_factor", 1000.0) or 1000.0
        return length_m * scale

    def _lookup_hook_length_m(self, bar: RebarDetail) -> float:
        table = {
            "#2": {"90": 0.10, "180": 0.080, "135": 0.075},
            "#3": {"90": 0.15, "180": 0.130, "135": 0.080},
            "#4": {"90": 0.20, "180": 0.150, "135": 0.127},
            "#5": {"90": 0.25, "180": 0.180, "135": 0.159},
            "#6": {"90": 0.30, "180": 0.210, "135": 0.191},
            "#7": {"90": 0.36, "180": 0.250, "135": 0.222},
            "#8": {"90": 0.41, "180": 0.300, "135": 0.254},
            "#9": {"90": 0.49, "180": 0.340, "135": None},
            "#10": {"90": 0.54, "180": 0.400, "135": None},
            "#11": {"90": 0.59, "180": 0.430, "135": None},
            "#14": {"90": 0.80, "180": 0.445, "135": None},
            "#18": {"90": 1.03, "180": 0.572, "135": None},
        }
        lengths = table.get(bar.diameter or "")
        if not lengths:
            return 0.0
        value = lengths.get(bar.hook_type or "")
        return float(value or 0.0)

    @staticmethod
    def _support_threshold_m(geometry, *, position: str) -> float:
        supports = getattr(geometry, "supports", None) or []
        if not supports:
            return 0.45
        support = supports[0] if position == "start" else supports[-1]
        width = getattr(support, "width_m", None) or 0.35
        return max(0.25, min(width * 1.2, 0.6))

    @staticmethod
    def _geometry_length(geometry) -> float | None:
        if geometry is None:
            return None
        total = getattr(geometry, "total_length_m", None)
        if total:
            return float(total)
        supports = getattr(geometry, "supports", None)
        if supports:
            last = supports[-1]
            end = getattr(last, "end_m", None)
            if end is not None:
                return float(end)
        spans = getattr(geometry, "spans", None)
        if spans:
            last_span = spans[-1]
            end = getattr(last_span, "end_m", None)
            if end is not None:
                return float(end)
        return None

    def _is_near_support(self, coordinate_m: float | None, geometry, *, position: str) -> bool:
        if coordinate_m is None:
            return False
        threshold = self._support_threshold_m(geometry, position=position)
        if position == "start":
            return coordinate_m <= threshold
        beam_length = self._geometry_length(geometry)
        if beam_length is None:
            return False
        return (beam_length - coordinate_m) <= threshold

    @staticmethod
    def _notes_force_hook(bar: RebarDetail, *, position: str) -> bool:
        note = (bar.notes or "").lower()
        if "apoyo" not in note:
            return False
        if position == "start":
            return any(token in note for token in ("izq", "izquier", "inicio", "left"))
        return any(token in note for token in ("der", "derech", "final", "right"))


__all__ = ["RebarDrawer"]
