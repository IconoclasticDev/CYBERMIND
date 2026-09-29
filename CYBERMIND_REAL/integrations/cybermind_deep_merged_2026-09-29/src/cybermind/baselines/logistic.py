from __future__ import annotations
import joblib, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from cybermind.evaluation.metrics import binary_metrics

class LogisticBaseline:
    def __init__(self): self.model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000,class_weight='balanced'))
    def fit(self,X,y): self.model.fit(X,y); return self
    def predict_proba(self,X): return self.model.predict_proba(X)[:,1]
    def metrics(self,X,y,threshold=.5):
        p=self.predict_proba(X)
        result=binary_metrics(y,p,threshold)
        if not np.any(np.asarray(y)==0): result['fpr']=None
        result['roc_auc']=float(roc_auc_score(y,p)) if len(np.unique(y))>1 else None
        return result
    def save(self,path): joblib.dump(self.model,path)
    def load(self,path): self.model=joblib.load(path); return self
