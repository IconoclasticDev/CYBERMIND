"""Fixed CPU diagnostics, sequential to bound laptop memory; failed cases stay failed."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
CASES=[('normalization_off100',['--identity-normalization']),
       ('class_weighted100',['--class-balance']),
       ('lr_0001_cpu',['--lr','.0001']),('lr_001_cpu',['--lr','.001']),
       ('lr_003_cpu',['--lr','.003']),('lr_01_cpu',['--lr','.01'])]


def main():
    plan=OUT/'remaining_plan.json'
    if plan.exists():raise FileExistsError('Do not replace a recorded diagnostic plan.')
    plan.write_text(json.dumps(dict(cases=CASES,epochs_each=100,device='cpu',fixture='original integration',
        gate='unchanged independent steps 1-4',selection='existing validation infiltration F1',
        note='Settings fixed before these experiments, no test-driven retries.'),indent=2),encoding='utf-8')
    records=[]
    for name,flags in CASES:
        print('CASE',name,flush=True)
        result=subprocess.run([sys.executable,'examples/phase3_remediation/run_case.py','--name',name,'--device','cpu',*flags],cwd=ROOT)
        records.append(dict(name=name,exit_code=result.returncode))
        (OUT/'remaining_execution.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print('ALL DECLARED DIAGNOSTICS EXECUTED',flush=True)


if __name__=='__main__':main()
