from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from steel_frame.exporters import export_module2_excel, save_json
from steel_frame.module2 import optimize_module2

from .adapters import build_module2_frame, module2_results_to_dataframe
from .visualization import draw_frame
from .widgets import (
    SHAPE_ORDER,
    load_module2_feasible_demo,
    load_module2_sample,
    parse_group_text,
    parse_storey_class_limits,
    storey_rows_module2_from_frame,
)


def _default_rows(n: int) -> List[Dict[str, Any]]:
    return [
        {
            "storey": i,
            "height_m": 3.0,
            "dead_load_kn_per_m": 5.0,
            "live_load_kn_per_m": 3.0,
        }
        for i in range(1, n + 1)
    ]


def _ensure_page_state(refs: Dict[str, Any]) -> None:
    st.session_state.setdefault("m2_num_storeys", 5)
    st.session_state.setdefault("m2_beam_span", 4.0)
    st.session_state.setdefault(
        "m2_design_standard",
        refs["standards_list"][0] if refs["standards_list"] else "",
    )
    st.session_state.setdefault("m2_defaults", None)
    st.session_state.setdefault("m2_constraints", None)


def _shape_label(value: str) -> str:
    norm = str(value).strip().upper().replace("_", " ")
    mapping = {
        "I SECTION": "I SECTION",
        "I-SECTION": "I SECTION",
        "CIRCULAR HOLLOW SECTION": "CIRCULAR HOLLOW SECTION",
        "CHS": "CIRCULAR HOLLOW SECTION",
        "SQUARE HOLLOW SECTION": "SQUARE HOLLOW SECTION",
        "SHS": "SQUARE HOLLOW SECTION",
    }
    return mapping.get(norm, norm)


def _normalize_shape_defaults(values: List[str] | None, fallback: List[str]) -> List[str]:
    normalized = [_shape_label(v) for v in (values or [])]
    normalized = [v for v in normalized if v in SHAPE_ORDER]
    return normalized or fallback


def _apply_defaults_to_widgets(n: int, defaults: List[Dict[str, Any]]) -> None:
    for i in range(1, n + 1):
        d = defaults[i - 1] if i - 1 < len(defaults) else _default_rows(n)[i - 1]
        st.session_state[f"m2_h_{i}"] = float(d.get("height_m", 3.0))
        st.session_state[f"m2_d_{i}"] = float(d.get("dead_load_kn_per_m", 5.0))
        st.session_state[f"m2_l_{i}"] = float(d.get("live_load_kn_per_m", 3.0))


def _copy_above_module2(i: int) -> None:
    st.session_state[f"m2_h_{i}"] = st.session_state.get(f"m2_h_{i-1}", 3.0)
    st.session_state[f"m2_d_{i}"] = st.session_state.get(f"m2_d_{i-1}", 5.0)
    st.session_state[f"m2_l_{i}"] = st.session_state.get(f"m2_l_{i-1}", 3.0)


def _apply_bulk_module2(num_storeys: int, start: int, end: int) -> None:
    start = max(1, min(start, num_storeys))
    end = max(1, min(end, num_storeys))
    if start > end:
        start, end = end, start

    use_height = st.session_state.get("m2_bulk_use_height", False)
    use_dead = st.session_state.get("m2_bulk_use_dead", False)
    use_live = st.session_state.get("m2_bulk_use_live", False)

    height = float(st.session_state.get("m2_bulk_height", 3.0))
    dead = float(st.session_state.get("m2_bulk_dead", 5.0))
    live = float(st.session_state.get("m2_bulk_live", 3.0))

    for i in range(start, end + 1):
        if use_height:
            st.session_state[f"m2_h_{i}"] = height
        if use_dead:
            st.session_state[f"m2_d_{i}"] = dead
        if use_live:
            st.session_state[f"m2_l_{i}"] = live


def _render_bulk_tools(num_storeys: int) -> None:
    with st.expander("Fast Input Tools", expanded=True):
        st.caption(
            "Quickly fill repeated heights and loads for the competition, then adjust only the exceptions."
        )

        c1, c2, c3 = st.columns(3)
        c1.checkbox("Height", key="m2_bulk_use_height")
        c2.checkbox("Dead load", key="m2_bulk_use_dead")
        c3.checkbox("Live load", key="m2_bulk_use_live")

        r1, r2, r3 = st.columns(3)
        r1.number_input("Height value (m)", min_value=0.1, value=3.0, key="m2_bulk_height")
        r2.number_input(
            "Dead load value (kN/m)", min_value=0.0, value=5.0, key="m2_bulk_dead"
        )
        r3.number_input(
            "Live load value (kN/m)", min_value=0.0, value=3.0, key="m2_bulk_live"
        )

        a1, a2, a3, a4 = st.columns([1, 1, 1, 2])
        a1.number_input(
            "From storey",
            min_value=1,
            max_value=num_storeys,
            value=1,
            step=1,
            key="m2_bulk_from",
        )
        a2.number_input(
            "To storey",
            min_value=1,
            max_value=num_storeys,
            value=num_storeys,
            step=1,
            key="m2_bulk_to",
        )

        if a3.button("Apply to range", key="m2_apply_range"):
            _apply_bulk_module2(
                num_storeys,
                int(st.session_state["m2_bulk_from"]),
                int(st.session_state["m2_bulk_to"]),
            )
            st.rerun()

        if a4.button("Apply to all storeys", key="m2_apply_all"):
            _apply_bulk_module2(num_storeys, 1, num_storeys)
            st.rerun()


def _build_rows(n: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i in range(1, n + 1):
        cols = st.columns(5)
        cols[0].markdown(f"**Storey {i}**")
        height = cols[1].number_input(f"Height (m) - S{i}", min_value=0.1, key=f"m2_h_{i}")
        dead = cols[2].number_input(f"Dead load (kN/m) - S{i}", min_value=0.0, key=f"m2_d_{i}")
        live = cols[3].number_input(f"Live load (kN/m) - S{i}", min_value=0.0, key=f"m2_l_{i}")

        cols[4].button(
            "Copy above",
            key=f"m2_copy_above_{i}",
            disabled=(i == 1),
            on_click=_copy_above_module2,
            args=(i,),
        )

        rows.append(
            {
                "storey": i,
                "height_m": height,
                "dead_load_kn_per_m": dead,
                "live_load_kn_per_m": live,
            }
        )
    return rows


def _render_export_buttons(results: Dict[str, Any]) -> None:
    with TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        json_path = tmp / "module2_results.json"
        xlsx_path = tmp / "module2_results.xlsx"
        save_json(results, json_path)
        export_module2_excel(results, xlsx_path)

        st.download_button(
            "Download JSON",
            data=json_path.read_bytes(),
            file_name="module2_results.json",
            mime="application/json",
        )
        st.download_button(
            "Download Excel",
            data=xlsx_path.read_bytes(),
            file_name="module2_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def _load_sample_into_state(sample, refs: Dict[str, Any]) -> None:
    st.session_state["m2_num_storeys"] = sample.num_storeys
    st.session_state["m2_beam_span"] = sample.beam_span_m
    if sample.design_standard in refs["standards_list"]:
        st.session_state["m2_design_standard"] = sample.design_standard

    defaults = storey_rows_module2_from_frame(sample)
    st.session_state["m2_defaults"] = defaults
    st.session_state["m2_constraints"] = sample.constraints
    _apply_defaults_to_widgets(sample.num_storeys, defaults)


def _constraint_check_table(results: Dict[str, Any], umin: float, umax: float) -> pd.DataFrame:
    rows = []
    for row in results.get("results_by_storey", []):
        beam_u = float(row["beam_utilization_ratio"])
        col_u = float(row["column_utilization_ratio"])
        rows.append(
            {
                "Storey": row["storey"],
                "Beam U": round(beam_u, 3),
                "Beam Check": "PASS"
                if umin <= beam_u <= umax
                else ("TOO LOW" if beam_u < umin else "TOO HIGH"),
                "Column U": round(col_u, 3),
                "Column Check": "PASS"
                if umin <= col_u <= umax
                else ("TOO LOW" if col_u < umin else "TOO HIGH"),
            }
        )
    return pd.DataFrame(rows)


def _violation_messages(results: Dict[str, Any], umin: float, umax: float) -> List[str]:
    messages: List[str] = []
    for row in results.get("results_by_storey", []):
        s = row["storey"]
        beam_u = float(row["beam_utilization_ratio"])
        col_u = float(row["column_utilization_ratio"])

        if beam_u < umin:
            messages.append(f"Storey {s} beam U = {beam_u:.3f} is below {umin:.1f}.")
        elif beam_u > umax:
            messages.append(f"Storey {s} beam U = {beam_u:.3f} is above {umax:.1f}.")

        if col_u < umin:
            messages.append(f"Storey {s} column U = {col_u:.3f} is below {umin:.1f}.")
        elif col_u > umax:
            messages.append(f"Storey {s} column U = {col_u:.3f} is above {umax:.1f}.")

    return messages


def render_module2_page(data_dir: Path, refs: Dict[str, Any]) -> None:
    st.title("Module 2: Optimize the Design")
    _ensure_page_state(refs)

    b1, b2 = st.columns(2)
    if b1.button("Load official Module 2 sample"):
        sample = load_module2_sample(data_dir)
        _load_sample_into_state(sample, refs)
        st.rerun()

    if b2.button("Load feasible demo sample"):
        sample = load_module2_feasible_demo(data_dir)
        _load_sample_into_state(sample, refs)
        st.rerun()

    c1, c2 = st.columns(2)
    c1.number_input("Number of Storeys", min_value=1, step=1, key="m2_num_storeys")
    c2.number_input("Beam Span (m)", min_value=0.1, key="m2_beam_span")
    st.selectbox("Design Standard", refs["standards_list"], key="m2_design_standard")

    num_storeys = int(st.session_state["m2_num_storeys"])
    defaults = st.session_state.get("m2_defaults")
    default_constraints = st.session_state.get("m2_constraints")

    if defaults is None:
        defaults = _default_rows(num_storeys)
        st.session_state["m2_defaults"] = defaults
        _apply_defaults_to_widgets(num_storeys, defaults)
    elif len(defaults) != num_storeys:
        current_rows = []
        for i in range(1, min(len(defaults), num_storeys) + 1):
            current_rows.append(
                {
                    "storey": i,
                    "height_m": float(
                        st.session_state.get(
                            f"m2_h_{i}", defaults[i - 1].get("height_m", 3.0)
                        )
                    ),
                    "dead_load_kn_per_m": float(
                        st.session_state.get(
                            f"m2_d_{i}", defaults[i - 1].get("dead_load_kn_per_m", 5.0)
                        )
                    ),
                    "live_load_kn_per_m": float(
                        st.session_state.get(
                            f"m2_l_{i}", defaults[i - 1].get("live_load_kn_per_m", 3.0)
                        )
                    ),
                }
            )
        if num_storeys > len(current_rows):
            current_rows.extend(_default_rows(num_storeys)[len(current_rows) :])

        st.session_state["m2_defaults"] = current_rows[:num_storeys]
        _apply_defaults_to_widgets(num_storeys, st.session_state["m2_defaults"])

    _render_bulk_tools(num_storeys)

    st.subheader("Per-storey loads")
    rows = _build_rows(num_storeys)

    st.subheader("Constraints")
    util1, util2 = st.columns(2)
    default_umin = float(default_constraints.utilization_min) if default_constraints else 0.2
    default_umax = float(default_constraints.utilization_max) if default_constraints else 0.7

    umin = util1.number_input(
        "Minimum Utilization",
        min_value=0.0,
        max_value=10.0,
        value=default_umin,
    )
    umax = util2.number_input(
        "Maximum Utilization",
        min_value=0.0,
        max_value=10.0,
        value=default_umax,
    )

    st.caption("Latest sample problem requirement: utilization ratio must be between 20% and 70%.")

    shape1, shape2 = st.columns(2)
    default_beam_shapes = _normalize_shape_defaults(
        getattr(default_constraints, "beam_allowed_shapes", None),
        ["I SECTION"],
    )
    default_col_shapes = _normalize_shape_defaults(
        getattr(default_constraints, "column_allowed_shapes", None),
        ["CIRCULAR HOLLOW SECTION", "SQUARE HOLLOW SECTION"],
    )

    beam_shapes = shape1.multiselect(
        "Allowed Beam Shapes",
        SHAPE_ORDER,
        default=default_beam_shapes,
    )
    column_shapes = shape2.multiselect(
        "Allowed Column Shapes",
        SHAPE_ORDER,
        default=default_col_shapes,
    )

    default_allowed_grades = (
        default_constraints.allowed_steel_grades
        if default_constraints and default_constraints.allowed_steel_grades
        else refs["grades"]
    )
    allowed_grades = st.multiselect(
        "Allowed Steel Grades",
        refs["grades"],
        default=default_allowed_grades,
    )

    group1, group2 = st.columns(2)
    beam_groups = default_constraints.beam_same_groups if default_constraints else [[2, 3, 4]]
    col_groups = default_constraints.column_same_groups if default_constraints else [[1, 2, 3, 4]]

    def _group_text(groups: List[List[int]]) -> str:
        lines = []
        for g in groups:
            g = sorted(g)
            if len(g) > 1 and g == list(range(min(g), max(g) + 1)):
                lines.append(f"{min(g)}-{max(g)}")
            else:
                lines.append(",".join(map(str, g)))
        return "\n".join(lines)

    beam_group_text = group1.text_area(
        "Beam Same Groups",
        value=_group_text(beam_groups),
        help="One group per line. Examples: 2-4 or 1,3,5",
    )
    column_group_text = group2.text_area(
        "Column Same Groups",
        value=_group_text(col_groups),
        help="One group per line. Examples: 1-4 or 2,5",
    )

    class1, class2 = st.columns(2)
    beam_class_dict = (
        default_constraints.beam_max_section_class_by_storey if default_constraints else {}
    )
    column_class_dict = (
        default_constraints.column_max_section_class_by_storey
        if default_constraints
        else {"1": 2, "2": 2, "3": 2}
    )

    beam_class_text = class1.text_area(
        "Beam Max Section Class by Storey",
        value="\n".join(f"{k}:{v}" for k, v in beam_class_dict.items()),
        help="Format: storey:class, one per line",
    )
    column_class_text = class2.text_area(
        "Column Max Section Class by Storey",
        value="\n".join(f"{k}:{v}" for k, v in column_class_dict.items()),
        help="Format: storey:class, one per line",
    )

    if st.button("Run Module 2", type="primary"):
        try:
            form_data = {
                "num_storeys": num_storeys,
                "beam_span_m": float(st.session_state["m2_beam_span"]),
                "design_standard": st.session_state["m2_design_standard"],
                "storeys": rows,
                "constraints": {
                    "utilization_min": umin,
                    "utilization_max": umax,
                    "beam_same_groups": parse_group_text(beam_group_text),
                    "column_same_groups": parse_group_text(column_group_text),
                    "allowed_steel_grades": allowed_grades,
                    "beam_allowed_shapes": beam_shapes,
                    "column_allowed_shapes": column_shapes,
                    "beam_max_section_class_by_storey": parse_storey_class_limits(beam_class_text),
                    "column_max_section_class_by_storey": parse_storey_class_limits(column_class_text),
                },
            }

            frame = build_module2_frame(form_data)
            results = optimize_module2(
                frame,
                refs["sections"],
                refs["materials"],
                refs["standards"],
            )
            st.session_state["module2_results"] = results

            if results["feasible"]:
                st.success("Module 2 finished successfully.")
            else:
                st.warning("No feasible solution found for the given constraints.")

        except Exception as exc:
            st.session_state["module2_results"] = None
            st.error(f"Module 2 failed: {exc}")

    results = st.session_state.get("module2_results")
    if results:
        st.subheader("Constraint Check")
        st.info(f"Target utilization range: {umin:.1f} ≤ U ≤ {umax:.1f}")

        if results["feasible"]:
            r1, r2, r3 = st.columns(3)
            r1.metric("Design Standard", results["design_standard"]["code"])
            r2.metric("Feasible", "YES")
            r3.metric("Optimized Total Cost (SGD)", f"{results['total_cost_sgd']:.3f}")

            check_df = _constraint_check_table(results, umin, umax)
            violations = _violation_messages(results, umin, umax)

            if violations:
                st.error("Some members still fall outside the selected utilization range.")
                for msg in violations:
                    st.write(f"- {msg}")
            else:
                st.success("All beam and column utilization ratios satisfy the selected range.")

            st.dataframe(check_df, use_container_width=True)
            st.dataframe(module2_results_to_dataframe(results), use_container_width=True)
            st.pyplot(draw_frame(results, optimized=True), use_container_width=True)

        else:
            st.error("No feasible solution exists for the current constraints.")
            reports = results.get("infeasibility_reports", [])

            if reports:
                st.write("Likely reasons:")
                for report in reports:
                    st.write(f"- {report.get('message', 'Constraint set is too restrictive.')}")

            for report in reports:
                with st.expander(f"{report['member_type'].title()} group {report['group']}"):
                    closest = report.get("closest_candidates", [])
                    if closest:
                        st.json(closest)

        st.subheader("Export results")
        _render_export_buttons(results)