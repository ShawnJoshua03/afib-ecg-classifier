# Handoff summary for Shawn — 2026-10-19

- **Results:** clean-cache training reproduced all scores, CV results, predictions,
  and probabilities exactly. Main official F1 remains 0.7800483091787439 on 1,705
  held-out records; training CV mean remains 0.7923677521918693. No model, feature,
  seed, split assignment, or tuning setting changed. The original model stays in Git.
- **Changed:** removed pytest's fixed temp directory; corrected feature/provenance
  wording; added duplicate/design history, credits, MIT notice and screenshot;
  added demo themes, a text error banner, marker explanation and accurate short-trace
  time axes; updated CI/Pages action majors.
- **Verified:** 23 tests and Ruff pass; production build passes; all 28 recordings
  pass both themes at desktop and 390 px (112 combinations). Release commit
  `63dfa15` passed [CI and Pages deployment](https://github.com/ShawnJoshua03/afib-ecg-classifier/actions/runs/39262359376).
  The live site returned HTTP 200 and passed a headless phone-width check.
- **Cut:** optional confusion-matrix chart only.
- **Follow-up:** `selected_model.json` now includes `model_joblib_sha256` and
  `split_final_sha256`. The saved model loads and passes the 34-feature schema and
  demo inference checks; full test prediction equality remains unverified without
  local raw records or cached features (see [verification](REPRODUCIBILITY.md#saved-model-verification)).
- **Open:** `split_final.json` still has stale pre-exclusion count metadata.
  An unpatched braces advisory remains in shadcn's CLI
  dependency chain (seven high-severity audit entries); the app exposes no glob input.
  Vite's 517.49 kB chunk warning remains. Patient-independence and clinical validity
  are not established.

Details: [reproduction](REPRODUCIBILITY.md), [skeptical review](REVIEW_FINDINGS.md),
[security/release review](RELEASE_REVIEW.md). The original automatic security-review
HTTP 429 was handled by manual review, not claimed to have later passed.
