from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from steel_frame.models import (
    FrameInput,
    FrameOptimizationInput,
    OptimizationConstraints,
    StoreyInput,
    StoreyLoadInput,
)


def build_module1_frame(form_data: Dict[str, Any]) -> FrameInput:
    storeys = [StoreyInput(**row) for row in form_data["storeys"]]
    return FrameInput(
        num_storeys=int(form_data["num_storeys"]),
        beam_span_m=float(form_data["beam_span_m"]),
        design_standard=str(form_data["design_standard"]),
        storeys=storeys,
    )


def build_module2_frame(form_data: Dict[str, Any]) -> FrameOptimizationInput:
    constraints = OptimizationConstraints(
        utilization_min=float(form_data["constraints"]["utilization_min"]),
        utilization_max=float(form_data["constraints"]["utilization_max"]),
        beam_same_groups=form_data["constraints"]["beam_same_groups"],
        column_same_groups=form_data["constraints"]["column_same_groups"],
        allowed_steel_grades=form_data["constraints"]["allowed_steel_grades"],
        beam_allowed_shapes=form_data["constraints"]["beam_allowed_shapes"],
        column_allowed_shapes=form_data["constraints"]["column_allowed_shapes"],
        beam_max_section_class_by_storey=form_data["constraints"]["beam_max_section_class_by_storey"],
        column_max_section_class_by_storey=form_data["constraints"]["column_max_section_class_by_storey"],
    )
    storeys = [StoreyLoadInput(**row) for row in form_data["storeys"]]
    return FrameOptimizationInput(
        num_storeys=int(form_data["num_storeys"]),
        beam_span_m=float(form_data["beam_span_m"]),
        design_standard=str(form_data["design_standard"]),
        storeys=storeys,
        constraints=constraints,
    )


def _round_numeric_columns(df: pd.DataFrame, digits: int = 3) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].round(digits)
    return out


def module1_results_to_dataframe(results: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for row in results.get("results_by_storey", []):
        rows.append({
            "Storey": row["storey"],
            "Height (m)": row["height_m"],
            "Beam Section": row["beam_section"],
            "Beam Grade": row["beam_grade"],
            "Beam U": row["beam_utilization_ratio"],
            "Column Section": row["column_section"],
            "Column Grade": row["column_grade"],
            "Column U": row["column_utilization_ratio"],
            "Storey Cost (SGD)": row["storey_total_cost_sgd"],
        })
    return _round_numeric_columns(pd.DataFrame(rows))


def module2_results_to_dataframe(results: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for row in results.get("results_by_storey", []):
        rows.append({
            "Storey": row["storey"],
            "Height (m)": row["height_m"],
            "Beam Section": row["beam_section"],
            "Beam Shape": row["beam_shape"],
            "Beam Grade": row["beam_grade"],
            "Beam Class": row["beam_section_class"],
            "Beam U": row["beam_utilization_ratio"],
            "Column Section": row["column_section"],
            "Column Shape": row["column_shape"],
            "Column Grade": row["column_grade"],
            "Column Class": row["column_section_class"],
            "Column U": row["column_utilization_ratio"],
            "Storey Cost (SGD)": row["storey_total_cost_sgd"],
        })
    return _round_numeric_columns(pd.DataFrame(rows))
