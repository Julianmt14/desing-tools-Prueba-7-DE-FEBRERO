from pathlib import Path

from app.modules.drawing import BeamDrawingService
from app.modules.drawing.preview_renderer import render_svg
from app.modules.drawing.schemas import (
    AxisMarker,
    BeamDrawingMetadata,
    BeamDrawingPayload,
    BeamGeometry,
    BeamRebarLayout,
    BeamSpan,
    BeamSupport,
    DrawingUnits,
    RebarGroup,
)
from app.schemas.design import StirrupConfig
from app.schemas.tools.despiece import (
    ContinuousBarsInfo,
    DetailingResults,
    MaterialItem,
    RebarDetail,
    StirrupDesignSummary,
    StirrupSegment,
    StirrupSpanSpec,
)


def build_payload() -> BeamDrawingPayload:
    metadata = BeamDrawingMetadata(
        project_name="Centro Cultural",
        beam_label="VA 201",
        element_identifier="VA 201",
        element_level=3.52,
        element_quantity=1,
        axis_labels=["A", "B", "C", "D"],
        notes="Ensayo",
        concrete_strength="21 MPa (3000 psi)",
        reinforcement="420 MPa (Grado 60)",
        energy_dissipation_class="DES",
    )

    supports = [
        BeamSupport(index=0, label="A", width_m=0.35, start_m=0.0, end_m=0.35),
        BeamSupport(index=1, label="B", width_m=0.35, start_m=4.35, end_m=4.70),
        BeamSupport(index=2, label="C", width_m=0.35, start_m=8.70, end_m=9.05),
    ]

    spans = [
        BeamSpan(
            index=0,
            label="Luz 1",
            start_support_index=0,
            end_support_index=1,
            clear_length_m=4.0,
            start_m=0.35,
            end_m=4.35,
            section_width_cm=30,
            section_height_cm=45,
        ),
        BeamSpan(
            index=1,
            label="Luz 2",
            start_support_index=1,
            end_support_index=2,
            clear_length_m=4.0,
            start_m=4.70,
            end_m=8.70,
            section_width_cm=30,
            section_height_cm=45,
        ),
    ]

    axis_markers = [
        AxisMarker(index=idx, label=s.label, position_m=(s.start_m + s.end_m) / 2)
        for idx, s in enumerate(supports)
    ]

    geometry = BeamGeometry(
        total_length_m=9.05,
        spans=spans,
        supports=supports,
        axis_markers=axis_markers,
        has_cantilevers=False,
    )

    rebar_layout = BeamRebarLayout(
        top_groups=[RebarGroup(diameter="#5", quantity=4, position="top")],
        bottom_groups=[RebarGroup(diameter="#5", quantity=4, position="bottom")],
        hook_type="135",
        cover_cm=4,
        lap_splice_length_min_m=0.75,
        max_rebar_length_m=12.0,
        segment_reinforcements=None,
    )

    splice = {"start_m": 0.8, "end_m": 1.2, "length": 0.4, "type": "lap"}

    bar_template = dict(
        diameter="#5",
        position="top",
        type="continuous",
        length_m=7.5,
        hook_type="135",
        quantity=2,
        development_length_m=0.6,
        notes="Barra continua",
    )

    top_bars = [
        RebarDetail(id="T5-C01-S01", start_m=0.1, end_m=7.4, splices=[splice], **bar_template),
        RebarDetail(id="T5-C01-S02", start_m=0.5, end_m=8.5, splices=None, **bar_template),
    ]

    bottom_bar_template = dict(
        diameter="#5",
        position="bottom",
        type="span",
        length_m=7.0,
        hook_type="135",
        quantity=2,
        development_length_m=0.6,
        notes="Refuerzo inferior",
    )

    bottom_bars = [
        RebarDetail(id="B5-S01", start_m=0.2, end_m=7.2, splices=[splice], **bottom_bar_template),
    ]

    material_list = [
        MaterialItem(
            diameter="#5",
            total_length_m=60.0,
            pieces=10,
            weight_kg=90.0,
            commercial_lengths=[],
            waste_percentage=2.0,
        )
    ]

    continuous_bars = {
        "top": ContinuousBarsInfo(diameters=["#5"], count_per_diameter={"#5": 2}, total_continuous=2),
        "bottom": ContinuousBarsInfo(diameters=["#5"], count_per_diameter={"#5": 2}, total_continuous=2),
    }

    span_specs = [
        StirrupSpanSpec(
            span_index=0,
            label="Luz 1",
            base_cm=30,
            height_cm=45,
            cover_cm=4,
            stirrup_width_cm=22,
            stirrup_height_cm=37,
            effective_depth_m=0.4,
            spacing_confined_m=0.1,
            spacing_non_confined_m=0.15,
        ),
        StirrupSpanSpec(
            span_index=1,
            label="Luz 2",
            base_cm=30,
            height_cm=45,
            cover_cm=4,
            stirrup_width_cm=22,
            stirrup_height_cm=37,
            effective_depth_m=0.4,
            spacing_confined_m=0.1,
            spacing_non_confined_m=0.15,
        ),
    ]

    zone_segments = [
        StirrupSegment(start_m=0.35, end_m=2.5, zone_type="confined", spacing_m=0.1, estimated_count=20),
        StirrupSegment(start_m=2.5, end_m=4.35, zone_type="non_confined", spacing_m=0.15, estimated_count=12),
        StirrupSegment(start_m=4.70, end_m=8.70, zone_type="non_confined", spacing_m=0.15, estimated_count=26),
    ]

    stirrups_summary = StirrupDesignSummary(
        diameter="#3",
        hook_type="135",
        additional_branches_total=0,
        span_specs=span_specs,
        zone_segments=zone_segments,
    )

    detailing_results = DetailingResults(
        top_bars=top_bars,
        bottom_bars=bottom_bars,
        prohibited_zones=[],
        material_list=material_list,
        continuous_bars=continuous_bars,
        warnings=[],
        validation_passed=True,
        total_weight_kg=90.0,
        total_bars_count=5,
        stirrups_summary=stirrups_summary,
    )

    return BeamDrawingPayload(
        design_id=1,
        despiece_id=1,
        metadata=metadata,
        geometry=geometry,
        rebar_layout=rebar_layout,
        detailing_results=detailing_results,
        stirrups_config=[StirrupConfig(additional_branches=0, stirrup_type="C")],
        drawing_units=DrawingUnits(source_unit="m", target_unit="mm", scale_factor=1000.0, precision=2),
    )


def main() -> None:
    payload = build_payload()
    service = BeamDrawingService()
    document = service.render_document(payload)
    svg_content = render_svg(document)
    output_path = Path("preview_outputs/stirrups_preview.svg")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding="utf-8")
    print(f"SVG generado en: {output_path}")


if __name__ == "__main__":
    main()
