"""Reproduce the audit, frozen split, baselines, model selection and held-out results."""

import argparse
import hashlib
import json
import platform
import warnings
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from afib.data import SEED, audit_dataset, frozen_split, load_recording, write_json
from afib.download import download, sha256
from afib.features import RR_BASELINE_FEATURES, extract_features
from afib.metrics import evaluate
from afib.signal import DETECTOR_CONFIG


def code_fingerprint():
    root = Path(__file__).parent
    return {name: sha256(root / name) for name in ["data.py", "signal.py", "features.py"]}


def feature_matrix(paths, audit, cache_dir):
    """Cache label-free extraction only, keyed by complete source and feature code hashes."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    identity = {"records_sha256": audit["records_sha256"], "code": code_fingerprint()}
    cache_key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    cache_path = cache_dir / f"features-{cache_key}.npz"
    ids = sorted(paths)
    if cache_path.exists():
        with np.load(cache_path, allow_pickle=False) as saved:
            if saved["record_ids"].tolist() != ids:
                raise ValueError("Feature cache record order mismatch")
            frame = pd.DataFrame(saved["values"], index=ids, columns=saved["names"].tolist())
        print(f"Loaded verified feature cache: {len(frame)} records", flush=True)
    else:
        rows = []
        for index, record_id in enumerate(ids, start=1):
            recording = load_recording(paths[record_id])
            features, _ = extract_features(recording.signal, recording.sampling_rate)
            rows.append(features)
            if index % 1000 == 0:
                print(f"Extracted {index}/{len(ids)} records", flush=True)
        frame = pd.DataFrame(rows, index=ids, dtype=float)
        np.savez_compressed(
            cache_path,
            record_ids=np.asarray(ids),
            values=frame.to_numpy(),
            names=np.asarray(frame.columns),
        )
    if np.isinf(frame.to_numpy()).any():
        raise ValueError("Infinite feature value")
    return frame, identity


def fit_baselines(features, labels, split, output_dir):
    train_ids, test_ids = split["train_ids"], split["test_ids"]
    train_y, test_y = [labels[key] for key in train_ids], [labels[key] for key in test_ids]
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(np.zeros((len(train_ids), 1)), train_y)
    majority_pred = dummy.predict(np.zeros((len(test_ids), 1)))
    rr_model = make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(C=1.0, solver="lbfgs", max_iter=5000, random_state=SEED),
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rr_model.fit(features.loc[train_ids, RR_BASELINE_FEATURES], train_y)
    rr_pred = rr_model.predict(features.loc[test_ids, RR_BASELINE_FEATURES])
    scores = {
        "majority": evaluate(test_y, majority_pred),
        "rr_logistic": evaluate(test_y, rr_pred),
        "rr_fit_warnings": [
            {"category": item.category.__name__, "message": str(item.message)} for item in caught
        ],
        "rr_features": RR_BASELINE_FEATURES,
        "rr_model_parameters": {"C": 1.0, "solver": "lbfgs", "max_iter": 5000},
        "majority_class": str(dummy.classes_[int(np.argmax(dummy.class_prior_))]),
    }
    existing = Path(output_dir) / "baselines.json"
    if existing.exists() and json.loads(existing.read_text()) != scores:
        raise ValueError("Baseline results changed; review before replacing frozen evaluation")
    write_json(existing, scores)
    predictions = pd.DataFrame(
        {
            "record_id": test_ids,
            "true_label": test_y,
            "majority_prediction": majority_pred,
            "rr_prediction": rr_pred,
        }
    )
    predictions.to_csv(Path(output_dir) / "baseline_predictions.csv", index=False)
    joblib.dump(rr_model, Path(output_dir) / "rr_baseline.joblib", compress=3)
    print(f"Majority test official F1: {scores['majority']['official_mean_f1']:.6f}", flush=True)
    print(
        f"RR baseline test official F1: {scores['rr_logistic']['official_mean_f1']:.6f}", flush=True
    )
    if caught:
        print(f"Baseline fit warnings: {scores['rr_fit_warnings']}", flush=True)
    return scores, predictions


def prepare(raw_dir, output_dir):
    provenance = download(raw_dir)
    write_json(output_dir / "data_provenance.json", provenance)
    paths, labels, audit = audit_dataset(raw_dir, output_dir)
    split = frozen_split(labels, output_dir / "split.json")
    train_set, test_set = set(split["train_ids"]), set(split["test_ids"])
    # Exact duplicate signals must not straddle the split. Pre-fit, label-blind of results:
    # the test-side copy is excluded from the held-out set and disclosed.
    excluded = sorted(
        record_id
        for group in audit["duplicate_signal_groups"]
        if train_set.intersection(group)
        for record_id in group
        if record_id in test_set
    )
    if excluded:
        split = {
            **split,
            "test_ids": [key for key in split["test_ids"] if key not in excluded],
            "excluded_duplicate_test_ids": excluded,
        }
        write_json(output_dir / "split_final.json", split)
    features, identity = feature_matrix(paths, audit, Path(raw_dir).parent / "processed")
    write_json(
        output_dir / "feature_schema.json",
        {
            "feature_names": list(features.columns),
            "n_features": len(features.columns),
            "source_identity": identity,
            "detector": DETECTOR_CONFIG,
            "missing_value": "NaN: native HGB handling; train-fit median imputation for baseline",
            "definitions": "FEATURES.md and afib/features.py",
        },
    )
    write_json(
        output_dir / "training_feature_missingness.json",
        {key: int(value) for key, value in features.loc[split["train_ids"]].isna().sum().items()},
    )
    write_json(
        output_dir / "environment.json",
        {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": {
                name: version(name)
                for name in [
                    "numpy",
                    "scipy",
                    "scikit-learn",
                    "pandas",
                    "matplotlib",
                    "joblib",
                    "threadpoolctl",
                    "pytest",
                    "ruff",
                ]
            },
            "numerical_thread_limit": 1,
        },
    )
    return paths, labels, audit, split, features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--stage", choices=["baseline", "full"], default="full")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with threadpool_limits(limits=1):
        paths, labels, audit, split, features = prepare(args.raw_dir, args.output_dir)
        baselines, predictions = fit_baselines(features, labels, split, args.output_dir)
        if args.stage == "baseline":
            return
        # Main-model selection is implemented in Phase 2, without changing the split.
        from afib.model import train_model

        train_model(features, labels, split, baselines, predictions, paths, audit, args.output_dir)


if __name__ == "__main__":
    main()
