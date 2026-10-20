from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier

from afib.model import candidate_parameters, select_model


def test_candidate_parameters_match_declared_spec_order():
    candidates = candidate_parameters()

    assert len(candidates) == 16
    assert candidates[0] == {
        "max_leaf_nodes": 15,
        "min_samples_leaf": 40,
        "l2_regularization": 1.0,
        "class_weight": None,
    }
    assert candidates[1]["class_weight"] == "balanced"
    assert candidates[2]["l2_regularization"] == 0.0
    assert candidates[8]["max_leaf_nodes"] == 31
    assert candidates[-1] == {
        "max_leaf_nodes": 31,
        "min_samples_leaf": 20,
        "l2_regularization": 0.0,
        "class_weight": "balanced",
    }
    expected = [
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
    assert candidates == expected


def test_select_model_rejects_held_out_record_in_training(tmp_path):
    features = pd.DataFrame({"feature": [0.0, 1.0]}, index=["A00001", "A00002"])

    with pytest.raises(ValueError, match="Held-out record found in training"):
        select_model(features, ["N", "A"], ["A00002"], tmp_path)

    assert not (tmp_path / "tuning_plan.json").exists()


def test_hist_gradient_boosting_rejects_wrong_feature_count():
    rng = np.random.default_rng(0)
    values = rng.normal(size=(60, 3))
    labels = np.array(["N", "A"] * 30)
    estimator = HistGradientBoostingClassifier(max_iter=5, random_state=0)
    estimator.fit(values, labels)

    with pytest.raises(ValueError, match="expecting 3 features"):
        estimator.predict(rng.normal(size=(2, 5)))
    with pytest.raises(ValueError, match="expecting 3 features"):
        estimator.predict_proba(rng.normal(size=(2, 5)))


def test_probability_columns_map_through_classes_not_assumed_order():
    rng = np.random.default_rng(0)
    values = rng.normal(size=(60, 3))
    labels = np.array(["N", "A"] * 30)
    estimator = HistGradientBoostingClassifier(max_iter=5, random_state=0)
    estimator.fit(values, labels)
    probabilities = estimator.predict_proba(values[:4])

    assert list(estimator.classes_) == ["A", "N"]
    for row in probabilities:
        assert row[list(estimator.classes_).index("N")] == row[1]
        assert row[list(estimator.classes_).index("A")] == row[0]
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0)


def test_hist_gradient_boosting_accepts_native_missing_values():
    rng = np.random.default_rng(0)
    values = rng.normal(size=(60, 3))
    values[::4, 1] = np.nan
    labels = np.array(["N", "A", "O"] * 20)
    estimator = HistGradientBoostingClassifier(max_iter=5, random_state=0).fit(values, labels)

    predicted = estimator.predict(values[:6])
    probabilities = estimator.predict_proba(values[:6])

    assert len(predicted) == 6
    assert np.isfinite(probabilities).all()
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0)
