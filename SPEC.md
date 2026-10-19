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
The active GPT-6 agent handles this session. In-place `/model` switching is unavailable;
the requested strong/cheap phase allocation cannot be claimed as performed.
