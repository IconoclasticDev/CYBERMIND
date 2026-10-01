from __future__ import annotations
import json
from pathlib import Path
from typing import Dict
import yaml


def load_stage_map(path):
    p=Path(path)
    return yaml.safe_load(p.read_text()).get('label_to_stage',{})


def parse_attack_stix(path):
    data=json.loads(Path(path).read_text())
    objs=data.get('objects',[]) if isinstance(data,dict) else []
    techniques={o.get('external_references',[{}])[0].get('external_id'):o.get('name') for o in objs if o.get('type')=='attack-pattern'}
    return {k:v for k,v in techniques.items() if k}


def load_knowledge_registry(root):
    root=Path(root)
    return {'stage_map':load_stage_map(root/'knowledge/stage_mapping.yaml')}
