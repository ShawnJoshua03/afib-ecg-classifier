# Known edge cases

All four cases found by the edge-case tests in `tests/test_edge_*.py` are fixed, and their tests no longer
use `xfail`. None could occur with the shipped data (300 Hz, non-constant, well-formed records), so the
frozen model's results are unchanged.

The fixes edit `signal.py`, `features.py`, `data.py` and `demo_data.py`, which are hashed into
`artifacts/selected_model.json` (`source_sha256`). Those four hashes are now stale until
`python -m afib.train` is rerun on the raw dataset and the artifacts are recommitted.

| # | Where | Was | Fix |
|---|---|---|---|
| 1 | `afib/signal.py` | Integer truncation bypassed the one-second minimum (250 samples at 250.5 Hz returned one peak). | Compare against the float rate. |
| 2 | `afib/features.py` | Rounding after demeaning gave a constant signal finite spectral ratios instead of NaN. | Zero total power when the signal is constant. |
| 3 | `afib/data.py` | A corrupt `.mat` raised scipy's `MatReadError` or `IndexError`. | Raise `ValueError`. |
| 4 | `afib/demo_data.py` | A missing output folder failed after processing every record. | Create it. |
