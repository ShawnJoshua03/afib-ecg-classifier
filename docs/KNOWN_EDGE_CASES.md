# Known edge cases

Found by the edge-case tests in `tests/test_edge_*.py`. Each one is pinned by a strict `xfail`
test, so the suite stays green and the test starts failing loudly (XPASS) once the bug is fixed.

None is fixed on purpose. `signal.py`, `features.py`, `data.py` and `demo_data.py` are hashed into
`artifacts/selected_model.json` (`source_sha256`), and the test set has been evaluated once. A fix
means editing those files, rerunning `python -m afib.train` on the raw dataset and recommitting the
artifacts. None of these can occur with the shipped data (300 Hz, non-constant, well-formed records).

| # | Where | What happens | Trigger | Severity |
|---|---|---|---|---|
| 1 | `afib/signal.py:39` | Integer truncation bypasses the one-second minimum and returns one peak. | 250 samples at 250.5 Hz | Low |
| 2 | `afib/features.py:83` | Rounding error after demeaning creates spectral power, so a constant signal returns finite ratios and entropy instead of NaN. | `np.full(300, 0.1)` at 300 Hz | Medium |
| 3 | `afib/data.py:67` | A corrupt `.mat` raises scipy's `MatReadError` (or `IndexError`) instead of the module's usual `ValueError`. | Valid `.hea` plus an empty `.mat` | Low |
| 4 | `afib/demo_data.py:49` | The output folder is not created, so `main` fails with `FileNotFoundError` after processing all records. | `out` in a folder that does not exist | Low |
