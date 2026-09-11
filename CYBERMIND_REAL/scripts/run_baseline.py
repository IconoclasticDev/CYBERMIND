#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys,numpy as np
from sklearn.dummy import DummyClassifier
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.baselines.logistic import LogisticBaseline

def feat(s):
    x=np.stack([st.x.numpy().mean(0) for st in s.states],0)
    return x.reshape(-1)

a=argparse.ArgumentParser(); a.add_argument('--processed',default='data/processed'); a.add_argument('--split',default='test'); args=a.parse_args(); root=Path(__file__).resolve().parents[1]
tr=GraphSequenceDataset(root/args.processed/'train.pt'); te=GraphSequenceDataset(root/args.processed/f'{args.split}.pt')
if len(tr)==0:
    raise SystemExit('No training sequences in processed/train.pt')
Xtr=np.stack([feat(s) for s in tr]); ytr=np.array([int(any(st.y_infiltration>0 for st in s.states)) for s in tr])
if len(te)==0:
    out={'baseline':'logistic_regression_or_dummy','split':args.split,'metrics':{'note':'split is empty; generate more scenarios or use chronological fallback'}}; (root/'results').mkdir(exist_ok=True); (root/'results'/f'baseline_{args.split}.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2)); raise SystemExit(0)
Xte=np.stack([feat(s) for s in te]); yte=np.array([int(any(st.y_infiltration>0 for st in s.states)) for s in te])
if len(np.unique(ytr))<2:
    model=DummyClassifier(strategy='prior').fit(Xtr,ytr); pred=model.predict_proba(Xte)[:,1] if hasattr(model,'predict_proba') and model.classes_.size>1 else np.repeat(float(ytr.mean()),len(Xte)); metrics={'note':'dummy prior used because training split has one class','positive_rate':float(ytr.mean())}
else:
    model=LogisticBaseline().fit(Xtr,ytr); metrics=model.metrics(Xte,yte)
out={'baseline':'logistic_regression_or_dummy','split':args.split,'metrics':metrics}; (root/'results').mkdir(exist_ok=True); (root/'results'/f'baseline_{args.split}.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
