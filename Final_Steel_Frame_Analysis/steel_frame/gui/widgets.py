from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from steel_frame.database import (
    load_design_standard_database,
    load_material_database,
    load_module1_input_json,
    load_module2_input_json,
    load_section_database,
)

SHAPE_ORDER = ["I SECTION", "CIRCULAR HOLLOW SECTION", "SQUARE HOLLOW SECTION"]


@st.cache_data(show_spinner=False)
def load_reference_data(data_dir: Path) -> Dict[str, Any]:
    sections = load_section_database(data_dir / "member_section.xlsx")
    materials = load_material_database(data_dir / "material_cost.xlsx")
    standards = load_design_standard_database(data_dir / "design_standard.xlsx")

    section_names = sorted([s.name for s in sections.values()])
    grades = sorted([g.grade for g in materials.values()])
    standards_list = sorted([s.code for s in standards.values()])

    sections_by_shape: Dict[str, List[str]] = {shape: [] for shape in SHAPE_ORDER}
    for section in sections.values():
        shape = section.shape.upper()
        sections_by_shape.setdefault(shape, []).append(section.name)
    for shape in sections_by_shape:
        sections_by_shape[shape] = sorted(sections_by_shape[shape])

    return {
        "sections": sections,
        "materials": materials,
        "standards": standards,
        "section_names": section_names,
        "grades": grades,
        "standards_list": standards_list,
        "sections_by_shape": sections_by_shape,
    }


def load_module1_sample(data_dir: Path):
    return load_module1_input_json(data_dir / "sample_input_module1.json")


def load_module2_sample(data_dir: Path):
    return load_module2_input_json(data_dir / "sample_input_module2.json")


def load_module2_feasible_demo(data_dir: Path):
    return load_module2_input_json(data_dir / "sample_input_module2_feasible_demo.json")


def parse_group_text(raw: str) -> List[List[int]]:
    groups: List[List[int]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "-" in line and "," not in line:
            start, end = [int(x.strip()) for x in line.split("-", 1)]
            if start > end:
                start, end = end, start
            groups.append(list(range(start, end + 1)))
        else:
            groups.append([int(x.strip()) for x in line.split(",") if x.strip()])
    return groups


def parse_storey_class_limits(raw: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        storey, cls = [x.strip() for x in line.split(":", 1)]
        out[str(int(storey))] = int(cls)
    return out


def storey_rows_module1_from_frame(frame) -> List[Dict[str, Any]]:
    return [
        {
            "storey": s.storey,
            "height_m": s.height_m,
            "dead_load_kn_per_m": s.dead_load_kn_per_m,
            "live_load_kn_per_m": s.live_load_kn_per_m,
            "beam_section": s.beam_section,
            "beam_grade": s.beam_grade,
            "column_section": s.column_section,
            "column_grade": s.column_grade,
        }
        for s in frame.storeys
    ]


def storey_rows_module2_from_frame(frame) -> List[Dict[str, Any]]:
    return [
        {
            "storey": s.storey,
            "height_m": s.height_m,
            "dead_load_kn_per_m": s.dead_load_kn_per_m,
            "live_load_kn_per_m": s.live_load_kn_per_m,
        }
        for s in frame.storeys
    ]
