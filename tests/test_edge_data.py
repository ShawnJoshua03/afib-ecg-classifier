from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.io import savemat

from afib.data import (
    audit_dataset,
    discover_records,
    frozen_split,
    load_recording,
    read_header,
)
from afib.demo_data import main as build_demo
from afib.download import sha256

QUOTA = {"N": (5, 2), "A": (5, 2), "O": (4, 4), "~": (3, 3)}


def write_record(directory, record_id, samples, *, rate=250, extra_lines=()):
    samples = np.asarray(samples, dtype=np.int64).reshape(1, -1)
    header = (
        f"{record_id} 1 {rate} {samples.shape[1]}\n"
        f"{record_id}.mat 16 200(100)/mV 16 0 -50 0 0 ECG\n"
    )
    header += "".join(f"{line}\n" for line in extra_lines)
    (Path(directory) / f"{record_id}.hea").write_text(header, encoding="ascii")
    savemat(Path(directory) / f"{record_id}.mat", {"val": samples}, format="4")


def test_missing_header_or_mat_file_raises_oserror(tmp_path):
    savemat(tmp_path / "A00001.mat", {"val": np.array([[1, 2]])}, format="4")
    with pytest.raises(FileNotFoundError):
        load_recording(tmp_path / "A00001.mat")

    (tmp_path / "A00002.hea").write_text(
        "A00002 1 250 2\nA00002.mat 16 200(100)/mV 16 0 -50 0 0 ECG\n", encoding="ascii"
    )
    with pytest.raises(OSError):
        load_recording(tmp_path / "A00002.mat")

    (tmp_path / "A00003.hea").write_text("A00003 1 250 1\n", encoding="ascii")
    with pytest.raises(ValueError, match="Incomplete"):
        read_header(tmp_path / "A00003.hea")


@pytest.mark.xfail(strict=True, reason="corrupt .mat raises scipy MatReadError, not ValueError")
def test_corrupt_mat_file_raises_value_error(tmp_path):
    (tmp_path / "A00001.hea").write_text(
        "A00001 1 250 1\nA00001.mat 16 200(100)/mV 16 0 -50 0 0 ECG\n", encoding="ascii"
    )
    (tmp_path / "A00001.mat").write_bytes(b"")

    with pytest.raises(ValueError):
        load_recording(tmp_path / "A00001.mat")


def test_discover_records_reports_empty_and_duplicate_ids(tmp_path):
    with pytest.raises(FileNotFoundError, match="No ECG files"):
        discover_records(tmp_path)

    for subdirectory in ("one", "two"):
        (tmp_path / subdirectory).mkdir()
        (tmp_path / subdirectory / "A00001.mat").write_bytes(b"x")
    with pytest.raises(ValueError, match="Duplicate record ID"):
        discover_records(tmp_path)


def test_frozen_split_sizes_disjoint_and_order_independent(tmp_path):
    labels = {
        f"A{index:05d}": label
        for label in ("N", "A", "O", "~")
        for index in range(1 + 10 * ("NAO~".index(label)), 11 + 10 * ("NAO~".index(label)))
    }
    reversed_labels = {key: labels[key] for key in reversed(list(labels))}

    first = frozen_split(labels, tmp_path / "first.json")
    second = frozen_split(reversed_labels, tmp_path / "second.json")

    assert first == second
    assert (len(first["train_ids"]), len(first["test_ids"])) == (32, 8)
    assert set(first["train_ids"]).isdisjoint(first["test_ids"])
    assert first["test_class_counts"] == {"N": 2, "A": 2, "O": 2, "~": 2}


def test_sha256_matches_known_digest_and_missing_file(tmp_path):
    path = tmp_path / "abc.bin"
    path.write_bytes(b"abc")

    assert sha256(path) == hashlib.sha256(b"abc").hexdigest()
    with pytest.raises(FileNotFoundError):
        sha256(tmp_path / "absent.bin")


def build_audit_dataset(root):
    records = root / "training2017"
    records.mkdir(parents=True)
    labels = {"A00001": "N", "A00002": "A", "A00003": "O", "A00004": "~"}
    for index, record_id in enumerate(labels):
        write_record(records, record_id, [100 + index, 200, 300, 400])
    write_record(records, "A00003", [150, 260, 370, 480])
    write_record(records, "A00004", [150, 260, 370, 480])
    (root / "REFERENCE-v3.csv").write_text(
        "".join(f"{key},{value}\n" for key, value in labels.items()), encoding="ascii"
    )
    archived = dict(labels, A00002="O")
    (records / "REFERENCE.csv").write_text(
        "".join(f"{key},{value}\n" for key, value in archived.items()), encoding="ascii"
    )
    return root, labels


def test_audit_dataset_manifest_duplicates_and_label_changes(tmp_path):
    raw_dir, labels = build_audit_dataset(tmp_path / "raw")
    output_dir = tmp_path / "artifacts"

    _, audited, summary = audit_dataset(raw_dir, output_dir)
    _, _, repeated = audit_dataset(raw_dir, output_dir)

    assert audited == labels
    assert summary["n_records"] == 4
    assert summary["class_counts"] == {"N": 1, "A": 1, "O": 1, "~": 1}
    assert summary["duplicate_signal_groups"] == [["A00003", "A00004"]]
    assert summary["archive_reference_label_changes"] == 1
    assert summary["patient_ids_available"] is False
    assert summary["records_sha256"] == repeated["records_sha256"]
    assert (raw_dir / "REFERENCE.csv").read_bytes() == (
        raw_dir / "REFERENCE-v3.csv"
    ).read_bytes()
    manifest = json.loads((output_dir / "record_manifest.json").read_text(encoding="utf-8"))
    assert [row["record_id"] for row in manifest] == sorted(labels)


def test_audit_dataset_rejects_label_and_disk_mismatch(tmp_path):
    raw_dir, _ = build_audit_dataset(tmp_path / "raw")
    (raw_dir / "training2017" / "A00004.mat").unlink()

    with pytest.raises(ValueError, match="record ID sets differ"):
        audit_dataset(raw_dir, tmp_path / "artifacts")


def write_demo_inputs(work):
    raw_dir = work / "raw"
    raw_dir.mkdir()
    (work / "artifacts").mkdir()
    rows = []
    index = 0
    for label, (n_ok, n_bad) in QUOTA.items():
        for ok, count in ((True, n_ok), (False, n_bad)):
            for _ in range(count):
                index += 1
                record_id = f"A{index:05d}"
                write_record(raw_dir, record_id, [100 + index] + [120, 140] * 1550)
                wrong = next(key for key in QUOTA if key != label)
                rows.append(
                    {
                        "record_id": record_id,
                        "true_label": label,
                        "model_prediction": label if ok else wrong,
                        "probability_N": 0.4,
                        "probability_A": 0.3,
                        "probability_O": 0.2,
                        "probability_~": 0.1,
                    }
                )
    pd.DataFrame(rows).to_csv(work / "artifacts" / "test_predictions.csv", index=False)
    return raw_dir, len(rows)


def test_demo_data_output_shape_truncation_and_probabilities(tmp_path, monkeypatch):
    raw_dir, expected = write_demo_inputs(tmp_path)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "public" / "demo_data.json"
    out.parent.mkdir()

    build_demo(raw_dir=raw_dir, out=out)
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["seconds_shown"] == 12
    assert len(payload["records"]) == expected
    assert len({record["id"] for record in payload["records"]}) == expected
    for record in payload["records"]:
        probabilities = list(record["probs"].values())
        assert np.isfinite(probabilities).all()
        assert sum(probabilities) == pytest.approx(1.0, abs=1e-3)
        assert record["correct"] == (record["true"] == record["pred"])
        assert len(record["signal"]) == 12 * record["fs"]
        assert all(0 <= peak < len(record["signal"]) for peak in record["peaks"])


@pytest.mark.xfail(strict=True, reason="demo_data.main does not create its output directory")
def test_demo_data_creates_missing_output_directory(tmp_path, monkeypatch):
    raw_dir, _ = write_demo_inputs(tmp_path)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "missing" / "public" / "demo_data.json"

    build_demo(raw_dir=raw_dir, out=out)

    assert out.exists()
