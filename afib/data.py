"""Strict MATLAB/WFDB loading, dataset audit, and a frozen record-level split."""

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from scipy.io.matlab import MatReadError
from sklearn.model_selection import train_test_split

from afib.download import sha256
from afib.metrics import LABELS

SEED = 2017


@dataclass(frozen=True)
class Header:
    record_id: str
    sampling_rate: float
    n_samples: int
    gain: float
    baseline: float
    units: str
    n_header_lines: int


@dataclass(frozen=True)
class Recording:
    record_id: str
    signal: np.ndarray
    sampling_rate: float


def read_header(path):
    """Read the single-channel WFDB fields needed for physical-unit conversion."""
    lines = [line.strip() for line in Path(path).read_text().splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError(f"Incomplete WFDB header: {path}")
    first, second = lines[0].split(), lines[1].split()
    if len(first) < 4 or len(second) < 5 or int(first[1]) != 1:
        raise ValueError(f"Expected a single-channel WFDB header: {path}")
    match = re.fullmatch(r"([\d.eE+-]+)(?:\(([\d.eE+-]+)\))?/(\w+)", second[2])
    if not match:
        raise ValueError(f"Unsupported gain specification: {second[2]}")
    gain = float(match[1])
    baseline = float(match[2]) if match[2] is not None else float(second[4])
    rate = float(first[2])
    n_samples = int(first[3])
    if gain <= 0 or rate <= 0 or n_samples <= 0:
        raise ValueError("Gain, sampling rate and record length must be positive")
    if match[3] != "mV":
        raise ValueError(f"Expected mV units, found {match[3]}")
    if first[0] != Path(path).stem or Path(second[0]).stem != first[0]:
        raise ValueError("Header record ID does not match its filename")
    return Header(first[0], rate, n_samples, gain, baseline, match[3], len(lines))


def load_recording(mat_path):
    """Load one finite lead and verify its sample count against its .hea file."""
    mat_path = Path(mat_path)
    header = read_header(mat_path.with_suffix(".hea"))
    try:
        contents = loadmat(mat_path)
    except (MatReadError, ValueError, IndexError) as error:
        raise ValueError(f"Unreadable MAT file {mat_path}: {error}") from error
    if "val" not in contents:
        raise ValueError(f"MAT file has no 'val' array: {mat_path}")
    raw = np.asarray(contents["val"])
    if raw.shape != (1, header.n_samples):
        raise ValueError(f"MAT shape {raw.shape} does not match single-lead header: {mat_path}")
    signal = (raw[0].astype(np.float64) - header.baseline) / header.gain
    if not np.all(np.isfinite(signal)):
        raise ValueError(f"Non-finite ECG samples in {mat_path}")
    return Recording(header.record_id, signal, header.sampling_rate)


def read_reference(path):
    """Return a sorted record-label mapping; no patient IDs are inferred."""
    records = {}
    with Path(path).open(newline="") as stream:
        for row in csv.reader(stream):
            if len(row) != 2 or not re.fullmatch(r"A\d{5}", row[0]):
                raise ValueError(f"Malformed reference row: {row}")
            record_id, label = row
            if label not in LABELS or record_id in records:
                raise ValueError(f"Invalid label or duplicate record: {row}")
            records[record_id] = label
    if not records:
        raise ValueError("Empty reference file")
    return dict(sorted(records.items()))


def discover_records(raw_dir):
    paths = {}
    for path in sorted(Path(raw_dir).rglob("A*.mat")):
        if path.stem in paths:
            raise ValueError(f"Duplicate record ID on disk: {path.stem}")
        paths[path.stem] = path
    if not paths:
        raise FileNotFoundError("No ECG files found; run python -m afib.download first")
    return paths


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def audit_dataset(raw_dir, output_dir):
    """Check every MAT/header pair and preserve source identities for reproduction."""
    raw_dir, output_dir = Path(raw_dir), Path(output_dir)
    canonical = raw_dir / "REFERENCE.csv"
    final_reference = raw_dir / "REFERENCE-v3.csv"
    if not final_reference.exists():
        raise FileNotFoundError("Final v3 labels missing; run python -m afib.download")
    if canonical.exists() and canonical.read_bytes() != final_reference.read_bytes():
        raise ValueError("Canonical REFERENCE.csv does not match frozen final v3 labels")
    canonical.write_bytes(final_reference.read_bytes())
    labels = read_reference(canonical)
    paths = discover_records(raw_dir)
    if set(labels) != set(paths):
        raise ValueError("Label and ECG record ID sets differ")
    archive_refs = [p for p in raw_dir.rglob("REFERENCE.csv") if p != canonical]
    archived_labels = read_reference(archive_refs[0]) if len(archive_refs) == 1 else None
    changes = None
    if archived_labels is not None:
        if set(archived_labels) != set(labels):
            raise ValueError("Archive and final reference record sets differ")
        changes = sum(archived_labels[key] != value for key, value in labels.items())
    rows = []
    signal_hashes = {}
    fingerprint = hashlib.sha256()
    for i, (record_id, path) in enumerate(paths.items(), start=1):
        header = read_header(path.with_suffix(".hea"))
        header_lines = [
            line.split()
            for line in path.with_suffix(".hea").read_text().splitlines()
            if line.strip()
        ]
        if len(header_lines[0]) > 6 or len(header_lines[1]) != 9:
            raise ValueError("Unexpected header fields; inspect for patient metadata")
        optional = header_lines[0][4:]
        if optional and not re.fullmatch(r"\d{1,2}:\d{2}:\d{2}(?:\.\d+)?", optional[0]):
            raise ValueError("Unexpected header time field; inspect for patient metadata")
        if len(optional) == 2 and not re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", optional[1]):
            raise ValueError("Unexpected header date field; inspect for patient metadata")
        if header_lines[1][8] != "ECG":
            raise ValueError("Unexpected lead description; inspect header metadata")
        recording = load_recording(path)
        mat_hash, header_hash = sha256(path), sha256(path.with_suffix(".hea"))
        fingerprint.update(f"{record_id}:{mat_hash}:{header_hash}\n".encode())
        # Physical samples identify byte-identical waveforms even across differing MAT metadata.
        signal_hash = hashlib.sha256(recording.signal.astype("<f8").tobytes()).hexdigest()
        signal_hashes.setdefault(signal_hash, []).append(record_id)
        rows.append(
            {
                "record_id": record_id,
                "label": labels[record_id],
                "sampling_rate_hz": header.sampling_rate,
                "n_samples": header.n_samples,
                "duration_seconds": header.n_samples / header.sampling_rate,
                "header_lines": header.n_header_lines,
                "mat_sha256": mat_hash,
                "header_sha256": header_hash,
                "signal_sha256": signal_hash,
            }
        )
        if i % 2000 == 0:
            print(f"Validated {i}/{len(paths)} ECG/header pairs", flush=True)
    durations = [row["duration_seconds"] for row in rows]
    summary = {
        "n_records": len(rows),
        "class_counts": {key: sum(value == key for value in labels.values()) for key in LABELS},
        "sampling_rates_hz": sorted({row["sampling_rate_hz"] for row in rows}),
        "sample_count_min": min(row["n_samples"] for row in rows),
        "sample_count_max": max(row["n_samples"] for row in rows),
        "duration_seconds_min": min(durations),
        "duration_seconds_max": max(durations),
        "duration_seconds_median": float(np.median(durations)),
        "header_line_counts": dict(Counter(row["header_lines"] for row in rows)),
        "extra_header_line_records": sum(row["header_lines"] > 2 for row in rows),
        "patient_ids_available": False,
        "patient_id_evidence": (
            "No documented patient identifiers in inspected reference/header fields. "
            "REFERENCE.csv contains record ID and rhythm label only. Single-lead WFDB headers "
            "contain record ID, signal metadata, date/time and lead description, no patient ID. "
            "Record IDs and date/time fields are not documented patient identifiers."
        ),
        "final_reference_sha256": sha256(canonical),
        "archive_reference_label_changes": changes,
        "archive_reference_class_counts": dict(Counter(archived_labels.values()))
        if archived_labels is not None
        else None,
        "records_sha256": fingerprint.hexdigest(),
        "duplicate_signal_groups": [ids for ids in signal_hashes.values() if len(ids) > 1],
    }
    if summary["extra_header_line_records"]:
        raise ValueError("Extra header metadata found; inspect for patient IDs before splitting")
    write_json(output_dir / "dataset_audit.json", summary)
    write_json(output_dir / "record_manifest.json", rows)
    return paths, labels, summary


def frozen_split(labels, output_path):
    """Create once, then enforce the same stratified 80/20 record IDs on every run."""
    record_ids = sorted(labels)
    train, test = train_test_split(
        record_ids,
        test_size=0.2,
        random_state=SEED,
        stratify=[labels[record_id] for record_id in record_ids],
    )
    result = {
        "seed": SEED,
        "test_fraction": 0.2,
        "grouping": "record (patient IDs unavailable)",
        "train_ids": sorted(train),
        "test_ids": sorted(test),
        "train_class_counts": dict(Counter(labels[key] for key in train)),
        "test_class_counts": dict(Counter(labels[key] for key in test)),
    }
    output_path = Path(output_path)
    if output_path.exists() and json.loads(output_path.read_text()) != result:
        raise ValueError("Existing split differs; refusing to change the held-out test set")
    write_json(output_path, result)
    return result
