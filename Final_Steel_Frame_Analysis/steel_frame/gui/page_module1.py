
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List

import streamlit as st

from steel_frame.exporters import export_module1_excel, save_json
from steel_frame.module1 import run_module1
from steel_frame.utils import normalize_name

from .adapters import build_module1_frame, module1_results_to_dataframe
from .visualization import draw_frame
from .widgets import load_module1_sample, storey_rows_module1_from_frame

SELECT_SECTION = "-- Select Section --"
SELECT_GRADE = "-- Select Grade --"


def _default_rows(n: int) -> List[Dict[str, Any]]:
    return [
        {
            "storey": i,
            "height_m": 3.0,
            "dead_load_kn_per_m": 5.0,
            "live_load_kn_per_m": 3.0,
            "beam_section": "",
            "beam_grade": "",
            "column_section": "",
            "column_grade": "",
        }
        for i in range(1, n + 1)
    ]


def _normalize_storey_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                **row,
                "beam_section": normalize_name(row.get("beam_section", "")),
                "beam_grade": normalize_name(row.get("beam_grade", "")),
                "column_section": normalize_name(row.get("column_section", "")),
                "column_grade": normalize_name(row.get("column_grade", "")),
            }
        )
    return out


def _ensure_page_state(refs: Dict[str, Any]) -> None:
    st.session_state.setdefault("m1_num_storeys", 5)
    st.session_state.setdefault("m1_beam_span", 4.0)
    st.session_state.setdefault(
        "m1_design_standard",
        refs["standards_list"][0] if refs["standards_list"] else "",
    )
    st.session_state.setdefault("m1_defaults", None)
    st.session_state.setdefault("module1_results", None)


def _apply_defaults_to_widgets(n: int, defaults: List[Dict[str, Any]]) -> None:
    for i in range(1, n + 1):
        d = defaults[i - 1] if i - 1 < len(defaults) else _default_rows(n)[i - 1]
        st.session_state[f"m1_h_{i}"] = float(d.get("height_m", 3.0))
        st.session_state[f"m1_d_{i}"] = float(d.get("dead_load_kn_per_m", 5.0))
        st.session_state[f"m1_l_{i}"] = float(d.get("live_load_kn_per_m", 3.0))
        st.session_state[f"m1_bs_{i}"] = normalize_name(d.get("beam_section", ""))
        st.session_state[f"m1_bg_{i}"] = normalize_name(d.get("beam_grade", ""))
        st.session_state[f"m1_cs_{i}"] = normalize_name(d.get("column_section", ""))
        st.session_state[f"m1_cg_{i}"] = normalize_name(d.get("column_grade", ""))


def _copy_above_module1(i: int) -> None:
    st.session_state[f"m1_h_{i}"] = st.session_state.get(f"m1_h_{i-1}", 3.0)
    st.session_state[f"m1_d_{i}"] = st.session_state.get(f"m1_d_{i-1}", 5.0)
    st.session_state[f"m1_l_{i}"] = st.session_state.get(f"m1_l_{i-1}", 3.0)
    st.session_state[f"m1_bs_{i}"] = st.session_state.get(f"m1_bs_{i-1}", "")
    st.session_state[f"m1_bg_{i}"] = st.session_state.get(f"m1_bg_{i-1}", "")
    st.session_state[f"m1_cs_{i}"] = st.session_state.get(f"m1_cs_{i-1}", "")
    st.session_state[f"m1_cg_{i}"] = st.session_state.get(f"m1_cg_{i-1}", "")


def _apply_bulk_module1(num_storeys: int, refs: Dict[str, Any], start: int, end: int) -> None:
    start = max(1, min(start, num_storeys))
    end = max(1, min(end, num_storeys))
    if start > end:
        start, end = end, start

    checks = {
        "height": st.session_state.get("m1_bulk_use_height", False),
        "dead": st.session_state.get("m1_bulk_use_dead", False),
        "live": st.session_state.get("m1_bulk_use_live", False),
        "beam_section": st.session_state.get("m1_bulk_use_beam_section", False),
        "beam_grade": st.session_state.get("m1_bulk_use_beam_grade", False),
        "column_section": st.session_state.get("m1_bulk_use_column_section", False),
        "column_grade": st.session_state.get("m1_bulk_use_column_grade", False),
    }
    values = {
        "height": float(st.session_state.get("m1_bulk_height", 3.0)),
        "dead": float(st.session_state.get("m1_bulk_dead", 5.0)),
        "live": float(st.session_state.get("m1_bulk_live", 3.0)),
        "beam_section": st.session_state.get("m1_bulk_beam_section", SELECT_SECTION),
        "beam_grade": st.session_state.get("m1_bulk_beam_grade", SELECT_GRADE),
        "column_section": st.session_state.get("m1_bulk_column_section", SELECT_SECTION),
        "column_grade": st.session_state.get("m1_bulk_column_grade", SELECT_GRADE),
    }

    for i in range(start, end + 1):
        if checks["height"]:
            st.session_state[f"m1_h_{i}"] = values["height"]
        if checks["dead"]:
            st.session_state[f"m1_d_{i}"] = values["dead"]
        if checks["live"]:
            st.session_state[f"m1_l_{i}"] = values["live"]
        if checks["beam_section"]:
            st.session_state[f"m1_bs_{i}"] = values["beam_section"]
        if checks["beam_grade"]:
            st.session_state[f"m1_bg_{i}"] = values["beam_grade"]
        if checks["column_section"]:
            st.session_state[f"m1_cs_{i}"] = values["column_section"]
        if checks["column_grade"]:
            st.session_state[f"m1_cg_{i}"] = values["column_grade"]


def _render_bulk_tools(num_storeys: int, refs: Dict[str, Any]) -> None:
    with st.expander("Fast Input Tools", expanded=True):
        st.caption("Use this to fill repeated values quickly before editing only the few storeys that differ.")
        c1, c2, c3 = st.columns(3)
        c1.checkbox("Height", key="m1_bulk_use_height")
        c2.checkbox("Dead load", key="m1_bulk_use_dead")
        c3.checkbox("Live load", key="m1_bulk_use_live")

        c4, c5, c6, c7 = st.columns(4)
        c4.checkbox("Beam section", key="m1_bulk_use_beam_section")
        c5.checkbox("Beam grade", key="m1_bulk_use_beam_grade")
        c6.checkbox("Column section", key="m1_bulk_use_column_section")
        c7.checkbox("Column grade", key="m1_bulk_use_column_grade")

        r1, r2, r3 = st.columns(3)
        r1.number_input("Height value (m)", min_value=0.1, value=3.0, key="m1_bulk_height")
        r2.number_input("Dead load value (kN/m)", min_value=0.0, value=5.0, key="m1_bulk_dead")
        r3.number_input("Live load value (kN/m)", min_value=0.0, value=3.0, key="m1_bulk_live")

        section_options = [SELECT_SECTION] + refs["section_names"]
        grade_options = [SELECT_GRADE] + refs["grades"]

        r4, r5, r6, r7 = st.columns(4)
        r4.selectbox("Beam section value", section_options, key="m1_bulk_beam_section")
        r5.selectbox("Beam grade value", grade_options, key="m1_bulk_beam_grade")
        r6.selectbox("Column section value", section_options, key="m1_bulk_column_section")
        r7.selectbox("Column grade value", grade_options, key="m1_bulk_column_grade")

        a1, a2, a3, a4 = st.columns([1, 1, 1, 2])
        a1.number_input("From storey", min_value=1, max_value=num_storeys, value=1, step=1, key="m1_bulk_from")
        a2.number_input("To storey", min_value=1, max_value=num_storeys, value=num_storeys, step=1, key="m1_bulk_to")

        if a3.button("Apply to range", key="m1_apply_range"):
            _apply_bulk_module1(
                num_storeys,
                refs,
                int(st.session_state["m1_bulk_from"]),
                int(st.session_state["m1_bulk_to"]),
            )
            st.rerun()

        if a4.button("Apply to all storeys", key="m1_apply_all"):
            _apply_bulk_module1(num_storeys, refs, 1, num_storeys)
            st.rerun()


def _build_rows(n: int, refs: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    section_options = [SELECT_SECTION] + refs["section_names"]
    grade_options = [SELECT_GRADE] + refs["grades"]

    for i in range(1, n + 1):
        st.markdown(f"**Storey {i}**")
        c1, c2, c3, c4 = st.columns(4)

        height = c1.number_input(f"Height (m) - S{i}", min_value=0.1, key=f"m1_h_{i}")
        dead = c2.number_input(f"Dead load (kN/m) - S{i}", min_value=0.0, key=f"m1_d_{i}")
        live = c3.number_input(f"Live load (kN/m) - S{i}", min_value=0.0, key=f"m1_l_{i}")

        c4.button(
            "Copy above",
            key=f"m1_copy_above_{i}",
            disabled=(i == 1),
            on_click=_copy_above_module1,
            args=(i,),
        )

        c5, c6, c7, c8 = st.columns(4)
        current_bs = normalize_name(st.session_state.get(f"m1_bs_{i}", ""))
        current_bg = normalize_name(st.session_state.get(f"m1_bg_{i}", ""))
        current_cs = normalize_name(st.session_state.get(f"m1_cs_{i}", ""))
        current_cg = normalize_name(st.session_state.get(f"m1_cg_{i}", ""))

        beam_section = c5.selectbox(
            f"Beam Section - S{i}",
            section_options,
            index=section_options.index(current_bs) if current_bs in section_options else 0,
            key=f"m1_bs_{i}",
        )
        beam_grade = c6.selectbox(
            f"Beam Grade - S{i}",
            grade_options,
            index=grade_options.index(current_bg) if current_bg in grade_options else 0,
            key=f"m1_bg_{i}",
        )
        column_section = c7.selectbox(
            f"Column Section - S{i}",
            section_options,
            index=section_options.index(current_cs) if current_cs in section_options else 0,
            key=f"m1_cs_{i}",
        )
        column_grade = c8.selectbox(
            f"Column Grade - S{i}",
            grade_options,
            index=grade_options.index(current_cg) if current_cg in grade_options else 0,
            key=f"m1_cg_{i}",
        )

        rows.append(
            {
                "storey": i,
                "height_m": height,
                "dead_load_kn_per_m": dead,
                "live_load_kn_per_m": live,
                "beam_section": beam_section if beam_section != SELECT_SECTION else "",
                "beam_grade": beam_grade if beam_grade != SELECT_GRADE else "",
                "column_section": column_section if column_section != SELECT_SECTION else "",
                "column_grade": column_grade if column_grade != SELECT_GRADE else "",
            }
        )

    return rows


def _validate_module1_rows(rows: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    for row in rows:
        s = row["storey"]
        if not row["beam_section"]:
            errors.append(f"Storey {s}: select a beam section.")
        if not row["beam_grade"]:
            errors.append(f"Storey {s}: select a beam grade.")
        if not row["column_section"]:
            errors.append(f"Storey {s}: select a column section.")
        if not row["column_grade"]:
            errors.append(f"Storey {s}: select a column grade.")
    return errors


def _render_export_buttons(results: Dict[str, Any]) -> None:
    with TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        json_path = tmp / "module1_results.json"
        xlsx_path = tmp / "module1_results.xlsx"
        save_json(results, json_path)
        export_module1_excel(results, xlsx_path)
        st.download_button(
            "Download JSON",
            data=json_path.read_bytes(),
            file_name="module1_results.json",
            mime="application/json",
        )
        st.download_button(
            "Download Excel",
            data=xlsx_path.read_bytes(),
            file_name="module1_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def render_module1_page(data_dir: Path, refs: Dict[str, Any]) -> None:
    st.title("Module 1: Analyze a Given Design")
    _ensure_page_state(refs)

    if st.button("Load sample Module 1 input"):
        sample = load_module1_sample(data_dir)
        st.session_state["m1_num_storeys"] = sample.num_storeys
        st.session_state["m1_beam_span"] = sample.beam_span_m
        st.session_state["m1_design_standard"] = normalize_name(sample.design_standard)
        defaults = _normalize_storey_rows(storey_rows_module1_from_frame(sample))
        st.session_state["m1_defaults"] = defaults
        _apply_defaults_to_widgets(sample.num_storeys, defaults)
        st.rerun()

    top1, top2 = st.columns([1, 1])
    with top1:
        st.number_input("Number of Storeys", min_value=1, step=1, key="m1_num_storeys")
    with top2:
        st.number_input("Beam Span (m)", min_value=0.1, key="m1_beam_span")

    st.selectbox("Design Standard", refs["standards_list"], key="m1_design_standard")

    num_storeys = int(st.session_state["m1_num_storeys"])
    defaults = st.session_state.get("m1_defaults")

    if defaults is None:
        defaults = _default_rows(num_storeys)
        _apply_defaults_to_widgets(num_storeys, defaults)
        st.session_state["m1_defaults"] = defaults
    elif len(defaults) != num_storeys:
        current_rows = []
        for i in range(1, min(len(defaults), num_storeys) + 1):
            current_rows.append(
                {
                    "storey": i,
                    "height_m": float(st.session_state.get(f"m1_h_{i}", defaults[i - 1].get("height_m", 3.0))),
                    "dead_load_kn_per_m": float(st.session_state.get(f"m1_d_{i}", defaults[i - 1].get("dead_load_kn_per_m", 5.0))),
                    "live_load_kn_per_m": float(st.session_state.get(f"m1_l_{i}", defaults[i - 1].get("live_load_kn_per_m", 3.0))),
                    "beam_section": normalize_name(st.session_state.get(f"m1_bs_{i}", defaults[i - 1].get("beam_section", ""))),
                    "beam_grade": normalize_name(st.session_state.get(f"m1_bg_{i}", defaults[i - 1].get("beam_grade", ""))),
                    "column_section": normalize_name(st.session_state.get(f"m1_cs_{i}", defaults[i - 1].get("column_section", ""))),
                    "column_grade": normalize_name(st.session_state.get(f"m1_cg_{i}", defaults[i - 1].get("column_grade", ""))),
                }
            )
        if num_storeys > len(current_rows):
            current_rows.extend(_default_rows(num_storeys)[len(current_rows):])

        st.session_state["m1_defaults"] = current_rows[:num_storeys]
        _apply_defaults_to_widgets(num_storeys, st.session_state["m1_defaults"])

    _render_bulk_tools(num_storeys, refs)

    st.info(
        "Please select beam/column sections and grades explicitly, or use 'Load sample Module 1 input'. "
        "The app will no longer silently default to the first section in the database."
    )

    st.subheader("Per-storey inputs")
    rows = _build_rows(num_storeys, refs)

    if st.button("Run Module 1", type="primary"):
        validation_errors = _validate_module1_rows(rows)
        if validation_errors:
            st.session_state["module1_results"] = None
            st.error("Module 1 cannot run yet. Please complete the missing selections below.")
            for msg in validation_errors:
                st.write(f"- {msg}")
        else:
            form_data = {
                "num_storeys": num_storeys,
                "beam_span_m": float(st.session_state["m1_beam_span"]),
                "design_standard": st.session_state["m1_design_standard"],
                "storeys": rows,
            }
            try:
                frame = build_module1_frame(form_data)
                results = run_module1(
                    frame,
                    refs["sections"],
                    refs["materials"],
                    refs["standards"],
                )
                st.session_state["module1_results"] = results
                st.success("Module 1 finished successfully.")
            except Exception as exc:
                st.session_state["module1_results"] = None
                st.error(f"Module 1 failed: {exc}")

    results = st.session_state.get("module1_results")
    if results:
        c1, c2, c3 = st.columns(3)
        c1.metric("Design Standard", results["design_standard"]["code"])
        c2.metric("Total Cost (SGD)", f"{results['total_cost_sgd']:.3f}")
        max_u = max(
            max(r["beam_utilization_ratio"], r["column_utilization_ratio"])
            for r in results["results_by_storey"]
        )
        c3.metric("Max Utilization", f"{max_u:.3f}")

        st.dataframe(module1_results_to_dataframe(results), use_container_width=True)
        st.pyplot(draw_frame(results, optimized=False), use_container_width=True)

        st.subheader("Export results")
        _render_export_buttons(results)
