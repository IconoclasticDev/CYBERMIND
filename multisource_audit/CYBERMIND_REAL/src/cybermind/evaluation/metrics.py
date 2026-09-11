from __future__ import annotations
from typing import Dict, Iterable, Sequence
import numpy as np
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, confusion_matrix

def binary_metrics(y_true,y_score,threshold=.5)->Dict[str,float|None]:
    y=np.asarray(y_true).astype(int); s=np.asarray(y_score); p=(s>=threshold).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,p,labels=[0,1]).ravel()
    fpr=fp/max(fp+tn,1)
    return {'f1':float(f1_score(y,p,zero_division=0)),'precision':float(precision_score(y,p,zero_division=0)),
            'recall':float(recall_score(y,p,zero_division=0)),'fpr':float(fpr),
            'ap':float(average_precision_score(y,s)) if len(np.unique(y))>1 else None}

def early_warning_lead_time(timestamps, y_true, risk_scores, threshold=.5, reliability_window=1):
    ts=np.asarray(timestamps,dtype=float); y=np.asarray(y_true).astype(int); s=np.asarray(risk_scores,dtype=float)
    critical=np.where(y>=1)[0]
    if critical.size==0: return {'lead_time_seconds':None,'warning_index':None,'critical_index':None}
    ci=int(critical[0]); warnings=np.where(s[:ci+1]>=threshold)[0]
    if warnings.size==0: return {'lead_time_seconds':0.0,'warning_index':None,'critical_index':ci}
    wi=int(warnings[0])
    return {'lead_time_seconds':float(max(0.,ts[ci]-ts[wi])),'warning_index':wi,'critical_index':ci}
