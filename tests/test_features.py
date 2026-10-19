from itertools import combinations

import numpy as np
import pytest

from afib.features import extract_features, rr_features, sample_entropy, spectral_features


def independent_entropy(values, m=2, tolerance_fraction=0.2):
    """Count Chebyshev template matches directly from the definition."""
    values = np.asarray(values, dtype=float)
    tolerance = tolerance_fraction * np.std(values, ddof=0)
    starts = range(len(values) - m)

    def count_matches(length):
        count = 0
        for left, right in combinations(starts, 2):
            distance = np.max(
                np.abs(values[left : left + length] - values[right : right + length])
            )
            count += distance <= tolerance
        return count

    b_count = count_matches(m)
    a_count = count_matches(m + 1)
    return -np.log(a_count / b_count)


def test_rr_features_match_hand_calculated_statistics():
    rr = np.array([0.5, 0.625, 0.65625, 0.75, 0.71875, 0.875])

    features = rr_features(rr)

    assert features["rr_mean_s"] == pytest.approx(0.6875)
    assert features["rr_std_s"] == pytest.approx(np.sqrt(0.080078125 / 5))
    assert features["rr_rmssd_s"] == pytest.approx(np.sqrt(0.05078125 / 5))
    assert features["rr_pnn50"] == pytest.approx(3 / 5)
    assert features["rr_cv"] == pytest.approx(np.sqrt(0.080078125 / 5) / 0.6875)
    assert features["rr_turning_point_ratio"] == pytest.approx(2 / 4)


def test_pnn50_uses_strict_50ms_threshold_at_300hz():
    base_rr = 0.8

    exactly_50_ms = rr_features([base_rr, base_rr + 15 / 300])
    above_50_ms = rr_features([base_rr, base_rr + 16 / 300])
    negative_above_50_ms = rr_features([base_rr + 16 / 300, base_rr])

    assert exactly_50_ms["rr_pnn50"] == 0.0
    assert above_50_ms["rr_pnn50"] == 1.0
    assert negative_above_50_ms["rr_pnn50"] == 1.0


def test_sample_entropy_constant_short_and_independent_match_count():
    assert sample_entropy(np.ones(10)) == 0.0
    assert np.isnan(sample_entropy(np.arange(9, dtype=float)))

    repeating = np.tile([0.0, 1.0], 5)
    assert sample_entropy(repeating) == pytest.approx(independent_entropy(repeating))


def test_sample_entropy_returns_missing_when_templates_do_not_match():
    assert np.isnan(sample_entropy(np.arange(10, dtype=float) * 10))


def test_flat_waveform_retains_missing_features_without_infinities():
    features, peaks = extract_features(np.zeros(1000), 250)

    assert peaks.size == 0
    assert features["rr_mean_s"] != features["rr_mean_s"]
    assert features["power_high_frequency_ratio"] != features["power_high_frequency_ratio"]
    assert not np.isinf(list(features.values())).any()


def test_spectral_high_frequency_ratio_uses_unfiltered_raw_waveform():
    sampling_rate = 250
    time = np.arange(10 * sampling_rate) / sampling_rate
    signal = np.sin(2 * np.pi * 60 * time)

    features = spectral_features(signal, sampling_rate)

    assert features["power_high_frequency_ratio"] > 0.99
    assert features["power_qrs_band_ratio"] < 0.001


def test_feature_duration_uses_supplied_sampling_rate():
    signal = np.zeros(1000)

    at_200_hz, _ = extract_features(signal, 200)
    at_250_hz, _ = extract_features(signal, 250)

    assert at_200_hz["duration_s"] == pytest.approx(5.0)
    assert at_250_hz["duration_s"] == pytest.approx(4.0)
