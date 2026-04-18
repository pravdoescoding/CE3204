from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SectionProperty:
    name: str
    shape: str
    weight_kg_per_m: float
    area_mm2: float
    inertia_mm4: float
    elastic_modulus_mm3: float
    section_class: Optional[int] = None
    depth_mm: Optional[float] = None
    width_mm: Optional[float] = None
    diameter_mm: Optional[float] = None
    side_mm: Optional[float] = None


@dataclass
class SteelGrade:
    grade: str
    yield_strength_mpa: float
    cost_sgd_per_kg: float


@dataclass
class DesignStandard:
    code: str
    alpha: float
    beta: float


@dataclass
class StoreyInput:
    storey: int
    height_m: float
    dead_load_kn_per_m: float
    live_load_kn_per_m: float
    beam_section: str
    beam_grade: str
    column_section: str
    column_grade: str


@dataclass
class FrameInput:
    num_storeys: int
    beam_span_m: float
    design_standard: str
    storeys: List[StoreyInput]


@dataclass
class StoreyLoadInput:
    storey: int
    height_m: float
    dead_load_kn_per_m: float
    live_load_kn_per_m: float


@dataclass
class OptimizationConstraints:
    utilization_min: float
    utilization_max: float
    beam_same_groups: List[List[int]]
    column_same_groups: List[List[int]]
    allowed_steel_grades: List[str]
    beam_allowed_shapes: List[str]
    column_allowed_shapes: List[str]
    beam_max_section_class_by_storey: Dict[str, int]
    column_max_section_class_by_storey: Dict[str, int]


@dataclass
class FrameOptimizationInput:
    num_storeys: int
    beam_span_m: float
    design_standard: str
    storeys: List[StoreyLoadInput]
    constraints: OptimizationConstraints


@dataclass
class CandidateResult:
    section: str
    shape: str
    steel_grade: str
    section_class: int
    total_cost_sgd: float
    utilizations_by_storey: Dict[int, float]
