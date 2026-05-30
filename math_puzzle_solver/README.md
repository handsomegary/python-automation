# Magic Diamond Puzzle Solver

Python solvers and an Excel workbook for a 13-position magic diamond puzzle using the numbers 1 through 13.

## Files

- `magic_diamond_solver.py`
  - Counts distinct solutions by target sum.
  - Uses multiprocessing and canonical symmetry reduction across rotations and reflections.
- `magic_diamond_target_sum_solver.py`
  - Finds and prints example arrangements for a fixed `TARGET_SUM`.
  - Uses `MAX_SOLUTIONS` to limit how many matching grids are printed.
- `magic_diamond_solution_workbook.xlsx`
  - Excel workbook with a puzzle layout, line-sum formulas, and supporting calculations for checking candidate arrangements.

## Notes

- `magic_diamond_solver.py` requires `tqdm`.
- The workbook is useful for manually checking or exploring candidate solutions.
