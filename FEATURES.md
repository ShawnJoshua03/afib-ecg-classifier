# Fixed feature definitions

All features are computed independently for each recording. No label, record ID, file order,
patient metadata, or split membership is a predictor. Waveforms are converted to mV with
the gain and baseline in their WFDB header. The sampling rate is read, not assumed.
There are 34 features. Feature order and detector constants are also saved with the model.

## Detected peaks

The exploratory detector uses a third-order 5–20 Hz Butterworth SOS filter applied
forward/backward, squared energy averaged over 100 ms, and `scipy.signal.find_peaks`.
For the energy envelope, let `d = q95 - median`. Height is `median + 0.15*d` and minimum
prominence is `0.20*d`. Candidates must be 250 ms apart. Each is moved to the strongest
absolute filtered extremum within ±120 ms; candidates are then deduplicated and the
250 ms spacing is enforced again, retaining stronger peaks first. It supports inverted
polarity. Flat signals and signals shorter than one second return no peaks.

These are **detected peaks**, not expert beat annotations. No real-ECG peak accuracy is
claimed. Synthetic timing checks cannot establish clinical accuracy. RR intervals are
consecutive detected-peak differences in seconds; unusual intervals are retained.

## RR features

| Feature | Definition |
|---|---|
| `rr_mean_s` | Arithmetic mean RR; at least one interval |
| `rr_std_s` | Sample SD (`ddof=1`); at least two intervals |
| `rr_rmssd_s` | Root mean squared successive RR difference; at least two |
| `rr_pnn50` | Fraction of absolute successive differences >50 ms; at least two; 1 ps numerical tolerance prevents exact 50 ms differences crossing through float roundoff |
| `rr_cv` | Sample SD / mean; at least two |
| `rr_turning_point_ratio` | Strict local extrema / (`n_RR-2`); ties are not extrema; at least three |
| `rr_sample_entropy` | SampEn, m=2, tolerance=0.2 × population SD; at least ten RR |
| `rr_median_s` | Median RR |
| `rr_iqr_s` | 75th minus 25th percentile RR |
| `rr_p10_s` | 10th percentile RR |
| `rr_p90_s` | 90th percentile RR |
| `rr_min_s` | Minimum RR |
| `rr_max_s` | Maximum RR |
| `rr_implausible_fraction` | Fraction RR <0.3 s or >2 s; a detector-quality proxy, not a clinical rhythm rule |

SampEn compares distinct unordered template pairs by Chebyshev distance, excluding
self-matches. Length-m and length-(m+1) templates use the same starting positions;
with match counts B and A respectively, entropy is `-log(A/B)`. A sufficiently long
constant sequence gives zero. Zero A/B counts or too few intervals give NaN. This
short-record statistic is exploratory, not a validated clinical HRV measure.

## Recording and signal quality

| Feature | Definition |
|---|---|
| `duration_s` | Sample count / header sampling rate |
| `n_detected_peaks` | Number of detected peaks |
| `peak_rate_hz` | Detected peak count / duration |
| `signal_std_mv` | Population SD of the raw physical waveform |
| `signal_iqr_mv` | Raw 75th minus 25th percentile |
| `signal_p99_p01_range_mv` | Raw 99th minus 1st percentile |
| `signal_skewness` | Bias-corrected sample skewness; constant signal → NaN |
| `signal_excess_kurtosis` | Bias-corrected excess kurtosis; constant signal → NaN |
| `flat_step_fraction` | Fraction of consecutive raw sample pairs that are exactly equal |
| `observed_extrema_fraction` | Fraction equal to the observed minimum or maximum; a clipping proxy, not verified ADC saturation |
| `difference_std_over_signal_std` | Population SD of sample differences / raw population SD |

## Spectral and morphology summaries

Welch PSD is calculated on the **raw demeaned waveform**, before the detector filter:
4-second Hann windows (or the full signal if shorter), 50% overlap, no additional
detrending. Ratios sum uniform-grid PSD bins with left-inclusive/right-exclusive bands;
the denominator includes all bins from zero through Nyquist. Zero power gives NaN.

| Feature | Definition |
|---|---|
| `power_baseline_ratio` | Power in [0, 0.5) Hz / total |
| `power_qrs_band_ratio` | Power in [5, 20) Hz / total |
| `power_high_frequency_ratio` | Power in [40, 100) Hz / total |
| `power_mains_ratio` | Power in [48, 52) plus [58, 62) Hz / total |
| `spectral_entropy` | Shannon entropy of normalized PSD / log(number of PSD bins) |
| `peak_amplitude_median_mv` | Median absolute amplitude at detected peaks in a 0.5–40 Hz waveform |
| `peak_amplitude_cv` | Sample SD / mean absolute peak amplitude; at least two peaks |
| `template_correlation_median` | Median Pearson correlation between demeaned complete beats and the pointwise median of those demeaned beats |
| `template_low_correlation_fraction` | Fraction of those correlations <0.8 |

Morphology uses a third-order zero-phase 0.5–40 Hz Butterworth filter. Beat windows span
−200 through +400 ms around each detected peak and must fit fully inside the signal.
At least five complete windows are required. Each beat is demeaned before calculating
the pointwise median template, which is then demeaned too. If any beat norm multiplied
by the template norm is at most machine epsilon, correlation features are NaN. These features do not
delineate P waves or measure clinical QRS duration. Spectral ratios are not LF/HF HRV.

## Missing values

Undefined summaries are NaN, never an arbitrary replacement or infinity. Records with
poor detections remain in the evaluation. The main model uses native missing-value
handling. The RR-only logistic baseline uses train-fitted median imputation, missingness
indicators and standard scaling. Its seven inputs are the first seven RR features above.
