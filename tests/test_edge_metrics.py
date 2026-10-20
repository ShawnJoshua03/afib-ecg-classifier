import json

import numpy as np
import pytest

from afib.metrics import evaluate, official_f1


@pytest.mark.parametrize(
    ("truth", "prediction", "expected"),
    [
        (["N", "A", "O", "~"], ["N", "A", "O", "~"], 1),
        (["N", "A", "O", "~"], ["A", "O", "~", "N"], 0),
        (["~", "~"], ["~", "~"], 0),
        (["A", "A"], ["A", "A"], 1 / 3),
        # O absent from truth; its false positive still penalizes A's recall.
        (["N", "A", "~"], ["N", "O", "~"], 1 / 3),
        # A absent from predictions: N F1 = 2/3, A = 0, O = 1.
        (["N", "A", "O", "~"], ["N", "N", "O", "~"], 5 / 9),
        (["N", "A", "O", "~"], ["~", "~", "~", "~"], 0),
        (["~", "~", "~"], ["N", "A", "O"], 0),
        # Noisy -> N is a false positive; O -> noisy is a false negative.
        (["N", "A", "O", "O", "~"], ["N", "A", "O", "~", "N"], 7 / 9),
    ],
)
def test_official_f1_hand_calculated_edge_cases(truth, prediction, expected):
    assert official_f1(truth, prediction) == pytest.approx(expected)
    assert official_f1(np.array(truth), np.array(prediction)) == pytest.approx(expected)
    assert official_f1(truth[::-1], prediction[::-1]) == pytest.approx(expected)
    report = evaluate(truth, prediction)
    assert report["official_mean_f1"] == pytest.approx(expected)
    assert report["label_order"] == ["N", "A", "O", "~"]
    assert np.asarray(report["confusion_matrix"]).shape == (4, 4)
    assert report["n_test"] == len(truth)
    for label in ["N", "A", "O", "~"]:
        assert report["per_class"][label]["support"] == truth.count(label)
    json.dumps(report, allow_nan=False)


def test_evaluation_confusion_matrix_has_explicit_non_alphabetical_label_order():
    report = evaluate(["~", "O", "A", "N", "N"], ["N", "~", "O", "A", "A"])
    assert report["label_order"] == ["N", "A", "O", "~"]
    assert report["confusion_matrix"] == [
        [0, 2, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
        [1, 0, 0, 0],
    ]


@pytest.mark.parametrize(
    ("truth", "prediction"),
    [([], []), (["N"], []), ([], ["N"]), (["N", "A"], ["N"]),
     (["X"], ["N"]), (["N"], ["X"])],
)
@pytest.mark.parametrize("function", [official_f1, evaluate])
def test_invalid_label_inputs_rejected(function, truth, prediction):
    with pytest.raises(ValueError):
        function(truth, prediction)
