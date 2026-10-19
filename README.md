# ECG rhythm classifier (AFib)

[![CI](https://github.com/ShawnJoshua03/afib-ecg-classifier/actions/workflows/ci.yml/badge.svg)](https://github.com/ShawnJoshua03/afib-ecg-classifier/actions/workflows/ci.yml)
[![Live demo](https://img.shields.io/badge/demo-live-blue)](https://shawnjoshua03.github.io/afib-ecg-classifier/)

Atrial fibrillation (AFib) is an irregular heart rhythm that raises stroke risk and often shows up as
irregularly spaced heartbeats on an ECG. This project classifies single-lead ECG recordings from the
open PhysioNet/CinC Challenge 2017 data as **Normal (N), AFib (A), Other rhythm (O) or Noisy (~)**
using classical machine learning. **Not a medical device; no clinical validation.**

**[Live demo](https://shawnjoshua03.github.io/afib-ecg-classifier/)** - 28 curated held-out recordings with
detected R-peaks, true label, prediction and probabilities, including mistakes.

## Results

Held-out test set: 1,705 recordings (record-level stratified 80/20 split, seed 2017; test set never used
for tuning). Metric: the challenge's official score, mean F1 of N, A and O
([equation 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC5978770/)); Noisy still counts in errors.
These are **not** official leaderboard results (the challenge's private test set is not used).

| Model | Official mean F1 | F1 N | F1 A | F1 O | F1 ~ |
|---|---|---|---|---|---|
| Majority class | 0.249 | 0.746 | 0.000 | 0.000 | 0.000 |
| Logistic regression on 7 RR features | 0.667 | 0.822 | 0.671 | 0.507 | 0.357 |
| **Gradient boosting, 34 features** | **0.780** | 0.880 | 0.776 | 0.685 | 0.653 |

5-fold CV on the training portion (used for selection): 0.792 +/- 0.010.

Gradient-boosting per-class results on the test set:

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| N | 0.851 | 0.911 | 0.880 | 1014 |
| A | 0.756 | 0.796 | 0.776 | 152 |
| O | 0.742 | 0.636 | 0.685 | 483 |
| ~ | 0.733 | 0.589 | 0.653 | 56 |

Confusion matrix (rows = true, columns = predicted):

| | N | A | O | ~ |
|---|---|---|---|---|
| **N** | 924 | 11 | 76 | 3 |
| **A** | 8 | 121 | 20 | 3 |
| **O** | 144 | 26 | 307 | 6 |
| **~** | 10 | 2 | 11 | 33 |

All numbers come from `artifacts/results.json`, written by `python -m afib.train`.

## How it works

1. Convert each recording to mV using its WFDB header (sampling rate is read, not assumed).
2. Detect R-peaks with a 5-20 Hz band-pass, energy envelope and `scipy.signal.find_peaks`.
3. Compute 34 features: RR-interval statistics (mean, SD, RMSSD, pNN50, CV, turning-point ratio,
   sample entropy, percentiles), signal-quality and morphology summaries, duration
   (see [FEATURES.md](FEATURES.md)).
4. Train scikit-learn `HistGradientBoostingClassifier` (class-balanced), 16-candidate search chosen by
   5-fold CV on the training split only. No deep learning.

Design and evaluation rules were frozen before fitting: [SPEC.md](SPEC.md). Build log: [WORK_LOG.md](WORK_LOG.md).

## Reproduce

```
python -m venv .venv && .venv/Scripts/activate   # Python 3.13
pip install -r requirements.txt
python -m afib.train        # downloads data (~99 MB), audits, trains, writes artifacts/
python -m afib.demo_data    # builds docs/demo_data.json
pytest
```

## Limitations

- **No patient IDs** in this dataset, so the split is by record. Several recordings may come from the same
  patient, which can inflate test scores. One exact-duplicate signal pair (A00227 in train, A01176 in test)
  crossed the split; the test copy was excluded (1,705 test records instead of 1,706), decided before any model was fit.
- Small dataset (8,528 recordings), single lead, single device. Recordings are 9-61 s.
- Labels are noisy; "Other" is a heterogeneous class and, with "Noisy" (only 56 test records), is the weakest.
- R-peak detection is validated on synthetic signals only; no accuracy against expert beat annotations is claimed.
- Probabilities are uncalibrated. The demo set is curated to include errors and is not an evaluation.
- Not a medical device; no clinical validation; not for diagnosis.

Data: PhysioNet/CinC Challenge 2017, Open Data Commons Attribution License v1.0 ([DATA_LICENSE.md](DATA_LICENSE.md)).
