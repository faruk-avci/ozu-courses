Purpose
- Help AI coding assistants quickly become productive in this repository (PHYS551 homeworks & projects).

Repository layout (examples)
- `HW1/code/` — C++ simulations and plotting glue (see `HW1/code/HW1.cpp`).
- `HW1/latex/` — LaTeX report for HW1 (`HW1/latex/HW1.tex`).
- `HW2/code/` — Python solutions (see `HW2/code/hw2.py`).
- `HW*/images/` — figures used by LaTeX reports.

Quick orientation
- C++ examples: `HW1/code/HW1.cpp` is the main entry for HW1. It includes a `main()` that calls `run_problem_2()` and `run_problem_3()`; toggle behavior by commenting/uncommenting calls inside `main()`.
- Python examples: run `python3 HW2/code/hw2.py` to execute HW2 scripts; functions like `generate_rayleigh()` and `plot_cdf()` illustrate idiomatic small-script layout.
- LaTeX: reports live in `HW*/latex/` and include images from the `images/` subfolder. `HW1/latex/HW1.tex` shows the document structure and code listing styles.

Build / run commands (concrete examples)
- Compile HW1 C++ (from file comments):
  - Linux: `g++ mc.cpp -std=c++11 -I/usr/include/python3.10 -lpython3.10 -o mc` (adjust python include/name to your system)
  - macOS: `g++ mc.cpp -std=c++11 $(python3-config --cflags) $(python3-config --ldflags) -o mc`
  - Run: `./mc`
- Run Python HW2: `python3 HW2/code/hw2.py`
- Build PDF (LaTeX): from `HW1/latex/` run `latexmk -pdf HW1.tex` or `pdflatex HW1.tex` (the repo includes `listings`/`tcolorbox` styling).

Project-specific patterns and conventions
- C++ code embeds usage and compile instructions in header comments — consult the top of `HW1/code/HW1.cpp` for the supported compile/link flags and `matplotlib-cpp` notes.
- Plotting in C++ uses `matplotlib-cpp` and therefore often requires linking against the local Python installation (`-I` and `-lpythonX.Y`). If `matplotlibcpp.h` is missing, download it into the same folder (see comments in `HW1/code/HW1.cpp`).
- LaTeX reports use `tcolorbox` + `listings` for code blocks; images are referenced from the repo `images/` directories.
- Python scripts are simple scripts (no packaging). Look for `run_...()` or `if __name__ == "__main__"` patterns; `HW2/code/hw2.py` runs on import currently via a top-level call.

Integration points / external deps
- `matplotlib-cpp` header (`matplotlibcpp.h`) — not vendored in some folders; check `HW1/code/`.
- System Python (headers/libs) for C++ linking (adjust `python3` version-specific flags).
- Standard Linux/macOS toolchain for C++ and LaTeX (`g++`, `latexmk` / `pdflatex`).

What AI assistants should do first
1. Open `HW1/code/HW1.cpp` and `HW1/latex/HW1.tex` to learn how compile/run instructions are embedded.
2. Use the concrete compile/run commands above when proposing code edits or CI steps.
3. When adding new code, follow existing structure: put simulations in `HW*/code/` and corresponding reports/figures in `HW*/latex/` and `HW*/images/`.

Limitations discovered
- No automated test harness or CI present; do not assume unit tests exist.
- Some scripts run on import (no `__main__` guard) — be cautious when importing from other modules.

If unclear
- Ask which target platform and Python version to assume for compile/link flags.

Last step
- After changes, regenerate local PDFs and run the example scripts to validate behavior.
