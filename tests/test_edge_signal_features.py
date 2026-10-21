import json
from pathlib import Path

import numpy as np
import pytest

from afib.features import extract_features, rr_features, sample_entropy, spectral_features
from afib.signal import bandpass, detect_r_peaks


def pulse_train(sampling_rate, times, duration=6):
    time = np.arange(round(duration * sampling_rate)) / sampling_rate
    signal = np.zeros(len(time))
    for peak_time in times:
        signal += np.exp(-0.5 * ((time - peak_time) / 0.025) ** 2)
    return signal


def assert_schema(features):
    path = Path(__file__).resolve().parents[1] / "artifacts" / "feature_schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert list(features) == schema["feature_names"]
    assert len(features) == schema["n_features"] == 34
    assert not np.isinf(list(features.values())).any()


@pytest.mark.parametrize("signal", [[np.nan], [np.inf], [-np.inf], [[1, 2]], 1.0])
@pytest.mark.parametrize("function", [detect_r_peaks, extract_features])
def test_invalid_signal_rejected_even_when_short(function, signal):
    with pytest.raises(ValueError, match="ECG"):
        function(signal, 300)


def test_empty_signal_contracts():
    peaks = detect_r_peaks([], 300)
    assert peaks.shape == (0,)
    assert np.issubdtype(peaks.dtype, np.integer)
    with pytest.raises(ValueError, match="nonempty"):
        extract_features([], 300)


@pytest.mark.parametrize("rate", [-1, 0, 40, np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("function", [detect_r_peaks, extract_features])
def test_invalid_sampling_rate_rejected(function, rate):
    with pytest.raises(ValueError, match="[Ss]ampling rate"):
        function(np.zeros(300), rate)


@pytest.mark.parametrize("rate", [40.5, 60, 80])
def test_feature_filter_has_stricter_nyquist_requirement(rate):
    assert detect_r_peaks(np.zeros(300), rate).size == 0
    with pytest.raises(ValueError, match=">80"):
        extract_features(np.zeros(300), rate)


@pytest.mark.parametrize("length", [0, 1, 2, 20, 21])
def test_bandpass_rejects_input_at_or_below_padding_length(length):
    with pytest.raises(ValueError, match="padlen"):
        bandpass(np.arange(length, dtype=float), 300, 5, 20)


def test_bandpass_accepts_first_length_above_padding():
    filtered = bandpass(np.arange(22, dtype=float), 300, 5, 20)
    assert filtered.shape == (22,)
    assert np.isfinite(filtered).all()


@pytest.mark.parametrize("length", [1, 2, 3, 20, 21, 22, 31, 32, 299])
def test_short_record_keeps_schema_and_missing_physiology(length):
    features, peaks = extract_features(np.linspace(-1, 1, length), 300)
    assert_schema(features)
    assert peaks.size == 0
    assert features["duration_s"] == pytest.approx(length / 300)
    assert all(np.isnan(value) for name, value in features.items() if name.startswith("rr_"))
    assert np.isnan(features["peak_amplitude_median_mv"])
    assert np.isnan(features["template_correlation_median"])


@pytest.mark.parametrize("level", [0, 1, -2])
def test_flat_record_has_no_peaks_or_spectral_power(level):
    signal = np.full(600, level, dtype=float)
    features, peaks = extract_features(signal, 300)
    assert_schema(features)
    assert peaks.size == 0
    assert features["signal_std_mv"] == 0
    assert features["flat_step_fraction"] == 1
    assert all(np.isnan(value) for value in spectral_features(signal, 300).values())


@pytest.mark.parametrize("rate", [81, 125, 257, 300.5])
@pytest.mark.parametrize("polarity", [1, -1])
def test_pulse_count_timing_and_schema_at_odd_rates(rate, polarity):
    times = np.array([0.7, 1.7, 2.7, 3.7, 4.7])
    features, peaks = extract_features(polarity * pulse_train(rate, times), rate)
    assert_schema(features)
    assert len(peaks) == features["n_detected_peaks"] == len(times)
    np.testing.assert_allclose(peaks / rate, times, atol=0.030, rtol=0)
    assert features["rr_mean_s"] == pytest.approx(1, abs=1 / rate)
    assert features["duration_s"] == pytest.approx(6)


def test_seeded_noise_is_deterministic_with_valid_refractory_spacing():
    signal = np.random.default_rng(2017).normal(size=3000)
    features, peaks = extract_features(signal, 300)
    assert_schema(features)
    np.testing.assert_array_equal(peaks, detect_r_peaks(signal, 300))
    # Noise can produce candidates; this detector does not promise noise rejection.
    assert peaks.size > 1
    assert np.issubdtype(peaks.dtype, np.integer)
    assert np.all((peaks >= 0) & (peaks < len(signal)))
    assert np.all(np.diff(peaks) >= 75)
    assert features["n_detected_peaks"] == len(peaks)


@pytest.mark.parametrize("count", [0, 1, 2])
def test_zero_one_two_peaks_preserve_missing_rr_features(count):
    times = [1.0, 2.0][:count]
    features, peaks = extract_features(pulse_train(300, times), 300)
    assert_schema(features)
    assert len(peaks) == count
    rr = rr_features(np.diff(peaks) / 300)
    for name, value in rr.items():
        assert features[name] == pytest.approx(value, nan_ok=True)
    if count < 2:
        assert all(np.isnan(value) for value in rr.values())
    else:
        assert rr["rr_mean_s"] == pytest.approx(1)
        assert rr["rr_iqr_s"] == 0
        assert rr["rr_implausible_fraction"] == 0
    for name in ("rr_std_s", "rr_cv", "rr_rmssd_s", "rr_pnn50",
                 "rr_turning_point_ratio", "rr_sample_entropy"):
        assert np.isnan(rr[name])
    assert np.isnan(features["template_correlation_median"])


@pytest.mark.parametrize("rr", [[0], [-1], [np.nan], [np.inf], [-np.inf], [[1, 2]]])
def test_invalid_rr_intervals_are_rejected(rr):
    with pytest.raises(ValueError, match="RR intervals"):
        rr_features(rr)


def test_two_intervals_enable_variability_but_not_turning_points():
    features = rr_features([1, 1.5])
    assert features["rr_mean_s"] == 1.25
    assert features["rr_std_s"] == pytest.approx(np.sqrt(0.125))
    assert features["rr_cv"] == pytest.approx(np.sqrt(0.125) / 1.25)
    assert features["rr_rmssd_s"] == 0.5
    assert features["rr_pnn50"] == 1
    assert np.isnan(features["rr_turning_point_ratio"])


@pytest.mark.parametrize("length", [0, 1, 2, 9, 10])
def test_entropy_minimum_count_for_constant_intervals(length):
    entropy = sample_entropy(np.ones(length))
    assert entropy == 0 if length >= 10 else np.isnan(entropy)


def test_fractional_rate_rejects_record_shorter_than_one_second():
    rate = 250.5
    signal = pulse_train(rate, [0.5], duration=250 / rate)
    assert len(signal) / rate < 1
    assert detect_r_peaks(signal, rate).size == 0


def test_nonzero_decimal_constant_has_missing_spectral_features():
    features = spectral_features(np.full(300, 0.1), 300)
    assert all(np.isnan(value) for value in features.values())
