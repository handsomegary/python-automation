# Version History

This project was originally organized with date-based file names. The files have been renamed to describe their purpose while preserving the original code behavior.

## Math Puzzle Solver

| Original file | New file | Summary |
| --- | --- | --- |
| `2025120603.py` | `math_puzzle_solver/magic_diamond_solver.py` | Solves a 13-position equal-sum diamond puzzle using numbers 1 through 13. It uses backtracking, canonical symmetry reduction across rotations/reflections, multiprocessing by center value, and reports the number of distinct solutions for each target sum. |
| `code.py` | `math_puzzle_solver/magic_diamond_target_sum_solver.py` | Finds example arrangements for a fixed target sum. It uses backtracking, configurable `TARGET_SUM` and `MAX_SOLUTIONS` settings, and prints each matching grid. |
| `20251205.xlsx` | `math_puzzle_solver/magic_diamond_solution_workbook.xlsx` | Excel workbook for the magic diamond puzzle. It contains a grid-style puzzle layout, line-sum formulas, and supporting calculations for checking candidate arrangements. |

## Course Material Downloaders

| Original file | New file | Summary |
| --- | --- | --- |
| `20260322.py` | `course_material_downloaders/nthuee_aic_selected_file_downloader.py` | First NTHU EE AIC archive crawler. It recursively follows directory links under `https://nthuee.org/archive/AIC/` and downloads selected file types: PDF, DOCX, PPTX, and PNG. |
| `2026032201.py` | `course_material_downloaders/nthuee_aic_all_files_downloader.py` | Variant of the AIC archive crawler that changes the extension filter to download every non-directory file under the AIC archive instead of only selected file types. |
| `2026032202.py` | `course_material_downloaders/nctu_comm06_resumable_downloader.py` | Switches the target to the NCTU `Comm06_I` course site and adds a retry-enabled HTTP session, resumable downloads with `Range` headers, larger streamed chunks, per-file retry handling, and a `failed_downloads.txt` log. |
| `2026032701.py` | `course_material_downloaders/nctu_co13_filtered_resumable_downloader.py` | Switches the target to the NCTU `co_13` course site and adds URL normalization, a broad allowed-extension list, Apache directory-sort query skipping, local path conflict checks, 416 resume recovery, and safer crawl deduplication. |
| `2026032702.py` | `course_material_downloaders/multi_root_course_material_downloader.py` | Generalizes the downloader to support multiple root URLs through `BASE_URLS`. It adds skip-directory rules, duplicate URL statistics, remote size checks, detailed failure categories, a full failure report, and a printed summary. |

## Notes

- The rename is organizational only; script logic was not changed.
- `course_material_downloaders/multi_root_course_material_downloader.py` appears to be the most developed downloader version.
- The current `BASE_URLS` value in `multi_root_course_material_downloader.py` should be reviewed before running, because the first URL appears to contain a duplicated URL prefix.
