from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .models import CandidateResult, DesignStandard, FrameOptimizationInput, SectionProperty, SteelGrade
from .utils import normalize_name

VALID_SHAPES = {"I SECTION", "CIRCULAR HOLLOW SECTION", "SQUARE HOLLOW SECTION"}


def calculate_design_load(alpha: float, beta: float, dead_load_kn_per_m: float, live_load_kn_per_m: float) -> float:
    return alpha * dead_load_kn_per_m + beta * live_load_kn_per_m


def validate_frame_input(frame: FrameOptimizationInput) -> None:
    if frame.num_storeys != len(frame.storeys):
        raise ValueError("num_storeys does not match the number of storey rows.")
    if [s.storey for s in frame.storeys] != list(range(1, frame.num_storeys + 1)):
        raise ValueError("Storeys must be ordered from 1 to N.")
    c = frame.constraints
    if not (0.0 <= c.utilization_min <= c.utilization_max):
        raise ValueError("utilization_min must be <= utilization_max and both non-negative.")
    for name in c.beam_allowed_shapes + c.column_allowed_shapes:
        if normalize_name(name) not in VALID_SHAPES:
            raise KeyError(f"Unknown section shape: {name}")


def validate_database_lookups(frame: FrameOptimizationInput, sections, grades, standards) -> None:
    if normalize_name(frame.design_standard) not in standards:
        raise KeyError(f"Design standard not found: {frame.design_standard}")
    for grade_name in (frame.constraints.allowed_steel_grades or list(grades.keys())):
        if normalize_name(grade_name) not in grades:
            raise KeyError(f"Allowed steel grade not found: {grade_name}")


def compute_storey_actions(frame: FrameOptimizationInput, design_code: DesignStandard) -> Dict[str, List[float]]:
    design_loads = [calculate_design_load(design_code.alpha, design_code.beta, s.dead_load_kn_per_m, s.live_load_kn_per_m) for s in frame.storeys]
    beam_mmax_knm = [w * (frame.beam_span_m ** 2) / 12.0 for w in design_loads]
    column_increment_kn = [w * frame.beam_span_m / 2.0 for w in design_loads]
    column_total_kn = [0.0] * len(frame.storeys)
    running = 0.0
    for idx in reversed(range(len(frame.storeys))):
        running += column_increment_kn[idx]
        column_total_kn[idx] = running
    return {
        "design_loads_kn_per_m": design_loads,
        "beam_mmax_knm": beam_mmax_knm,
        "column_total_load_kn": column_total_kn,
    }


def build_storey_groups(num_storeys: int, explicit_groups: List[List[int]]) -> List[Tuple[int, ...]]:
    covered = set()
    groups: List[Tuple[int, ...]] = []
    for group in explicit_groups:
        tup = tuple(sorted(int(x) for x in group))
        groups.append(tup)
        covered.update(tup)
    for s in range(1, num_storeys + 1):
        if s not in covered:
            groups.append((s,))
    return groups


def get_allowed_grade_names(frame: FrameOptimizationInput, grades: Dict[str, SteelGrade]) -> List[str]:
    if frame.constraints.allowed_steel_grades:
        return [normalize_name(g) for g in frame.constraints.allowed_steel_grades]
    return list(grades.keys())


def get_max_section_class(member_type: str, storey: int, frame: FrameOptimizationInput):
    raw = frame.constraints.beam_max_section_class_by_storey if member_type == "beam" else frame.constraints.column_max_section_class_by_storey
    return raw.get(str(storey))


def compute_member_utilization(member_type: str, section: SectionProperty, grade: SteelGrade, storey: int, actions: Dict[str, List[float]]) -> float:
    idx = storey - 1
    if member_type == "beam":
        sigma = (actions["beam_mmax_knm"][idx] * 1e6) / section.elastic_modulus_mm3
    else:
        sigma = (actions["column_total_load_kn"][idx] * 1000.0) / section.area_mm2
    return sigma / grade.yield_strength_mpa


def compute_member_cost(member_type: str, section: SectionProperty, grade: SteelGrade, storey_input, frame: FrameOptimizationInput) -> float:
    if member_type == "beam":
        return section.weight_kg_per_m * frame.beam_span_m * grade.cost_sgd_per_kg
    return 2.0 * section.weight_kg_per_m * storey_input.height_m * grade.cost_sgd_per_kg


def enumerate_group_candidates(member_type: str, group: Sequence[int], frame: FrameOptimizationInput, sections: Dict[str, SectionProperty], grades: Dict[str, SteelGrade], actions: Dict[str, List[float]]) -> List[CandidateResult]:
    allowed_shapes = frame.constraints.beam_allowed_shapes if member_type == "beam" else frame.constraints.column_allowed_shapes
    allowed_shapes_norm = {normalize_name(x) for x in allowed_shapes}
    grade_names = get_allowed_grade_names(frame, grades)
    candidates: List[CandidateResult] = []

    for section in sections.values():
        if normalize_name(section.shape) not in allowed_shapes_norm:
            continue
        for storey in group:
            max_class = get_max_section_class(member_type, storey, frame)
            if max_class is not None and section.section_class is not None and section.section_class > max_class:
                break
        else:
            for grade_name in grade_names:
                grade = grades[grade_name]
                utilizations: Dict[int, float] = {}
                feasible = True
                total_cost = 0.0
                for storey in group:
                    u = compute_member_utilization(member_type, section, grade, storey, actions)
                    if not (frame.constraints.utilization_min <= u <= frame.constraints.utilization_max):
                        feasible = False
                        break
                    utilizations[storey] = u
                    total_cost += compute_member_cost(member_type, section, grade, frame.storeys[storey - 1], frame)
                if feasible:
                    candidates.append(CandidateResult(section=section.name, shape=section.shape, steel_grade=grade.grade, section_class=section.section_class or -1, total_cost_sgd=total_cost, utilizations_by_storey=utilizations))

    candidates.sort(key=lambda x: (x.total_cost_sgd, x.section, x.steel_grade))
    return candidates


def build_infeasibility_hint(member_type: str, group: Sequence[int], frame: FrameOptimizationInput, sections: Dict[str, SectionProperty], grades: Dict[str, SteelGrade], actions: Dict[str, List[float]], top_n: int = 5) -> Dict[str, Any]:
    allowed_shapes = frame.constraints.beam_allowed_shapes if member_type == "beam" else frame.constraints.column_allowed_shapes
    allowed_shapes_norm = {normalize_name(x) for x in allowed_shapes}
    diagnostics = []
    for section in sections.values():
        if normalize_name(section.shape) not in allowed_shapes_norm:
            continue
        for grade_name in get_allowed_grade_names(frame, grades):
            grade = grades[grade_name]
            total_violation = 0.0
            utilizations = {}
            class_ok = True
            for storey in group:
                max_class = get_max_section_class(member_type, storey, frame)
                if max_class is not None and section.section_class is not None and section.section_class > max_class:
                    class_ok = False
                    total_violation += abs(section.section_class - max_class) + 1000
                    continue
                u = compute_member_utilization(member_type, section, grade, storey, actions)
                utilizations[storey] = u
                if u < frame.constraints.utilization_min:
                    total_violation += frame.constraints.utilization_min - u
                elif u > frame.constraints.utilization_max:
                    total_violation += u - frame.constraints.utilization_max
            diagnostics.append({"section": section.name, "shape": section.shape, "steel_grade": grade.grade, "section_class": section.section_class, "utilizations_by_storey": utilizations, "total_violation": total_violation, "class_ok": class_ok})
    diagnostics.sort(key=lambda x: (x["total_violation"], x["section"], x["steel_grade"]))
    return {"member_type": member_type, "group": list(group), "message": "No feasible section/grade combination satisfies all constraints for this group.", "closest_candidates": diagnostics[:top_n]}


def optimize_module2(frame: FrameOptimizationInput, sections: Dict[str, SectionProperty], grades: Dict[str, SteelGrade], standards: Dict[str, DesignStandard]) -> Dict[str, Any]:
    validate_frame_input(frame)
    validate_database_lookups(frame, sections, grades, standards)
    design_code = standards[normalize_name(frame.design_standard)]
    actions = compute_storey_actions(frame, design_code)
    beam_groups = build_storey_groups(frame.num_storeys, frame.constraints.beam_same_groups)
    column_groups = build_storey_groups(frame.num_storeys, frame.constraints.column_same_groups)

    selected_beams = {}
    selected_columns = {}
    infeasibility_reports = []

    for group in beam_groups:
        options = enumerate_group_candidates("beam", group, frame, sections, grades, actions)
        if options:
            selected_beams[group] = options[0]
        else:
            infeasibility_reports.append(build_infeasibility_hint("beam", group, frame, sections, grades, actions))

    for group in column_groups:
        options = enumerate_group_candidates("column", group, frame, sections, grades, actions)
        if options:
            selected_columns[group] = options[0]
        else:
            infeasibility_reports.append(build_infeasibility_hint("column", group, frame, sections, grades, actions))

    if infeasibility_reports:
        return {"feasible": False, "input": {"num_storeys": frame.num_storeys, "beam_span_m": frame.beam_span_m, "design_standard": frame.design_standard, "storeys": [asdict(s) for s in frame.storeys], "constraints": asdict(frame.constraints)}, "design_standard": asdict(design_code), "actions": actions, "infeasibility_reports": infeasibility_reports, "results_by_storey": [], "total_cost_sgd": None}

    rows = []
    total_cost = 0.0
    def find_choice(selected, storey):
        for group, choice in selected.items():
            if storey in group:
                return choice
        raise KeyError(storey)

    for storey in range(1, frame.num_storeys + 1):
        idx = storey - 1
        beam_choice = find_choice(selected_beams, storey)
        column_choice = find_choice(selected_columns, storey)
        beam_section = sections[beam_choice.section]
        column_section = sections[column_choice.section]
        beam_grade = grades[beam_choice.steel_grade]
        column_grade = grades[column_choice.steel_grade]
        storey_input = frame.storeys[idx]
        beam_cost = compute_member_cost("beam", beam_section, beam_grade, storey_input, frame)
        column_cost = compute_member_cost("column", column_section, column_grade, storey_input, frame)
        storey_cost = beam_cost + column_cost
        total_cost += storey_cost
        rows.append({
            "storey": storey,
            "height_m": storey_input.height_m,
            "dead_load_kn_per_m": storey_input.dead_load_kn_per_m,
            "live_load_kn_per_m": storey_input.live_load_kn_per_m,
            "design_load_kn_per_m": actions["design_loads_kn_per_m"][idx],
            "beam_section": beam_choice.section,
            "beam_shape": beam_choice.shape,
            "beam_grade": beam_choice.steel_grade,
            "beam_section_class": beam_choice.section_class,
            "beam_utilization_ratio": beam_choice.utilizations_by_storey[storey],
            "beam_cost_sgd": beam_cost,
            "column_section": column_choice.section,
            "column_shape": column_choice.shape,
            "column_grade": column_choice.steel_grade,
            "column_section_class": column_choice.section_class,
            "column_utilization_ratio": column_choice.utilizations_by_storey[storey],
            "column_cost_total_sgd": column_cost,
            "storey_total_cost_sgd": storey_cost,
        })
    return {"feasible": True, "input": {"num_storeys": frame.num_storeys, "beam_span_m": frame.beam_span_m, "design_standard": frame.design_standard, "storeys": [asdict(s) for s in frame.storeys], "constraints": asdict(frame.constraints)}, "design_standard": asdict(design_code), "actions": actions, "results_by_storey": rows, "total_cost_sgd": total_cost}
