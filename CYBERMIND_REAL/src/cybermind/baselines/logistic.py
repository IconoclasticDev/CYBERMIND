from __future__ import annotations
import joblib, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

class LogisticBaseline:
    def __init__(self): self.model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000,class_weight='balanced'))
    def fit(self,X,y): self.model.fit(X,y); return self
    def predict_proba(self,X): return self.model.predict_proba(X)[:,1]
    def metrics(self,X,y,threshold=.5):
        p=self.predict_proba(X); pred=(p>=threshold).astype(int)
        return {'f1':float(f1_score(y,pred,zero_division=0)),'precision':float(precision_score(y,pred,zero_division=0)),
                'recall':float(recall_score(y,pred,zero_division=0)),'ap':float(average_precision_score(y,p)),
                'roc_auc':float(roc_auc_score(y,p)) if len(np.unique(y))>1 else None}
    def save(self,path): joblib.dump(self.model,path)
    def load(self,path): self.model=joblib.load(path); return self
