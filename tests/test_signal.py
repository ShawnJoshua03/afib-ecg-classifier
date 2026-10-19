import numpy as np

from afib.signal import detect_r_peaks


def synthetic_qrs(sampling_rate=250, duration=5.0, times=(0.7, 1.5, 2.3, 3.1, 3.9, 4.7)):
    time = np.arange(round(duration * sampling_rate)) / sampling_rate
    signal = 0.25 * np.sin(2 * np.pi * 0.3 * time)
    for peak_time in times:
        signal += np.exp(-0.5 * ((time - peak_time) / 0.025) ** 2)
    return signal


def test_detect_r_peaks_matches_known_qrs_with_baseline_wander():
    sampling_rate = 250
    expected_times = np.array([0.7, 1.5, 2.3, 3.1, 3.9, 4.7])

    peaks = detect_r_peaks(synthetic_qrs(sampling_rate), sampling_rate)

    assert len(peaks) == len(expected_times)
    assert np.max(np.abs(peaks / sampling_rate - expected_times)) <= 0.030


def test_detect_r_peaks_supports_inverted_polarity():
    sampling_rate = 250
    signal = synthetic_qrs(sampling_rate)

    upright = detect_r_peaks(signal, sampling_rate)
    inverted = detect_r_peaks(-signal, sampling_rate)

    np.testing.assert_array_equal(inverted, upright)


def test_detect_r_peaks_returns_empty_for_flat_and_short_signals():
    sampling_rate = 250

    assert detect_r_peaks(np.zeros(3 * sampling_rate), sampling_rate).size == 0
    assert detect_r_peaks(synthetic_qrs(sampling_rate, duration=0.8), sampling_rate).size == 0


def test_refined_peaks_obey_refractory_period():
    sampling_rate = 250
    signal = synthetic_qrs(
        sampling_rate,
        duration=4.0,
        times=(0.6, 1.0, 1.25, 2.0, 3.0),
    )

    peaks = detect_r_peaks(signal, sampling_rate)

    assert len(peaks) >= 3
    assert np.all(np.diff(peaks) >= np.ceil(0.250 * sampling_rate))
