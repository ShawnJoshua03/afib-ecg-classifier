# Clean-cache reproduction — 2026-10-19

Completed on Windows using the existing Python 3.13 virtualenv and pinned packages.
Preserved all original artifacts, deleted `data/processed` after checking its
absolute path, retained `data/raw`, and ran:

```powershell
.venv/Scripts/python.exe -m afib.train
```

The command exited 0. It audited all 8528 recordings, freshly extracted all features,
ran the original 16 candidates across five training-only folds, and evaluated the
same fixed holdout. No overwrite guard was bypassed; no setting or source in the
training pipeline changed.

## Exact comparisons

- Parsed JSON equality passed for results, baselines, all CV candidate/fold scores,
  original and final split, feature schema, tuning plan, fold IDs, and record manifest.
- Both prediction CSVs were byte-identical to the preserved originals. The main
  CSV also passed an exact round-trip float comparison: 1705 unique held-out rows,
  no training overlap, and identical labels and all probability columns.
- The original released estimator and freshly fitted estimator have the same
  `joblib.hash`: `8cc00ebdbf08120e35e3c7b23dde5f65`. This compares estimator state,
  separately from the bundle's surrounding provenance metadata.
- Applying the original released estimator to freshly extracted held-out features
  reproduced every saved prediction; maximum absolute probability difference was 0.0.
- Every README table cell agrees with the JSON at its displayed precision. The
  exact official F1 values remain majority `0.24862081647664583`, RR-logistic
  `0.6668134016177736`, and gradient boosting `0.7800483091787439`. Selected CV
  mean is `0.7923677521918693`, population SD `0.0096546355795168`.

## Bundle metadata difference

The rerun's `selected_model.json` source dictionary adds `demo_data.py`, which was
created after the original fit. All existing source hashes and every other
selection field match. Because selection metadata is embedded in `model.joblib`,
the full rerun bundle is not byte-identical even though its fitted estimator is.
These were the only two artifact differences. After comparison, the original
released model and selection files were restored; their recorded identity is
preserved. Original/rerun snapshots and check output remain locally in ignored
`review-local/`, not in Git.

## Remaining evidence limits

The stale Normal count in `split_final.json`, absence of a model-file digest in
`selected_model.json`, and original-split rather than final-split hash are reported
in [REVIEW_FINDINGS.md](REVIEW_FINDINGS.md). Exact score reproduction does not make
the split patient-independent or clinically validate the detector/model. This was
a reproducibility rerun of frozen choices, not a new tuning round.
