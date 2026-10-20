# Remaining work

State as of 2026-10-19, commit `90fa09e` (CI green, live demo deployed).
Held-out official mean F1 is **0.780** on 1,705 records (majority 0.249, RR-logistic 0.667).
Do not change the split, seed, metric, model or hyperparameters. The test set has been evaluated once.

## Open items

1. **Done: checksums in `artifacts/selected_model.json`.** Added SHA-256 hex fields
   `model_joblib_sha256` and `split_final_sha256`; provenance metadata only.
2. **Partially verified: regenerated `model.joblib`.** Loading, 34-feature schema/order,
   parameters and demo `predict_proba` checks pass. Full test prediction equality remains
   unverified: neither local checkout has raw records or cached features. Recommend keeping
   the frozen 1.3 MB model in Git; no tracking change made. See
   [verification details](docs/REPRODUCIBILITY.md#saved-model-verification).
3. **Done: demo checked in a browser.** Dark mode, the exact-count table and 390 px width were checked.
   The 390 px check found a sideways scroll from the recording picker, fixed in `demo/src/index.css`.
4. **Dependency advisory.** `braces` (7 high-severity `npm audit` entries) is in shadcn's CLI chain, which is
   used at install time only. Re-check with `npm audit` in `demo/`, and update shadcn if a fix exists.
5. **Vite chunk warning.** The JS bundle is about 517 kB. Optional: code-split.
6. **Security review.** The automatic review of the first push failed with HTTP 429 and was replaced by a manual
   review (`docs/RELEASE_REVIEW.md`). Run `/security-review` on the recent commits if you want it automated.

## Known limitations (keep in README)

- No patient IDs, so the split is by record. Same-patient leakage may inflate scores.
- Test set is a holdout from the public training data, not the challenge's private test set.
- "Other" and "Noisy" are the weakest classes. Only 56 Noisy test records.
- R-peak detector validated on synthetic signals only. Markers can sit on the S wave.
- Probabilities are uncalibrated. Not a medical device; no clinical validation.

## Lessons from this session

- The feature cache reload path was untested until a second run crashed. Consider a test that saves and
  reloads the cache.
- `train.py`, `data.py`, `signal.py` and `features.py` are hashed into the provenance files. Editing them
  changes `selected_model.json` on the next run. Rerun `python -m afib.train` and commit the artifacts.

## Reproduce

```
python -m afib.train                       # about 5 min, clean cache
python -m afib.demo_data                   # builds demo/public/demo_data.json
cp artifacts/results.json demo/public/     # keep the demo chart in sync
cd demo && npm ci && npm run build
ruff check . && pytest
```

Handoff prompt for Codex or Copilot: `../CODEX_HANDOFF.md`. Most of its tasks are already done, see
`docs/HANDOFF_SUMMARY.md`.
