"""Record-local ECG features. Missing physiology stays NaN; no records are dropped."""

import numpy as np
from scipy.signal import welch
from scipy.spatial.distance import pdist
from scipy.stats import kurtosis, skew

from afib.signal import bandpass, detect_r_peaks

RR_BASELINE_FEATURES = [
    "rr_mean_s",
    "rr_std_s",
    "rr_rmssd_s",
    "rr_pnn50",
    "rr_cv",
    "rr_turning_point_ratio",
    "rr_sample_entropy",
]


def sample_entropy(values, m=2, tolerance_fraction=0.2):
    """SampEn with common template starts and unordered pairs, requiring >=10 RR.

    r is tolerance_fraction * population SD. No self matches. Constant sequences
    return zero; zero match counts or insufficient observations return NaN.
    """
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("Sample entropy requires finite one-dimensional input")
    if m < 1 or tolerance_fraction < 0:
        raise ValueError("Invalid sample entropy parameters")
    if len(values) < max(10, m + 2):
        return np.nan
    if np.ptp(values) == 0:
        return 0.0
    tolerance = tolerance_fraction * np.std(values, ddof=0)
    templates = np.lib.stride_tricks.sliding_window_view(values, m + 1)
    b_count = np.count_nonzero(pdist(templates[:, :m], metric="chebyshev") <= tolerance)
    a_count = np.count_nonzero(pdist(templates, metric="chebyshev") <= tolerance)
    if a_count == 0 or b_count == 0:
        return np.nan
    return float(-np.log(a_count / b_count))


def rr_features(rr):
    """RR in seconds; unusual intervals are retained, never clipped or deleted."""
    rr = np.asarray(rr, dtype=float)
    if rr.ndim != 1 or not np.all(np.isfinite(rr)) or np.any(rr <= 0):
        raise ValueError("RR intervals must be finite, positive and one-dimensional")
    mean = float(np.mean(rr)) if len(rr) else np.nan
    std = float(np.std(rr, ddof=1)) if len(rr) >= 2 else np.nan
    differences = np.diff(rr)
    return {
        "rr_mean_s": mean,
        "rr_std_s": std,
        "rr_rmssd_s": float(np.sqrt(np.mean(differences**2))) if len(rr) >= 2 else np.nan,
        # 1 ps tolerance prevents exact 50 ms sample differences crossing via roundoff.
        "rr_pnn50": float(np.mean(np.abs(differences) > 0.050 + 1e-12)) if len(rr) >= 2 else np.nan,
        "rr_cv": std / mean if len(rr) >= 2 else np.nan,
        "rr_turning_point_ratio": float(np.mean(differences[:-1] * differences[1:] < 0))
        if len(rr) >= 3
        else np.nan,
        "rr_sample_entropy": sample_entropy(rr),
        "rr_median_s": float(np.median(rr)) if len(rr) else np.nan,
        "rr_iqr_s": float(np.subtract(*np.percentile(rr, [75, 25]))) if len(rr) else np.nan,
        "rr_p10_s": float(np.percentile(rr, 10)) if len(rr) else np.nan,
        "rr_p90_s": float(np.percentile(rr, 90)) if len(rr) else np.nan,
        "rr_min_s": float(np.min(rr)) if len(rr) else np.nan,
        "rr_max_s": float(np.max(rr)) if len(rr) else np.nan,
        "rr_implausible_fraction": float(np.mean((rr < 0.3) | (rr > 2.0))) if len(rr) else np.nan,
    }


def spectral_features(signal, sampling_rate):
    """Welch density on demeaned raw ECG, 4 s Hann windows, 50% overlap.

    Ratios are sums of uniform-grid PSD bins divided by total PSD over [0, Nyquist].
    Bands are left-inclusive/right-exclusive: [0,.5), [5,20), [40,100),
    and [48,52) union [58,62). Zero total power gives missing ratios.
    """
    nperseg = min(len(signal), round(4 * sampling_rate))
    frequency, power = welch(
        signal - np.mean(signal),
        fs=sampling_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=nperseg // 2,
        detrend=False,
        scaling="density",
    )
    total = np.sum(power) if np.ptp(signal) > 0 else 0.0

    def ratio(mask):
        return float(np.sum(power[mask]) / total) if total > 0 else np.nan

    distribution = power[power > 0] / total if total > 0 else np.array([])
    return {
        "power_baseline_ratio": ratio(frequency < 0.5),
        "power_qrs_band_ratio": ratio((frequency >= 5) & (frequency < 20)),
        "power_high_frequency_ratio": ratio((frequency >= 40) & (frequency < 100)),
        "power_mains_ratio": ratio(
            ((frequency >= 48) & (frequency < 52)) | ((frequency >= 58) & (frequency < 62))
        ),
        "spectral_entropy": float(-np.sum(distribution * np.log(distribution)) / np.log(len(power)))
        if len(distribution) and len(power) > 1
        else np.nan,
    }


def morphology_features(signal, sampling_rate, peaks):
    """Amplitude/template summaries in 0.5–40 Hz, not validated clinical measurements.

    Complete beat windows span -200 to +400 ms. At least five are required.
    Correlate each demeaned beat with the pointwise median template. A constant
    template or any constant beat makes both correlation summaries missing.
    """
    result = dict.fromkeys(
        [
            "peak_amplitude_median_mv",
            "peak_amplitude_cv",
            "template_correlation_median",
            "template_low_correlation_fraction",
        ],
        np.nan,
    )
    if len(signal) < max(32, int(sampling_rate)):
        return result
    broad = bandpass(signal, sampling_rate, 0.5, 40.0)
    amplitudes = np.abs(broad[peaks])
    if len(amplitudes):
        result["peak_amplitude_median_mv"] = float(np.median(amplitudes))
    if len(amplitudes) >= 2 and np.mean(amplitudes) > 0:
        result["peak_amplitude_cv"] = float(np.std(amplitudes, ddof=1) / np.mean(amplitudes))
    before, after = round(0.2 * sampling_rate), round(0.4 * sampling_rate)
    beats = [
        broad[p - before : p + after + 1] for p in peaks if p >= before and p + after < len(signal)
    ]
    if len(beats) < 5:
        return result
    beats = np.asarray(beats)
    beats -= beats.mean(axis=1, keepdims=True)
    template = np.median(beats, axis=0)
    template -= template.mean()
    norms = np.linalg.norm(beats, axis=1) * np.linalg.norm(template)
    if np.any(norms <= np.finfo(float).eps):
        return result
    correlations = np.clip((beats @ template) / norms, -1.0, 1.0)
    result["template_correlation_median"] = float(np.median(correlations))
    result["template_low_correlation_fraction"] = float(np.mean(correlations < 0.8))
    return result


def extract_features(signal, sampling_rate):
    """Return a stable ordered mapping, plus peak indices for audit/demo reuse."""
    signal = np.asarray(signal, dtype=float)
    if signal.ndim != 1 or not len(signal) or not np.all(np.isfinite(signal)):
        raise ValueError("Expected a nonempty finite ECG vector")
    if sampling_rate <= 80:
        raise ValueError("Feature filters require sampling rate >80 Hz")
    peaks = detect_r_peaks(signal, sampling_rate)
    result = rr_features(np.diff(peaks) / sampling_rate)
    std = float(np.std(signal))
    result.update(
        {
            "duration_s": len(signal) / sampling_rate,
            "n_detected_peaks": float(len(peaks)),
            "peak_rate_hz": len(peaks) * sampling_rate / len(signal),
            "signal_std_mv": std,
            "signal_iqr_mv": float(np.subtract(*np.percentile(signal, [75, 25]))),
            "signal_p99_p01_range_mv": float(np.subtract(*np.percentile(signal, [99, 1]))),
            "signal_skewness": float(skew(signal, bias=False)) if std > 0 else np.nan,
            "signal_excess_kurtosis": float(kurtosis(signal, bias=False)) if std > 0 else np.nan,
            "flat_step_fraction": float(np.mean(np.diff(signal) == 0))
            if len(signal) > 1
            else np.nan,
            "observed_extrema_fraction": float(
                np.mean((signal == signal.min()) | (signal == signal.max()))
            ),
            "difference_std_over_signal_std": float(np.std(np.diff(signal)) / std)
            if std > 0 and len(signal) > 1
            else np.nan,
        }
    )
    result.update(spectral_features(signal, sampling_rate))
    result.update(morphology_features(signal, sampling_rate, peaks))
    if np.any(np.isinf(list(result.values()))):
        raise ValueError("Infinite feature value")
    return result, peaks
