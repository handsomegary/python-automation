# Python Automation

A collection of Python automation scripts for course material downloading and puzzle solving.

## Project Structure

- `course_material_downloaders/`
  - Crawlers and downloaders for course archive pages.
  - Includes selected-file, all-file, resumable, filtered, and multi-root downloader versions.
- `math_puzzle_solver/`
  - Solvers and an Excel workbook for a 13-position magic diamond puzzle.

## Version History

The original scripts used date-based file names. They have been renamed to descriptive file names while preserving the original behavior.

See [`VERSION_HISTORY.md`](VERSION_HISTORY.md) for the old-to-new file mapping and version notes.

## Notes

- Review each script's `BASE_URL`, `BASE_URLS`, and `SAVE_DIR` before running it.
- Some scripts require third-party packages such as `requests`, `beautifulsoup4`, and `tqdm`.
