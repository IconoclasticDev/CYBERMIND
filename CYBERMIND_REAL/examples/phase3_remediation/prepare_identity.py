"""Normalization-off diagnostic: rebuild identical raw graphs; no new feature signals."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import torch
import yaml

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from cybermind.data.normalization import FeatureNormalizer


def main():
    destination=OUT/'identity_processed'
    assert not destination.exists(),'Refuse to replace diagnostic data.'
    spec=importlib.util.spec_from_file_location('prepare',ROOT/'scripts/prepare_data.py')
    prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)
    original=ROOT/'examples/phase3_root_cause/original_pipeline'
    cfg=yaml.safe_load((original/'config.yaml').read_text())
    files=sorted((original/'canonical').glob('*.parquet'))
    frames=[prepare.canonicalize(prepare.read_any(p),str(p)) for p in files]
    transform=FeatureNormalizer.transform
    try:
        FeatureNormalizer.transform=lambda self,values,kind:values.to(dtype=torch.float32).clone()
        splits,actual_fit,reports=prepare.prepare_frames(frames,cfg)
    finally:
        FeatureNormalizer.transform=transform
    constants=copy.deepcopy(actual_fit.constants)
    constants['method']='identity_normalization_diagnostic'
    constants['original_train_statistics']=copy.deepcopy(actual_fit.constants)
    for kind in ('node','edge'):
        constants[kind]['mean']=[0.]*len(constants[kind]['mean'])
        constants[kind]['std']=[1.]*len(constants[kind]['std'])
    identity=FeatureNormalizer(constants)
    checks={}
    for split,samples in splits.items():
        prior=torch.load(original/'processed'/f'{split}.pt',weights_only=False)
        assert len(prior)==len(samples)
        max_error=0.
        for a,b in zip(samples,prior):
            a.metadata['normalization_fingerprint']=identity.fingerprint
            for s,t in zip(a.states,b.states):
                assert (s.timestamp,s.y_stage,s.y_infiltration)==(t.timestamp,t.y_stage,t.y_infiltration)
                assert torch.equal(s.edge_index,t.edge_index)
                for kind,raw,normalized in [('node',s.x,t.x),('edge',s.edge_attr,t.edge_attr)]:
                    reprojected=actual_fit.transform(raw,kind)
                    torch.testing.assert_close(reprojected,normalized,atol=1e-6,rtol=1e-6)
                    max_error=max(max_error,float((reprojected-normalized).abs().max()))
                s.metadata.update(normalization_fingerprint=identity.fingerprint,
                                  campaign_reset=t.metadata['campaign_reset'],
                                  campaign_reset_source=t.metadata['campaign_reset_source'])
        checks[split]=dict(sequences=len(samples),labels_and_topology_unchanged=True,normalized_reprojection_max_error=max_error)
    destination.mkdir()
    for split,samples in splits.items():torch.save(samples,destination/f'{split}.pt')
    identity.save(destination/'normalization.json')
    metadata=json.loads((original/'processed/metadata.json').read_text())
    metadata.update(normalization_fingerprint=identity.fingerprint,normalization_ablation='identity, diagnostic only')
    (destination/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    (OUT/'normalization_audit.json').write_text(json.dumps(dict(synthetic_only=True,
        original_method=actual_fit.constants['method'],original_fit_split='train',
        new_method='identity: no centering or scaling',fixture_features_added=False,
        split_checks=checks,note='Rebuilt same canonical rows. Identity preprocessing is the explicitly authorized normalization ablation, not a new class-encoded fixture.'),indent=2),encoding='utf-8')


if __name__=='__main__':main()
