from __future__ import annotations
from typing import List
import numpy as np
from .metrics import binary_metrics,early_warning_lead_time

def evaluate_sequence(ts, true_infil, pred_risk, threshold=.5):
    m=binary_metrics(true_infil,pred_risk,threshold)
    m.update(early_warning_lead_time(ts,true_infil,pred_risk,threshold))
    return m
