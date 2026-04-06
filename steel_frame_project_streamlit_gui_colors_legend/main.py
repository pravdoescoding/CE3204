from __future__ import annotations

import argparse
from pathlib import Path

from steel_frame import (
    export_module1_excel,
    export_module2_excel,
    load_design_standard_database,
    load_material_database,
    load_module1_input_json,
    load_module2_input_json,
    load_section_database,
    optimize_module2,
    run_module1,
    save_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Steel frame project runner for Module 1 and Module 2")
    subparsers = parser.add_subparsers(dest="module", required=True)

    def add_common(p: argparse.ArgumentParser):
        p.add_argument("--sections", default="data/member_section.xlsx")
        p.add_argument("--materials", default="data/material_cost.xlsx")
        p.add_argument("--standards", default="data/design_standard.xlsx")
        p.add_argument("--output-json", required=True)
        p.add_argument("--output-excel", required=True)

    p1 = subparsers.add_parser("module1", help="Run Module 1 analysis")
    p1.add_argument("--input", default="data/sample_input_module1.json")
    add_common(p1)

    p2 = subparsers.add_parser("module2", help="Run Module 2 optimization")
    p2.add_argument("--input", default="data/sample_input_module2.json")
    add_common(p2)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = Path(__file__).resolve().parent
    sections = load_section_database(base / args.sections)
    grades = load_material_database(base / args.materials)
    standards = load_design_standard_database(base / args.standards)

    output_json = base / args.output_json
    output_excel = base / args.output_excel
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_excel.parent.mkdir(parents=True, exist_ok=True)

    if args.module == "module1":
        frame = load_module1_input_json(base / args.input)
        results = run_module1(frame, sections, grades, standards)
        save_json(results, output_json)
        export_module1_excel(results, output_excel)
        print("Module 1 finished successfully.")
        print(f"Design standard: {results['design_standard']['code']}")
        print(f"Total cost (SGD): {results['total_cost_sgd']:.3f}")
    else:
        frame = load_module2_input_json(base / args.input)
        results = optimize_module2(frame, sections, grades, standards)
        save_json(results, output_json)
        export_module2_excel(results, output_excel)
        if results["feasible"]:
            print("Module 2 finished successfully.")
            print(f"Design standard: {results['design_standard']['code']}")
            print(f"Optimized total cost (SGD): {results['total_cost_sgd']:.3f}")
        else:
            print("Module 2 finished: no feasible solution for the given constraints.")


if __name__ == "__main__":
    main()
