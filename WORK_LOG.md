# Build and evaluation log

Times are UTC. The five-hour window begins 2026-10-19 05:01; deadline 10:01.

## Phase 0 — setup

- Python 3.13.5, Git 2.50.0.windows.2, gh 2.102.0 verified.
- GitHub CLI authenticated as ShawnJoshua03; public repository created and cloned.
- Requested scientific packages installed in `.venv`; exact versions in `requirements.txt`.
  Pinned NumPy/SciPy require Python >=3.12; reproduction targets Python 3.13 as used here.
- Archive HEAD verified 99,226,822 bytes, below 500 MB. A slow single connection was
  stopped; the downloader uses eight bounded workers and validates HTTP byte ranges.
- Phase 0 initial commit: `644d779`. Initial push failed because Git created `master`;
  renamed to `main` and pushed successfully. No data or credentials staged.
- CI run 39202824278 passed lint, all three initial metric tests and Pages deployment.
  Live placeholder verified HTTP 200 and rendered in headless Edge.
- Repository topics/homepage edit initially hit an automatic approval-review timeout;
  the permitted retry succeeded. No manual approval remains blocked by that timeout.
- Browser verification uses optional Playwright 1.64.0 with installed Edge.
- Coordinator: GPT-6. User approved delegated model selection during Phase 0.
  GPT-6 Astra (xhigh reasoning) reviews specification, evaluation/feature design and final release.
  GPT-6 Luna (high reasoning) reviews CI/packaging and handles tests, demo and README drafting.
  No in-place `/model` command exists in this tool interface.
- Archive download, CRC validation and extraction completed by 05:21:16 UTC.
  First recorded clock check was 05:01:44 UTC. Verified size 99,226,822 bytes;
  uncompressed 167,419,202 bytes. Exact archive/reference hashes are frozen in downloader.
  No further permission clarification is needed for planned work.
- Astra reviewed the frozen design and pre-fit feature implementation. Fixed a pNN50
  floating-point boundary bug and strengthened header metadata validation before fitting.
  Luna implemented synthetic loading/feature/peak tests; 23 tests pass.

## Handoff task C — local pytest directories (2026-10-19)

- The nine data-loading/split cases already used pytest's built-in `tmp_path`.
  Removed the fixed `--basetemp=.pytest-tmp` setting from `pyproject.toml`.
- Deleted the stale `.pytest-tmp`, `.pytest-data-tmp`, and `.pytest_cache` directories.
  The sandbox also denied access to Windows' normal pytest temp directory; running
  with normal user access passed all 23 tests. No fixtures or assertions were weakened.

## Reporting rules

Record measured scores only after computation. Do not rewrite the model after viewing
test scores. Any correction affecting evaluation must be logged explicitly.
Curated demo mistakes are selected after evaluation solely for inspection, never tuning.
