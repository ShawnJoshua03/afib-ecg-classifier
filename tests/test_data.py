from __future__ import annotations

import csv
import json

import numpy as np
import pytest
from scipy.io import savemat

from afib.data import frozen_split, load_recording, read_reference


def write_record(tmp_path, samples, *, record_id="A00001", rate=257, declared_samples=None):
    samples = np.asarray(samples)
    n_samples = samples.shape[-1]
    declared_samples = n_samples if declared_samples is None else declared_samples
    (tmp_path / f"{record_id}.hea").write_text(
        f"{record_id} 1 {rate} {declared_samples}\n"
        f"{record_id}.mat 16x 200(100)/mV 16 0 -50 0 0\n",
        encoding="ascii",
    )
    savemat(tmp_path / f"{record_id}.mat", {"val": samples}, format="4")
    return tmp_path / f"{record_id}.mat"


def test_load_recording_converts_adc_counts_to_mv_and_reads_header_rate(tmp_path):
    path = write_record(tmp_path, [[100, 300, 0]], rate=257)

    recording = load_recording(path)

    assert recording.record_id == "A00001"
    assert recording.sampling_rate == 257
    np.testing.assert_allclose(recording.signal, [0.0, 1.0, -0.5])


@pytest.mark.parametrize("samples", [[[1, 2]], [[1, 2], [3, 4]]])
def test_load_recording_rejects_sample_count_mismatch_and_multiple_leads(tmp_path, samples):
    path = write_record(tmp_path, samples, declared_samples=3)

    with pytest.raises(ValueError, match="shape"):
        load_recording(path)


def test_load_recording_rejects_multi_lead_header(tmp_path):
    (tmp_path / "A00001.hea").write_text(
        "A00001 2 257 2\nA00001.mat 16x 200(100)/mV 16 0 -50 0 0\n",
        encoding="ascii",
    )
    savemat(tmp_path / "A00001.mat", {"val": np.array([[1, 2], [3, 4]])}, format="4")

    with pytest.raises(ValueError, match="single-channel"):
        load_recording(tmp_path / "A00001.mat")


def test_load_recording_rejects_missing_val_and_nonfinite_samples(tmp_path):
    missing = write_record(tmp_path, [[1, 2]])
    savemat(missing, {"other": np.array([[1, 2]])}, format="4")
    with pytest.raises(ValueError, match="no 'val'"):
        load_recording(missing)

    nonfinite = write_record(tmp_path, [[1, np.nan]])
    with pytest.raises(ValueError, match="Non-finite"):
        load_recording(nonfinite)


def test_read_reference_rejects_malformed_row(tmp_path):
    path = tmp_path / "REFERENCE.csv"
    path.write_text("A00001,N,extra\n", encoding="ascii")

    with pytest.raises(ValueError, match="Malformed"):
        read_reference(path)


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([('A00001', 'N'), ('A00001', 'A')], "duplicate"),
        ([('A00001', 'X')], "Invalid label"),
    ],
)
def test_read_reference_rejects_duplicate_ids_and_unknown_labels(tmp_path, rows, message):
    path = tmp_path / "REFERENCE.csv"
    with path.open("w", newline="", encoding="ascii") as stream:
        csv.writer(stream).writerows(rows)

    with pytest.raises(ValueError, match=message):
        read_reference(path)


def test_frozen_split_is_deterministic_and_rejects_mutated_saved_split(tmp_path):
    labels = {
        f"A{index:05d}": label
        for label in ("N", "A", "O", "~")
        for index in range(1 + 10 * ("NAO~".index(label)), 11 + 10 * ("NAO~".index(label)))
    }
    path = tmp_path / "split.json"

    first = frozen_split(labels, path)
    second = frozen_split(labels, path)

    assert first == second
    assert set(first["train_ids"]).isdisjoint(first["test_ids"])
    assert set(first["train_ids"]) | set(first["test_ids"]) == set(labels)
    assert first["test_class_counts"] == {"N": 2, "A": 2, "O": 2, "~": 2}

    mutated = json.loads(path.read_text(encoding="utf-8"))
    mutated["test_ids"][0], mutated["train_ids"][0] = (
        mutated["train_ids"][0], mutated["test_ids"][0]
    )
    path.write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to change"):
        frozen_split(labels, path)
