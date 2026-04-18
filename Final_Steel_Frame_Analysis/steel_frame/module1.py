from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from .models import DesignStandard, FrameInput, SectionProperty, SteelGrade
from .utils import normalize_name


def validate_module1_input(frame: FrameInput) -> None:
    if frame.num_storeys != len(frame.storeys):
        raise ValueError("num_storeys does not match the number of storey rows.")
    if [s.storey for s in frame.storeys] != list(range(1, frame.num_storeys + 1)):
        raise ValueError("Storeys must be ordered from 1 to N.")
    if frame.beam_span_m <= 0:
        raise ValueError("Beam span must be positive.")


def validate_module1_lookups(frame: FrameInput, sections, grades, standards) -> None:
    if normalize_name(frame.design_standard) not in standards:
        raise KeyError(f"Design standard not found: {frame.design_standard}")
    for s in frame.storeys:
        for name in [s.beam_section, s.column_section]:
            if normalize_name(name) not in sections:
                raise KeyError(f"Section not found: {name}")
        for grade in [s.beam_grade, s.column_grade]:
            if normalize_name(grade) not in grades:
                raise KeyError(f"Steel grade not found: {grade}")


def calculate_design_load(alpha: float, beta: float, dead_load_kn_per_m: float, live_load_kn_per_m: float) -> float:
    return alpha * dead_load_kn_per_m + beta * live_load_kn_per_m


def run_module1(frame: FrameInput, sections: Dict[str, SectionProperty], grades: Dict[str, SteelGrade], standards: Dict[str, DesignStandard]) -> Dict[str, Any]:
    validate_module1_input(frame)
    validate_module1_lookups(frame, sections, grades, standards)
    design_code = standards[normalize_name(frame.design_standard)]
    design_loads = [calculate_design_load(design_code.alpha, design_code.beta, s.dead_load_kn_per_m, s.live_load_kn_per_m) for s in frame.storeys]
    column_load_increment_kn = [w * frame.beam_span_m / 2.0 for w in design_loads]
    column_total_load_kn = [0.0] * len(frame.storeys)
    running = 0.0
    for idx in reversed(range(len(frame.storeys))):
        running += column_load_increment_kn[idx]
        column_total_load_kn[idx] = running

    rows = []
    total_cost = 0.0
    for i, s in enumerate(frame.storeys):
        beam_section = sections[normalize_name(s.beam_section)]
        col_section = sections[normalize_name(s.column_section)]
        beam_grade = grades[normalize_name(s.beam_grade)]
        col_grade = grades[normalize_name(s.column_grade)]
        w = design_loads[i]
        mmax_knm = w * frame.beam_span_m**2 / 12.0
        beam_sigma = (mmax_knm * 1e6) / beam_section.elastic_modulus_mm3
        beam_u = beam_sigma / beam_grade.yield_strength_mpa
        p_kn = column_total_load_kn[i]
        column_sigma = (p_kn * 1000.0) / col_section.area_mm2
        column_u = column_sigma / col_grade.yield_strength_mpa
        beam_cost = beam_section.weight_kg_per_m * frame.beam_span_m * beam_grade.cost_sgd_per_kg
        column_cost_each = col_section.weight_kg_per_m * s.height_m * col_grade.cost_sgd_per_kg
        column_total_cost = 2.0 * column_cost_each
        storey_cost = beam_cost + column_total_cost
        total_cost += storey_cost
        rows.append({
            "storey": s.storey,
            "height_m": s.height_m,
            "dead_load_kn_per_m": s.dead_load_kn_per_m,
            "live_load_kn_per_m": s.live_load_kn_per_m,
            "design_load_kn_per_m": w,
            "beam_section": beam_section.name,
            "beam_shape": beam_section.shape,
            "beam_grade": beam_grade.grade,
            "beam_mmax_knm": mmax_knm,
            "beam_sigma_mpa": beam_sigma,
            "beam_utilization_ratio": beam_u,
            "beam_cost_sgd": beam_cost,
            "column_section": col_section.name,
            "column_shape": col_section.shape,
            "column_grade": col_grade.grade,
            "column_total_load_kn": p_kn,
            "column_sigma_mpa": column_sigma,
            "column_utilization_ratio": column_u,
            "column_cost_total_sgd": column_total_cost,
            "storey_total_cost_sgd": storey_cost,
        })
    return {"input": asdict(frame), "design_standard": asdict(design_code), "results_by_storey": rows, "total_cost_sgd": total_cost}
