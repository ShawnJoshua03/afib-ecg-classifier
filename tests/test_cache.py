import hashlib

import numpy as np
import pandas as pd
import pytest
from scipy.io import savemat

from afib.train import feature_matrix


def write_record(tmp_path, record_id, samples, rate=257):
    samples = np.asarray(samples).reshape(1, -1)
    (tmp_path / f"{record_id}.hea").write_text(
        f"{record_id} 1 {rate} {samples.shape[1]}\n"
        f"{record_id}.mat 16x 200(100)/mV 16 0 -50 0 0\n",
        encoding="ascii",
    )
    savemat(tmp_path / f"{record_id}.mat", {"val": samples}, format="4")
    return tmp_path / f"{record_id}.mat"


def synthetic_records(tmp_path):
    rate = 257
    time = np.arange(10 * rate) / rate
    paths = {}
    for record_id, frequency in [("A00001", 1.2), ("A00002", 1.6)]:
        counts = np.round(100 + 100 * np.sin(2 * np.pi * frequency * time))
        paths[record_id] = write_record(tmp_path, record_id, counts, rate=rate)
    return paths


def test_feature_matrix_saves_cache_and_reloads_after_records_disappear(tmp_path):
    paths = synthetic_records(tmp_path)
    audit = {"records_sha256": hashlib.sha256(b"synthetic records").hexdigest()}
    cache_dir = tmp_path / "processed"

    first, identity = feature_matrix(paths, audit, cache_dir)
    assert len(list(cache_dir.glob("features-*.npz"))) == 1

    for path in paths.values():
        path.unlink()
        path.with_suffix(".hea").unlink()

    reloaded, reloaded_identity = feature_matrix(paths, audit, cache_dir)

    assert reloaded_identity == identity
    pd.testing.assert_frame_equal(reloaded, first)
    assert first["duration_s"].tolist() == [10.0, 10.0]


def test_feature_matrix_rejects_cache_saved_for_different_record_order(tmp_path):
    paths = synthetic_records(tmp_path)
    audit = {"records_sha256": hashlib.sha256(b"synthetic records").hexdigest()}
    cache_dir = tmp_path / "processed"
    feature_matrix(paths, audit, cache_dir)
    cache_path = next(cache_dir.glob("features-*.npz"))
    with np.load(cache_path, allow_pickle=False) as saved:
        reordered = {name: saved[name] for name in saved.files}
    reordered["record_ids"] = reordered["record_ids"][::-1]
    np.savez_compressed(cache_path, **reordered)

    with pytest.raises(ValueError, match="record order mismatch"):
        feature_matrix(paths, audit, cache_dir)
