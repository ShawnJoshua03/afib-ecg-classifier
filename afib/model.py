"""Training-only model selection followed by the fixed held-out evaluation."""

import itertools
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold

from afib.data import SEED, write_json
from afib.download import sha256
from afib.metrics import LABELS, evaluate, official_f1

FIXED_PARAMETERS = {
    "learning_rate": 0.08,
    "max_iter": 200,
    "early_stopping": False,
    "random_state": SEED,
    "max_bins": 255,
}


def candidate_parameters():
    """Explicit SPEC order; np.argmax later makes exact ties choose the first."""
    return [
        {
            "max_leaf_nodes": leaves,
            "min_samples_leaf": minimum,
            "l2_regularization": l2,
            "class_weight": weight,
        }
        for leaves, minimum, l2, weight in itertools.product(
            [15, 31], [40, 20], [1.0, 0.0], [None, "balanced"]
        )
    ]


def select_model(train_x, train_y, test_ids, output_dir):
    """No test features or labels are passed to this function."""
    if set(train_x.index).intersection(test_ids):
        raise ValueError("Held-out record found in training")
    plan = {
        "estimator": "HistGradientBoostingClassifier",
        "fixed_parameters": FIXED_PARAMETERS,
        "candidates": candidate_parameters(),
        "cv_folds": 5,
        "cv_seed": SEED,
        "selection_metric": "mean of five fold-specific official F1(N,A,O) scores",
        "tie_break": "first candidate in declared order",
    }
    write_json(output_dir / "tuning_plan.json", plan)
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    folds = list(splitter.split(train_x, train_y))
    fold_ids = []
    for fold_train, fold_validation in folds:
        fitting_ids = train_x.index[fold_train].tolist()
        validation_ids = train_x.index[fold_validation].tolist()
        if set(fitting_ids).intersection(validation_ids):
            raise ValueError("Cross-validation fold overlap")
        fold_ids.append({"train_ids": fitting_ids, "validation_ids": validation_ids})
    write_json(output_dir / "cv_folds.json", fold_ids)
    candidates = []
    train_values, train_labels = train_x.to_numpy(), np.asarray(train_y)
    for index, parameters in enumerate(plan["candidates"], start=1):
        scores = []
        for fitting, validation in folds:
            estimator = HistGradientBoostingClassifier(**FIXED_PARAMETERS, **parameters)
            estimator.fit(train_values[fitting], train_labels[fitting])
            predicted = estimator.predict(train_values[validation])
            scores.append(official_f1(train_labels[validation], predicted))
        candidate = {
            "parameters": parameters,
            "fold_scores": scores,
            "mean_f1": float(np.mean(scores)),
            "std_f1": float(np.std(scores, ddof=0)),
        }
        candidates.append(candidate)
        print(
            f"CV candidate {index}/{len(plan['candidates'])}: "
            f"mean official F1={candidate['mean_f1']:.6f}",
            flush=True,
        )
    best_index = int(np.argmax([item["mean_f1"] for item in candidates]))
    selected = candidates[best_index]
    results = {
        "candidates": candidates,
        "best_candidate_index": best_index,
        "best_mean_f1": selected["mean_f1"],
        "best_std_f1": selected["std_f1"],
    }
    write_json(output_dir / "cv_results.json", results)
    # Freeze selection and all relevant source identities BEFORE touching test predictions.
    source = Path(__file__).parent
    selection = {
        "parameters": FIXED_PARAMETERS | selected["parameters"],
        "cv_mean_f1": selected["mean_f1"],
        "cv_std_f1": selected["std_f1"],
        "feature_names": list(train_x.columns),
        "n_training_records": len(train_x),
        "source_sha256": {path.name: sha256(path) for path in sorted(source.glob("*.py"))},
        "split_sha256": sha256(output_dir / "split.json"),
        "feature_schema_sha256": sha256(output_dir / "feature_schema.json"),
        "tuning_plan_sha256": sha256(output_dir / "tuning_plan.json"),
        "cv_results_sha256": sha256(output_dir / "cv_results.json"),
        "prediction_rule": "estimator argmax, no threshold tuning or calibration",
    }
    write_json(output_dir / "selected_model.json", selection)
    estimator = HistGradientBoostingClassifier(**selection["parameters"])
    estimator.fit(train_values, train_labels)
    bundle = {
        "model": estimator,
        "feature_names": list(train_x.columns),
        "label_order": list(LABELS),
        "selection": selection,
    }
    joblib.dump(bundle, output_dir / "model.joblib", compress=3)
    return estimator, selection, results


def train_model(features, labels, split, baselines, predictions, paths, audit, output_dir):
    output_dir = Path(output_dir)
    train_ids, test_ids = split["train_ids"], split["test_ids"]
    train_y = [labels[key] for key in train_ids]
    estimator, selection, cv = select_model(features.loc[train_ids], train_y, test_ids, output_dir)
    test_values = features.loc[test_ids].to_numpy()
    test_y = [labels[key] for key in test_ids]
    predicted = estimator.predict(test_values)
    probabilities = estimator.predict_proba(test_values)
    model_evaluation = evaluate(test_y, predicted)
    results = {
        "dataset": "PhysioNet/CinC Challenge 2017 public training data, final v3 labels",
        "evaluation": "fixed record-level held-out subset; not the private challenge test set",
        "metric": "mean F1 for N,A,O; all four classes retained in error counts",
        "seed": SEED,
        "n_train": len(train_ids),
        "n_test": len(test_ids),
        "n_features": len(features.columns),
        "label_order": list(LABELS),
        "majority": baselines["majority"],
        "rr_logistic": baselines["rr_logistic"],
        "hist_gradient_boosting": model_evaluation,
        "selection": {
            "cv_mean_f1": cv["best_mean_f1"],
            "cv_std_f1": cv["best_std_f1"],
            "parameters": selection["parameters"],
            "cv_candidates": len(cv["candidates"]),
            "cv_folds": 5,
        },
    }
    results_path = output_dir / "results.json"
    if results_path.exists() and json.loads(results_path.read_text()) != results:
        raise ValueError("Held-out results changed; review rather than overwrite frozen results")
    write_json(results_path, results)
    predictions = predictions.copy()
    predictions["model_prediction"] = predicted
    for label in LABELS:
        column = list(estimator.classes_).index(label)
        predictions[f"probability_{label}"] = probabilities[:, column]
    predictions.to_csv(output_dir / "test_predictions.csv", index=False, float_format="%.17g")
    print(
        f"Selected model test official F1: {model_evaluation['official_mean_f1']:.6f}", flush=True
    )
    # Reporting and static demo generation are added in Phase 3; the model is frozen above.
    return results
