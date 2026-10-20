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

The stale Normal count in `split_final.json` remains reported in
[REVIEW_FINDINGS.md](REVIEW_FINDINGS.md). The missing model and final-split digests
were added in the follow-up below. Exact score reproduction does not make
the split patient-independent or clinically validate the detector/model. This was
a reproducibility rerun of frozen choices, not a new tuning round.

## Saved-model verification

Follow-up on 2026-10-19 used the existing Python virtualenv without training or
downloads. `joblib.load` passed; the estimator, bundle and feature schema agree on
all 34 features and their order, and estimator parameters match the selection.
`predict_proba` passed on features extracted from demo records A00633, A03176 and
A03627: shape (3, 4), finite probabilities in [0, 1], and row sums equal to 1.
These are rounded, at-most-12-second waveforms, not full-record test features.
Neither this worktree nor `C:/Users/shawn/afib-ecg-classifier` contains raw records
or cached features. Exact predictions and probabilities for all 1,705 rows of
`artifacts/test_predictions.csv` therefore remain unverified for this saved bundle.

`selected_model.json` now records SHA-256 hex digests in `model_joblib_sha256`
and `split_final_sha256`; `split_sha256` still refers to the original `split.json`.
Only the external JSON gained these fields; embedded selection matches its other
fields. The model binary was not rewritten. The unchanged training code does not
emit these two additions, so a future authorized regeneration must refresh them.
The four older artifact hashes (`split_sha256`, `feature_schema_sha256`,
`cv_results_sha256`, `tuning_plan_sha256`) match CRLF versions of their JSON files,
not this checkout's LF bytes. They were left unchanged; the two new hashes cover
the actual bytes in this checkout.
Recommendation: keep this roughly 1.3 MB frozen model in Git for reproducible
inference; reconsider release assets or Git LFS if model versions accumulate.
No tracking change was made.
