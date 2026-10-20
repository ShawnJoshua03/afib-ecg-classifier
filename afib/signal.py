"""Fixed, exploratory R-peak detector; not a clinically validated beat annotator."""

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, find_peaks, sosfiltfilt

DETECTOR_CONFIG = {
    "band_hz": [5.0, 20.0],
    "filter_order": 3,
    "energy_window_seconds": 0.100,
    "refractory_seconds": 0.250,
    "refinement_radius_seconds": 0.120,
    "height_above_median_fraction_of_q95_range": 0.15,
    "prominence_fraction_of_q95_range": 0.20,
    "minimum_signal_seconds": 1.0,
}


def bandpass(signal, sampling_rate, low, high):
    """Zero-phase Butterworth filter; caller must supply a sufficiently long signal."""
    sos = butter(3, [low, high], btype="bandpass", fs=sampling_rate, output="sos")
    return sosfiltfilt(sos, signal)


def detect_r_peaks(signal, sampling_rate):
    """Return original-sample indices of energy peaks refined to absolute extrema.

    Bandpass 5–20 Hz, square, smooth over 100 ms, then scipy.find_peaks with
    height = median + .15*(q95-median) and prominence = .20*(q95-median).
    These record-local thresholds are fixed before cross-validation. A 250 ms
    refractory interval is imposed both before and after ±120 ms refinement.
    Flat or <1 second input returns no peaks; nonfinite input is rejected.
    """
    signal = np.asarray(signal, dtype=float)
    if signal.ndim != 1 or not np.all(np.isfinite(signal)):
        raise ValueError("Expected a finite, one-dimensional ECG signal")
    if not np.isfinite(sampling_rate) or sampling_rate <= 40:
        raise ValueError("Sampling rate must exceed twice the 20 Hz filter cutoff")
    if len(signal) < max(32, sampling_rate) or np.ptp(signal) == 0:
        return np.array([], dtype=int)
    filtered = bandpass(signal, sampling_rate, 5.0, 20.0)
    envelope = uniform_filter1d(filtered**2, size=max(1, round(0.100 * sampling_rate)))
    floor, upper = np.quantile(envelope, [0.50, 0.95])
    span = upper - floor
    if span <= np.finfo(float).eps:
        return np.array([], dtype=int)
    refractory = max(1, int(np.ceil(0.250 * sampling_rate)))
    candidates, _ = find_peaks(
        envelope,
        distance=refractory,
        height=floor + 0.15 * span,
        prominence=0.20 * span,
    )
    radius = round(0.120 * sampling_rate)
    refined = []
    for index in candidates:
        left, right = max(0, index - radius), min(len(filtered), index + radius + 1)
        refined.append(left + int(np.argmax(np.abs(filtered[left:right]))))
    # Strongest first, deterministic lower-index tie break; enforce spacing after snapping.
    retained = []
    for index in sorted(set(refined), key=lambda item: (-abs(filtered[item]), item)):
        if all(abs(index - previous) >= refractory for previous in retained):
            retained.append(index)
    return np.array(sorted(retained), dtype=int)
