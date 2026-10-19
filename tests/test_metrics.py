import pytest

from afib.metrics import official_f1


def test_official_metric_hand_calculation_includes_noisy_errors():
    # N: TP=1, FP=1, FN=1 -> 1/2; A: TP=1, FP=1, FN=0 -> 2/3.
    # O: TP=1, FP=0, FN=1 -> 2/3. Noisy -> N must count as an N FP.
    truth = ["N", "N", "A", "O", "O", "~", "~"]
    pred = ["N", "A", "A", "O", "~", "N", "~"]
    assert official_f1(truth, pred) == pytest.approx((1 / 2 + 2 / 3 + 2 / 3) / 3)


def test_absent_scored_class_contributes_zero():
    assert official_f1(["N", "~"], ["N", "~"]) == pytest.approx(1 / 3)


def test_unknown_label_rejected():
    with pytest.raises(ValueError):
        official_f1(["N"], ["X"])
