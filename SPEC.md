# Project specification

## Goal and time box

Classify public PhysioNet/CinC 2017 single-lead ECG recordings into Normal (N), AFib (A),
Other rhythm (O), or Noisy (~), with a reproducible classical ML pipeline and static demo.
Work starts 2026-10-19 05:01 UTC; hard deadline 10:01 UTC. Setup deadline 05:21 UTC.
Author: Shawn (ShawnJoshua03). Never fabricate or estimate a result.

## Verified source facts

- Dataset: https://physionet.org/content/challenge-2017/1.0.0/
- Archive: https://physionet.org/files/challenge-2017/1.0.0/training2017.zip
- HTTP HEAD Content-Length checked before download: 99,226,822 bytes (<500 MB).
- Official documentation describes 8,528 public training recordings, single lead, 300 Hz,
  in MATLAB V4 files with WFDB headers. Audit every file before claiming measured counts,
  sampling rates, or duration ranges. Archive SHA-256 will be recorded in data provenance.
- Data license on source page: Open Data Commons Attribution License v1.0.
- Verified archive SHA-256: `25fdbab36bb6724b66a4d2c26ff89f6b9d6ff87e6aed714d24cf5bf071cd1255`.
  CRC check passed; 17,059 files, 167,419,202 uncompressed bytes.
- Downloaded final v3 reference has 8,528 rows: N=5,076, A=758, O=2,415, ~=279.
  SHA-256: `ae517e474b0bc89a7517ad876b5b4dadc6c94f680d0665c04746db9432df855b`.
- The source provides revised label versions. Inspect archive REFERENCE.csv against v3,
  use final v3 labels, and explicitly record any differences; never silently mix versions.
- The challenge's private test set is not used. This project's test is a local holdout
  from the public training data; scores are not official challenge leaderboard results.
- Inspect supplied metadata for patient identifiers. Record IDs must not be treated as
  patient IDs. If patient IDs are absent, record that fact and the leakage limitation.

## Metric

Final official metric: (F1_N + F1_A + F1_O) / 3, with F1_c = 2TP/(2TP+FP+FN).
Keep all four classes in the confusion matrix and FP/FN counting; exclude only Noisy's
F1 from the final average. Undefined F1 is zero. Report each class's precision, recall,
F1 and support. Cite equation 1 of the final paper:
https://pmc.ncbi.nlm.nih.gov/articles/PMC5978770/
The old dataset webpage still displays a four-class average; do not use that formula.

## Split and selection rule (freeze before fitting)

If no patient IDs: sort record IDs, stratified 80/20 train/test split, seed 2017.
Save explicit train/test record IDs and input hashes. Never change the split or tune on test.
Pre-fit duplicate audit found A00227 (train) and A01176 (test) to be identical signals.
The test copy A01176 was excluded before any model fitting; the original split remains
in `artifacts/split.json`, and the evaluated 1,705 test IDs are in `artifacts/split_final.json`.
Its copied `test_class_counts` metadata still describes the original 1,706-record split;
use the final IDs and `results.json` supports (see `docs/REVIEW_FINDINGS.md`).
The seed and all remaining assignments were unchanged; this does not establish patient independence.
Use five-fold StratifiedKFold(shuffle=True, random_state=2017) inside training only.
Fit imputation/scaling within each fold where required. Any feature transformations are
record-local and label-free. Optimize only the official mean F1 on CV folds.
Select HistGradientBoostingClassifier hyperparameters using training CV. Freeze selected
parameters before evaluating test. Baseline test scores are recorded but must not guide
features or model selection. If a correctness bug forces reevaluation, disclose it.
Do not retrain the released model on the holdout: demo records must remain unseen.

## Methods

- Majority baseline fitted to training labels.
- Simple multinomial logistic regression on RR mean, SD, RMSSD, pNN50, coefficient of
  variation, turning-point ratio, and sample entropy; median imputation + indicators and
  standard scaling fit on training only; fixed regularization C=1, no tuning.
- SciPy bandpass / energy-envelope R-peak detector with documented refractory period;
  synthetic validation, no claim of validated real ECG beat annotations.
- Main features: baseline RR features, signal quality and morphology summaries, duration.
  Keep unusable RR summaries as missing values; do not drop difficult/noisy recordings.
- HistGradientBoostingClassifier, fixed seed, bounded CV search, no deep learning.
- Candidate search and feature definitions documented before test evaluation.
- Probabilities are uncalibrated model outputs, not clinical certainty.

## Pre-evaluation design review

This plan is declared before model fitting or held-out evaluation. The split and metric
above are unchanged. Record any implementation deviation before opening test results.

### Selection and evaluation details

- Use all four labels in stratification, fitting, prediction and confusion matrices.
  The scikit-learn scorer must call `official_f1`; ordinary four-class `f1_macro` is
  a different quantity. Never remove Noisy records before scoring.
- Fit the main model directly on numeric features with native missing-value handling;
  no global imputation or scaling. For the logistic baseline, keep imputation,
  missingness indicators and scaling inside its fold-fitted pipeline. Use `lbfgs`,
  C=1, no class weighting, and a sufficiently high fixed iteration limit; record any
  convergence warning rather than silently treating an unfinished fit as converged.
- HGB fixed parameters: `learning_rate=0.08`, `max_iter=200`,
  `early_stopping=False`, `random_state=2017`, `max_bins=255`.
  The 16 candidates are the Cartesian product of `max_leaf_nodes=[15,31]`,
  `min_samples_leaf=[40,20]`, `l2_regularization=[1.0,0.0]`, and
  `class_weight=[None,"balanced"]`. Balanced weights are computed by each fold's
  own fit, never from the whole dataset. Enumerate in the listed nested-loop order.
- Rank by the unweighted arithmetic mean of the five official fold F1 scores;
  exact ties choose the first listed candidate. Save every fold score, mean, standard
  deviation, candidate parameters and fold record IDs. A pooled out-of-fold F1, if
  reported, is a separate descriptive statistic and not the selection criterion.
- Refit the winning candidate once on all training records. Freeze feature code,
  candidate results, parameters, source versions and split hashes before the single
  held-out evaluation. Predictions use the fitted estimator's normal argmax rule;
  there is no test-driven threshold or class-weight adjustment. Map probability
  columns using `classes_`, never an assumed class order.
- Baselines and the selected model use identical held-out IDs. Report raw confusion
  counts with rows=true and columns=predicted in N,A,O,~ order, plus all class
  supports. `classification_report`'s four-class macro average must not be presented
  as the official metric. CV variability is not a test confidence interval.
- Audit exact duplicate waveform hashes before fitting, and report any cross-split
  overlap. If overlap exists, review it before fitting instead of silently changing
  the frozen split. Absence of exact duplicates does not establish patient independence.

### Feature and detector definitions

- Detector configuration is fixed before CV, with constants and failure behavior
  documented in the implementation. Use a 5-20 Hz zero-phase SOS bandpass for squared
  QRS energy, a 100 ms smoothing window and a 250 ms refractory period. Refine
  candidates within +/-120 ms to absolute extrema so inverted ECG polarity is supported, then
  deduplicate and enforce the refractory interval again after refinement. Preserve
  original-signal time coordinates for demo markers. Do not call these annotated beats.
- Synthetic checks must cover known timing, inverted polarity, flat input and very
  short input. Do not tune detector constants by inspecting held-out traces, labels,
  missingness patterns or model errors. Short/degenerate signals must have explicit
  deterministic behavior, without dropping the recording.
- RR values are consecutive detected-peak differences in seconds. Do not discard
  unusual intervals merely because they are unlike normal rhythm; this can erase the
  target signal. Record peak count and, if used, a separately named implausible-interval
  fraction. Use mean, sample SD (`ddof=1`), RMSSD, fraction of absolute adjacent RR differences
  strictly greater than 0.050 seconds, SD/mean, and strict turning-point fraction
  (`(RR[i]-RR[i-1])*(RR[i+1]-RR[i]) < 0`, denominator `n_RR-2`). Mean needs one RR;
  SD/CV/RMSSD/pNN50 need two; turning-point fraction needs three. Other cases are NaN.
- Sample entropy: m=2, Chebyshev distance, r=0.2 times population RR SD, no self
  matches, and at least ten RR intervals. Compare distinct template pairs using the
  same valid starting indices for length m and m+1; entropy is `-log(A/B)`.
  A constant sufficiently long RR sequence has entropy zero. If A or B is zero,
  return NaN rather than infinity or an arbitrary cap. Document that this unstable
  short-record statistic is an exploratory feature, not a clinical HRV measure.
- Compute spectral quality ratios from the original demeaned waveform, before the
  narrow QRS filter. Otherwise the detector's filter would manufacture low noise
  ratios. Fix Welch window/overlap, frequency-band endpoints and denominator in code;
  zero total power produces missing ratios. Do not interpret raw ECG PSD ratios as
  conventional LF/HF heart-rate-variability measurements.
- Flatness is a specified fraction of equal consecutive raw ADC samples. A feature
  based on repeated observed minima/maxima is a clipping proxy, not proof of ADC
  saturation; use that name unless actual ADC rails are verified from metadata.
  Peak amplitude variation and beat-template consistency use a 0.5-40 Hz broad
  morphology signal. Templates require full fixed windows and at least five beats;
  zero-variance templates yield NaN, not a perfect correlation. A detected-peak
  half-prominence width may be included as a named proxy; it is not clinical QRS
  duration because no validated beat delineation is performed.
- Recording duration is sample_count / sampling_frequency. Do not use record ID,
  filename, label version, split membership or data-file ordering as predictors.
  Feature order, units and definitions are saved with the model. Missing values are
  allowed, infinities are not. Label-free extraction may be cached per record, but
  distribution-dependent preprocessing belongs only inside training folds.

References checked during review: the [final challenge paper, equation 1](
https://physionet.org/files/challenge-2017/1.0.0/Clifford_et-al-challenge_2017_CinC_paper.pdf),
[scikit-learn F1 semantics](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html),
and [HGB missing values, weighting and early stopping](
https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html).

## Success criteria

1. All data and labels validated; deterministic split; raw files and credentials excluded.
2. Real baseline and main-model scores saved with per-record held-out predictions,
   CV scores, four-class confusion matrix, environment versions, source hashes and model.
3. `python -m afib.train` reproduces results; README numeric results generated from outputs.
4. Static HTML/JS demo contains about 30 held-out examples spanning all classes and failures,
   with trace, marked detected peaks, labels and probabilities. Curated set is not an evaluation.
5. pytest covers loading, synthetic peaks, known feature inputs and hand-computed scoring;
   ruff and pytest pass in GitHub Actions, then Pages deploys.
6. README honestly describes limitations and links code, provenance, results and demo.
No minimum score is promised. Report weak results and failures as measured.

## Non-goals and limitations to preserve

No diagnosis, uploaded user ECG inference, treatment advice, clinical validation, real-time
monitoring, patient-independent claims without identifiers, or benchmark superiority claims.
Small single-device, single-lead dataset; label uncertainty; heterogeneous Other class;
few Noisy records. Describe measured weak classes accurately rather than assuming rankings.
Noisy and Other are expected challenges, not a predeclared empirical conclusion.

## Execution and scope

Commit after setup, baseline, model, demo/tests, documentation/release, and final review.
Cut demo polish, then extra features, then tuning if a phase overruns by >20 minutes.
Never cut official scoring, holdout evaluation, or limitations.
Coordinator: GPT-6. With the user's Phase 0 authorization, delegated GPT-6 Astra reviews
the specification, feature/evaluation design and final release; GPT-6 Luna handles
CI/packaging review, tests, demo and README drafting. In-place `/model` switching is unavailable.
