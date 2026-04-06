# Steel Frame Project

This is a cleaner merged project folder for your CE3204 steel frame app.

## Folder structure

- `main.py` - single entry point for both modules
- `steel_frame/` - reusable project code
- `data/` - Excel databases and sample JSON inputs
- `outputs/` - generated JSON and Excel results

## How to run in VS Code terminal

Install dependency first:

```bash
python -m pip install -r requirements.txt
```

Run Module 1:

```bash
python main.py module1 --output-json outputs/module1_results.json --output-excel outputs/module1_results.xlsx
```

Run Module 2 with official sample input:

```bash
python main.py module2 --output-json outputs/module2_results.json --output-excel outputs/module2_results.xlsx
```

Run Module 2 with the relaxed feasible demo:

```bash
python main.py module2 --input data/sample_input_module2_feasible_demo.json --output-json outputs/module2_demo_results.json --output-excel outputs/module2_demo_results.xlsx
```

## Notes

- Keep the Excel files inside the `data/` folder.
- The official Module 2 sample may return infeasible depending on the given constraints.
- The relaxed demo input is included so you can test a successful optimization run.
