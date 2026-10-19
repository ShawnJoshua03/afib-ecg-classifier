# Skeptical review — 2026-10-19

Reviewed the release at `29968c1` and the follow-up documentation/demo changes.
Line references below identify the reviewed implementation; frozen artifacts were
not edited to conceal discrepancies.

## Findings

1. **Open: stale final-split class count.** `artifacts/split_final.json:7` retains
   the original test counts (N=1015) after the test-side duplicate is excluded in
   `afib/train.py:129`. Its actual IDs, `test_predictions.csv`, and `results.json`
   contain N=1014 and 1705 total. Training IDs and evaluated IDs are disjoint.
   Reported rather than corrected because changing a frozen numeric artifact was
   outside this review's authorization. Use the explicit IDs and results supports.
2. **Open: incomplete model identity binding.** `artifacts/selected_model.json:55`
   records source hashes and four artifact hashes, but no `model.joblib` digest.
   Its `split_sha256` at line 65 hashes the original `split.json`, not
   `split_final.json`. All listed hashes match, and the released joblib bundle's
   embedded selection, feature order, and fitted estimator parameters match the
   JSON. That is a metadata consistency check, not a pre-existing binary checksum.
3. **Fixed: morphology description order.** `FEATURES.md:79` and `FEATURES.md:84`
   now describe demeaning each beat before taking its pointwise median template,
   followed by demeaning the template. This matches `afib/features.py:140`.
   The near-zero norm guard is now described accurately too. No feature changed.
4. **Fixed: claims stronger than evidence.** `README.md:77` now limits the
   no-patient-ID statement to inspected headers/reference labels. The duration
   range is explicitly approximate. The README and demo describe detected peaks
   rather than implying validated R-wave annotations; absolute extrema can fall
   on S waves. The demo explains that the prediction uses the full recording.
5. **Fixed: duplicate/design decisions missing from the log.** SPEC and WORK_LOG
   now record the pre-fit A01176 exclusion and the requested React/Bklit deviation
   from the original plain-HTML demo plan.

## Checks and limits

- Every README result-table cell matches `artifacts/results.json` at the displayed
  precision, including all three models, per-class metrics/supports, and confusion
  counts. CV mean and population SD agree too; CV SD is not a test confidence interval.
- The CSV has exactly 1705 unique record IDs, exactly the final held-out set, with
  no training overlap. All 28 demo records, including 11 mistakes, match the CSV's
  labels, predictions, correctness flags, and probabilities at JSON precision.
- All 34 feature definitions were compared with `afib/features.py`. Extraction is
  record-local and label-free. Cache identity includes source/input hashes
  (`afib/train.py:31`); extraction across all records fits no population transform.
- `afib/model.py:40` accepts training features/labels only; all five folds are
  within training. The selected estimator is fitted at line 111 and serialized at
  line 118 before held-out inference at line 129. There is no test refit path.
  The RR imputation/scaling pipeline fits only training IDs (`afib/train.py:80`).
- README limitations cover undocumented patient IDs and possible same-patient
  overlap, single-device/lead data, label uncertainty, weaker O/~ performance,
  synthetic-only detector validation, uncalibrated probabilities, curated demo
  selection, and no clinical validation/medical-device claim.
- The second exact-duplicate pair (A02656/A03123) in `dataset_audit.json` is
  entirely within the held-out set, so it adds no train/test overlap but means
  not all held-out waveforms are distinct.
  Exact-duplicate removal does not prove patient-independent evaluation.
- Historical ordering is supported by the saved design, source flow, and handoff;
  a code review alone cannot prove every action in an earlier interactive session.

## Reporting guard limitation

`afib/model.py:93–118` writes selection/model artifacts before the held-out-result
comparison at line 153. A failing rerun can therefore leave those artifacts changed
even though it refuses to replace `results.json`. This review preserved a complete
local artifact snapshot before rerunning. No overwrite guard was bypassed.
