from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, cast

from app.schemas.tools.despiece import ProhibitedZone, RebarDetail
from app.services.detailing.logger import detailing_logger as logger

if TYPE_CHECKING:
    from app.services.detailing_service import BeamDetailingService


class SegmentationMixin:
    def _split_bar_by_max_length(
        self,
        bar: RebarDetail,
        *,
        max_length: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
        hook_length: float,
        edge_cover: float,
        beam_length: float,
        prefer_previous_zone: bool = False,
        splice_offset_ratio: float = 0.0,
        is_bottom_bar: bool = False,
    ) -> List[RebarDetail]:
        if max_length <= 0 or bar.length_m <= max_length:
            return [bar]

        if splice_length <= 0 or splice_length >= max_length:
            logger.warning(
                "No se puede segmentar la barra %s porque splice %.2f >= Lmax %.2f",
                bar.id,
                splice_length,
                max_length,
            )
            return [bar]

        if is_bottom_bar:
            return self._split_bottom_bar_strategy(
                bar=bar,
                max_length=max_length,
                splice_length=splice_length,
                prohibited_zones=prohibited_zones,
                hook_length=hook_length,
                edge_cover=edge_cover,
                beam_length=beam_length,
                splice_offset_ratio=splice_offset_ratio,
            )

        return self._split_top_bar_strategy(
            bar=bar,
            max_length=max_length,
            splice_length=splice_length,
            prohibited_zones=prohibited_zones,
            hook_length=hook_length,
            edge_cover=edge_cover,
            beam_length=beam_length,
            prefer_previous_zone=prefer_previous_zone,
        )

    def _split_top_bar_strategy(
        self,
        *,
        bar: RebarDetail,
        max_length: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
        hook_length: float,
        edge_cover: float,
        beam_length: float,
        prefer_previous_zone: bool = False,
    ) -> List[RebarDetail]:
        service = cast("BeamDetailingService", self)
        cover = max(service.min_edge_cover_m, edge_cover or 0.0)
        tolerance = 1e-3
        has_start_hook = bool(hook_length and bar.start_m <= cover + tolerance)
        has_end_hook = bool(
            hook_length and bar.end_m >= beam_length - cover - tolerance
        )

        segments: List[RebarDetail] = []
        joints: List[Dict[str, Any]] = []
        current_start = bar.start_m
        piece_index = 1
        safety_counter = 0

        while current_start < bar.end_m - 1e-6 and safety_counter < 100:
            safety_counter += 1
            remaining_length = max(bar.end_m - current_start, 0.0)
            if remaining_length <= 0:
                break

            hook_deduction = 0.0
            if has_start_hook and piece_index == 1:
                hook_deduction += hook_length
            if has_end_hook and remaining_length <= max_length + tolerance:
                hook_deduction += hook_length

            usable_max = max_length - hook_deduction
            if usable_max <= 0:
                logger.warning(
                    "La barra %s no puede segmentarse porque los ganchos consumen la longitud máxima",
                    bar.id,
                )
                usable_max = max_length

            segment_length = min(usable_max, remaining_length)
            if piece_index == 1 and remaining_length > max_length * 1.8:
                segment_length = min(usable_max * 0.6, remaining_length)

            candidate_end = current_start + segment_length
            is_last_segment = candidate_end >= bar.end_m - tolerance

            if (
                prefer_previous_zone
                and not is_last_segment
                and splice_length > 0
            ):
                joint_start_candidate = max(bar.start_m, candidate_end - splice_length)
                remaining_after_joint = bar.end_m - joint_start_candidate
                if remaining_after_joint <= max_length + tolerance:
                    preferred_end = self._prefer_splice_in_previous_corridor(
                        current_start=current_start,
                        joint_start=joint_start_candidate,
                        candidate_end=candidate_end,
                        splice_length=splice_length,
                        prohibited_zones=prohibited_zones,
                    )
                    if preferred_end < candidate_end - tolerance:
                        candidate_end = preferred_end
                        segment_length = candidate_end - current_start
                        is_last_segment = candidate_end >= bar.end_m - tolerance

            if is_last_segment:
                segment_end = bar.end_m
            else:
                segment_end = self._adjust_segment_end_for_splice_zones(
                    current_start,
                    candidate_end,
                    splice_length,
                    prohibited_zones,
                )

            length = segment_end - current_start
            if length <= 0:
                break

            segment = RebarDetail(
                id=f"{bar.id}-S{piece_index:02d}",
                diameter=bar.diameter,
                position=bar.position,
                type=bar.type,
                length_m=length,
                start_m=current_start,
                end_m=segment_end,
                hook_type=bar.hook_type,
                splices=None,
                quantity=bar.quantity,
                development_length_m=bar.development_length_m,
                notes=f"Segmento {piece_index} - Superior",
            )
            segments.append(segment)

            if segment_end >= bar.end_m - 1e-6:
                break

            joint_start = max(bar.start_m, segment_end - splice_length)
            joint_end = segment_end

            if self._overlaps_prohibited_zone(joint_start, joint_end, prohibited_zones):
                logger.warning(
                    "No se pudo ubicar el empalme de la barra %s fuera de zonas prohibidas",
                    bar.id,
                )

            joints.append(
                {
                    "start": joint_start,
                    "end": joint_end,
                    "length": joint_end - joint_start,
                    "type": "lap_splice_class_b",
                    "position": "top",
                }
            )

            current_start = joint_start
            piece_index += 1

        if safety_counter >= 100:
            logger.warning("Se alcanzó el límite de segmentación para la barra %s", bar.id)

        if not segments:
            return [bar]

        for idx, segment in enumerate(segments):
            segment_splices: List[Dict[str, Any]] = []
            if idx > 0:
                segment_splices.append(joints[idx - 1])
            if idx < len(joints):
                segment_splices.append(joints[idx])
            segment.splices = segment_splices or None

        return segments

    def _split_bottom_bar_strategy(
        self,
        *,
        bar: RebarDetail,
        max_length: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
        hook_length: float,
        edge_cover: float,
        beam_length: float,
        splice_offset_ratio: float = 0.0,
    ) -> List[RebarDetail]:
        logger.info(
            "Dividiendo barra inferior %s con longitud total %.2fm",
            bar.id,
            bar.length_m,
        )
        logger.info("Offset ratio inferior aplicado: %.3f", splice_offset_ratio or 0.0)

        service = cast("BeamDetailingService", self)
        cover = max(service.min_edge_cover_m, edge_cover or 0.0)
        tolerance = 1e-3
        has_start_hook = bool(hook_length and bar.start_m <= cover + tolerance)
        has_end_hook = bool(hook_length and bar.end_m >= beam_length - cover - tolerance)

        total_length = max(bar.end_m - bar.start_m, 0.0)
        offset_ratio = max(0.0, min(splice_offset_ratio or 0.0, 0.6))
        if offset_ratio > tolerance:
            first_segment_target = min(total_length * (0.4 + offset_ratio * 0.5), max_length)
        else:
            first_segment_target = min(total_length * 0.45, max_length * 0.8)
        first_segment_target = max(first_segment_target, splice_length * 1.5)
        first_segment_target = min(first_segment_target, total_length)

        segments: List[RebarDetail] = []
        joints: List[Dict[str, Any]] = []
        current_start = bar.start_m
        piece_index = 1
        safety_counter = 0
        logged_first_segment = False

        while current_start < bar.end_m - 1e-6 and safety_counter < 100:
            safety_counter += 1
            remaining_length = max(bar.end_m - current_start, 0.0)
            if remaining_length <= 0:
                break

            hook_deduction = 0.0
            if has_start_hook and piece_index == 1:
                hook_deduction += hook_length
            if has_end_hook and remaining_length <= max_length + tolerance:
                hook_deduction += hook_length

            usable_max = max_length - hook_deduction
            if usable_max <= 0:
                logger.warning(
                    "La barra %s no puede segmentarse porque los ganchos consumen la longitud máxima",
                    bar.id,
                )
                usable_max = max_length

            segment_length = min(usable_max, remaining_length)
            if piece_index == 1:
                segment_length = min(segment_length, first_segment_target)

            candidate_end = current_start + segment_length
            candidate_end = min(candidate_end, bar.end_m)
            is_last_segment = candidate_end >= bar.end_m - tolerance

            needs_zone_adjustment = True
            corridor_target = None
            if piece_index == 1 and not is_last_segment:
                corridor_target = self._target_bottom_corridor_end(
                    current_start=current_start,
                    candidate_end=candidate_end,
                    splice_length=splice_length,
                    prohibited_zones=prohibited_zones,
                )
                if corridor_target is not None:
                    candidate_end = min(bar.end_m, corridor_target)
                    is_last_segment = candidate_end >= bar.end_m - tolerance
                    needs_zone_adjustment = False
                    logger.info(
                        "Barra %s: empalme dirigido al corredor previo en %.2fm",
                        bar.id,
                        candidate_end,
                    )

            if piece_index == 1 and not is_last_segment and needs_zone_adjustment:
                joint_start_candidate = max(bar.start_m, candidate_end - splice_length)
                joint_end_candidate = candidate_end
                if self._overlaps_prohibited_zone(
                    joint_start_candidate, joint_end_candidate, prohibited_zones
                ):
                    safe_center = self._find_safe_splice_position(
                        start_range=current_start + splice_length,
                        end_range=candidate_end,
                        splice_length=splice_length,
                        prohibited_zones=prohibited_zones,
                    )
                    if safe_center is not None:
                        candidate_end = min(bar.end_m, safe_center)
                        joint_end_candidate = candidate_end
                        joint_start_candidate = joint_end_candidate - splice_length
                        needs_zone_adjustment = False
                        logger.info(
                            "Barra %s: empalme inicial reubicado en %.2fm",
                            bar.id,
                            joint_end_candidate,
                        )
                    else:
                        logger.warning(
                            "Barra %s: no se encontró corredor seguro para el primer empalme",
                            bar.id,
                        )
                else:
                    needs_zone_adjustment = False

            if not is_last_segment and needs_zone_adjustment:
                candidate_end = self._adjust_segment_end_for_splice_zones(
                    current_start,
                    candidate_end,
                    splice_length,
                    prohibited_zones,
                )
                if candidate_end >= bar.end_m - tolerance:
                    is_last_segment = True

            segment_end = bar.end_m if is_last_segment else candidate_end
            length = segment_end - current_start
            if length <= 0:
                break

            segment = RebarDetail(
                id=f"{bar.id}-S{piece_index:02d}",
                diameter=bar.diameter,
                position=bar.position,
                type=bar.type,
                length_m=length,
                start_m=current_start,
                end_m=segment_end,
                hook_type=bar.hook_type,
                splices=None,
                quantity=bar.quantity,
                development_length_m=bar.development_length_m,
                notes=f"Segmento {piece_index} - Inferior",
            )
            segments.append(segment)

            if not logged_first_segment and piece_index == 1:
                logger.info(
                    "Barra inferior %s: primer segmento=%.2fm",
                    bar.id,
                    length,
                )
                logged_first_segment = True

            if segment_end >= bar.end_m - 1e-6:
                break

            joint_start = max(bar.start_m, segment_end - splice_length)
            joint_end = segment_end

            if self._overlaps_prohibited_zone(joint_start, joint_end, prohibited_zones):
                logger.warning(
                    "Barra %s: empalme inferior aún cae en zona prohibida",
                    bar.id,
                )

            joints.append(
                {
                    "start": joint_start,
                    "end": joint_end,
                    "length": joint_end - joint_start,
                    "type": "lap_splice_class_b",
                    "position": "bottom",
                }
            )
            logger.info("Barra inferior %s: empalme en %.2fm", bar.id, joint_end)

            current_start = joint_start
            piece_index += 1

        if safety_counter >= 100:
            logger.warning("Se alcanzó el límite de segmentación para la barra %s", bar.id)

        if not segments:
            return [bar]

        for idx, segment in enumerate(segments):
            segment_splices: List[Dict[str, Any]] = []
            if idx > 0:
                segment_splices.append(joints[idx - 1])
            if idx < len(joints):
                segment_splices.append(joints[idx])
            segment.splices = segment_splices or None

        return segments

    def _prefer_splice_in_previous_corridor(
        self,
        *,
        current_start: float,
        joint_start: float,
        candidate_end: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
    ) -> float:
        tolerance = 1e-3
        if splice_length <= 0:
            return candidate_end

        before_zone = self._find_next_before_zone(joint_start, prohibited_zones)
        if not before_zone:
            return candidate_end

        prev_end = self._find_zone_end_before(before_zone.start_m, prohibited_zones)
        if prev_end is None or prev_end < current_start + tolerance:
            return candidate_end

        corridor_end = before_zone.start_m - tolerance
        available = corridor_end - prev_end
        if available < splice_length - tolerance:
            return candidate_end

        target_end = prev_end + splice_length
        target_end = min(target_end, corridor_end)
        if target_end <= current_start + tolerance:
            return candidate_end

        return target_end

    @staticmethod
    def _find_overlapping_zone(
        start: float, end: float, zones: List[ProhibitedZone]
    ) -> Optional[ProhibitedZone]:
        for zone in zones:
            if max(start, zone.start_m) < min(end, zone.end_m):
                return zone
        return None

    def _adjust_segment_end_for_splice_zones(
        self,
        current_start: float,
        candidate_end: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
    ) -> float:
        tolerance = 1e-3
        adjusted_end = candidate_end
        attempts = 0

        while attempts < 20:
            attempts += 1
            joint_start = adjusted_end - splice_length
            if joint_start < current_start + tolerance:
                joint_start = current_start + tolerance
            if not self._overlaps_prohibited_zone(joint_start, adjusted_end, prohibited_zones):
                return adjusted_end

            zone = self._find_overlapping_zone(joint_start, adjusted_end, prohibited_zones)
            if not zone:
                break

            shifted_end = zone.start_m - tolerance
            if shifted_end - splice_length <= current_start + tolerance:
                return candidate_end

            adjusted_end = shifted_end

        return adjusted_end

    @staticmethod
    def _find_next_zone_start(position: float, zones: List[ProhibitedZone]) -> Optional[float]:
        tolerance = 1e-3
        for zone in zones:
            if zone.start_m >= position + tolerance:
                return zone.start_m
        return None

    @staticmethod
    def _find_zone_end_before(position: float, zones: List[ProhibitedZone]) -> Optional[float]:
        tolerance = 1e-3
        previous_end = None
        for zone in zones:
            if zone.end_m < position - tolerance:
                previous_end = zone.end_m
            else:
                break
        return previous_end

    @staticmethod
    def _find_next_before_zone(position: float, zones: List[ProhibitedZone]) -> Optional[ProhibitedZone]:
        tolerance = 1e-3
        for zone in zones:
            if zone.start_m >= position + tolerance:
                description = (zone.description or "").lower()
                if "antes" in description:
                    return zone
        return None

    def _coordinate_splice_positions(
        self,
        top_bars: List[RebarDetail],
        bottom_bars: List[RebarDetail],
        prohibited_zones: List[ProhibitedZone],
        beam_length: float,
    ) -> Tuple[List[RebarDetail], List[RebarDetail]]:
        if not bottom_bars or beam_length <= 0:
            return top_bars, bottom_bars

        existing_splices: List[Dict[str, Any]] = []
        for bar in top_bars:
            if not bar.splices:
                continue
            for splice in bar.splices:
                length = splice.get("length") or max(splice.get("end", 0.0) - splice.get("start", 0.0), 0.0)
                center = (splice.get("start", 0.0) + splice.get("end", 0.0)) / 2
                existing_splices.append({"center": center, "length": length, "type": "top"})

        for bar in bottom_bars:
            if not bar.splices:
                continue
            bar_adjusted = False
            for splice in bar.splices:
                length = splice.get("length") or max(splice.get("end", 0.0) - splice.get("start", 0.0), 0.0)
                if length <= 0:
                    continue
                original_center = (splice.get("start", 0.0) + splice.get("end", 0.0)) / 2
                has_conflict = False
                for existing in existing_splices:
                    min_distance = max(length, existing["length"]) * 1.5
                    if abs(original_center - existing["center"]) < min_distance:
                        has_conflict = True
                        break

                if not has_conflict:
                    existing_splices.append({"center": original_center, "length": length, "type": "bottom"})
                    continue

                new_center = self._find_non_conflicting_splice_position(
                    original_center=original_center,
                    splice_length=length,
                    existing_splice_positions=existing_splices,
                    prohibited_zones=prohibited_zones,
                    beam_length=beam_length,
                    bar_id=bar.id,
                )

                if new_center is not None:
                    new_start = max(0.0, new_center - length / 2)
                    new_end = min(beam_length, new_center + length / 2)
                    splice["start"] = new_start
                    splice["end"] = new_end
                    splice["length"] = new_end - new_start
                    splice["adjusted"] = True
                    splice["original_center"] = original_center
                    bar_adjusted = True
                    final_center = (new_start + new_end) / 2
                    existing_splices.append({"center": final_center, "length": splice["length"], "type": "bottom"})
                else:
                    existing_splices.append({"center": original_center, "length": length, "type": "bottom"})
                    logger.warning(
                        "Barra %s: no se pudo evitar coincidencia de empalme en %.2fm",
                        bar.id,
                        original_center,
                    )

            if bar_adjusted:
                note = (bar.notes or "").strip()
                marker = "Empalmes coordinados"
                if marker not in note:
                    bar.notes = f"{note} | {marker}" if note else marker

        return top_bars, bottom_bars

    def _find_non_conflicting_splice_position(
        self,
        *,
        original_center: float,
        splice_length: float,
        existing_splice_positions: List[Dict[str, Any]],
        prohibited_zones: List[ProhibitedZone],
        beam_length: float,
        bar_id: str,
        max_attempts: int = 10,
    ) -> Optional[float]:
        if splice_length <= 0:
            return None

        service = cast("BeamDetailingService", self)
        offset_candidates = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        attempts = 0
        while attempts < max_attempts:
            for magnitude in offset_candidates:
                for direction in (1, -1):
                    test_center = original_center + direction * magnitude * (attempts + 1)
                    if test_center < splice_length / 2 or test_center > beam_length - splice_length / 2:
                        continue
                    if service._is_in_prohibited_zone(test_center, prohibited_zones, splice_length):
                        continue
                    conflict = False
                    for existing in existing_splice_positions:
                        min_distance = max(splice_length, existing["length"]) * 1.2
                        if abs(test_center - existing["center"]) < min_distance:
                            conflict = True
                            break
                    if not conflict:
                        return test_center
            attempts += 1

        logger.debug("Barra %s: no se encontró posición alternativa para el empalme", bar_id)
        return None

    def _find_safe_splice_position(
        self,
        *,
        start_range: float,
        end_range: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
        step: float = 0.1,
    ) -> Optional[float]:
        tolerance = 1e-3
        if splice_length <= 0 or end_range - start_range <= tolerance:
            return None

        test_positions: List[float] = []
        pos = start_range
        while pos <= end_range + tolerance:
            test_positions.append(pos)
            pos += max(step, tolerance)

        for i in range(len(test_positions) - 1):
            mid = (test_positions[i] + test_positions[i + 1]) / 2
            test_positions.append(mid)

        for position in sorted(set(test_positions)):
            splice_start = position - splice_length / 2
            splice_end = position + splice_length / 2
            overlaps = False
            for zone in prohibited_zones:
                if max(splice_start, zone.start_m) < min(splice_end, zone.end_m):
                    overlaps = True
                    break
            if not overlaps:
                return position

        return None

    def _target_bottom_corridor_end(
        self,
        *,
        current_start: float,
        candidate_end: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
    ) -> Optional[float]:
        tolerance = 1e-3
        before_zone = self._find_next_before_zone(current_start, prohibited_zones)
        if not before_zone:
            return None

        prev_end = self._find_zone_end_before(before_zone.start_m, prohibited_zones)
        if prev_end is None:
            return None

        corridor_end = before_zone.start_m - tolerance
        target = prev_end + splice_length
        target = min(target, corridor_end, candidate_end)
        if target - current_start < splice_length - tolerance:
            return None

        return target

    @staticmethod
    def _overlaps_prohibited_zone(start: float, end: float, zones: List[ProhibitedZone]) -> bool:
        for zone in zones:
            if max(start, zone.start_m) < min(end, zone.end_m):
                return True
        return False

    def _rebuild_splices_from_geometry(self, bars: List[RebarDetail]) -> None:
        if not bars:
            return

        grouped: Dict[str, List[RebarDetail]] = {}
        for bar in bars:
            base_id = bar.id.rsplit("-S", 1)[0] if "-S" in bar.id else bar.id
            grouped.setdefault(base_id, []).append(bar)

        tolerance = 1e-3
        for segments in grouped.values():
            segments.sort(key=lambda seg: (seg.start_m, seg.end_m))
            for segment in segments:
                segment.splices = None

            for idx in range(len(segments) - 1):
                current = segments[idx]
                following = segments[idx + 1]
                overlap_start = max(current.start_m, following.start_m)
                overlap_end = min(current.end_m, following.end_m)
                if overlap_end - overlap_start <= tolerance:
                    continue

                splice_payload = {
                    "start": overlap_start,
                    "end": overlap_end,
                    "length": overlap_end - overlap_start,
                    "type": "lap_splice_class_b",
                    "position": current.position,
                }

                for segment in (current, following):
                    splice_entry = splice_payload.copy()
                    if segment.splices:
                        segment.splices.append(splice_entry)
                    else:
                        segment.splices = [splice_entry]
