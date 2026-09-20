import numpy as np

from scripts.r5_posthoc_analysis import select_threshold


def test_threshold_selection_maximizes_validation_f1_without_test_data():
    result = select_threshold([0, 0, 1, 1], [0.1, 0.4, 0.6, 0.9])
    assert result["threshold"] == 0.6
    assert result["validation_confusion_counts"] == {"tn": 2, "fp": 0, "fn": 0, "tp": 2}


def test_threshold_tie_break_prefers_lower_fpr_then_higher_threshold():
    result = select_threshold([0, 0, 1], [0.1, 0.3, 0.3])
    assert np.isclose(result["threshold"], 0.3)
    assert result["validation_confusion_counts"]["fp"] == 1
