"""Build the requested single Markdown report from logged evidence and exact source."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def source(a,b):return '\n'.join((ROOT/'scripts/train.py').read_text().splitlines()[a-1:b])
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(str(v) for v in row)+' |' for row in rows])


def main():
    primary=read(OUT/'original_cuda/rollout.json')
    matrix=primary['samples'][0]['steps'][0]['transition_matrix']
    sample=primary['samples'][0]['steps']
    numbers=read(OUT/'numerical_summary.json')
    sections=[]
    sections.append('''# PHASE3 ROOT CAUSE AUDIT

Date: 2026-09-13. Active project: `CYBERMIND_REAL`; starting commit: `6634712`.

**Phase 3 exit criteria NOT met.** The original, non-prototype fixture remains collapsed at every checked future step. No production decoder or training fix has been established. The earlier balanced-fixture result is not accepted as resolution of this failure.

No exit gate, hard transition mask, original fixture, or Phase 4 configuration was changed. No balanced/prototype fixture was trained or evaluated in this audit. Numerical loss-weight controls below are diagnostic experiments on the original data, not substituted gates or claimed fixes.

## 1. Root cause identified — original-fixture reproduction and logged evidence

### Reproduction and scope

The original `scripts/phase01_smoke.py` pipeline was rerun with both features enabled, seed 42, its original two epochs, architecture, batch size and input generation, in `examples/phase3_root_cause/original_pipeline/`. Its CPU training history and existing evaluation fields reproduce `examples/phase3_joint/combined/` within **1e-6**. Node tensors, edge tensors, topology, timestamps, labels and reset declarations match exactly: **122 train / 25 validation / 25 test sequences**. Only output/provenance paths differ.

The same original tensors were then trained on CUDA with instrumentation and checked at horizons 1–4. The other original failed fixture, the frozen tensors used by `configs/smoke.yaml`, was also retrained and checked. Both selected and final-epoch checkpoints were inspected. All experiments ran two epochs; no extra training epochs or prototype signals were introduced. The original integration run contains 16 training batches and accumulates two batches per optimizer step: only eight optimizer updates total. The frozen smoke run contains 36 updates. These counts contextualize the short training exposure; they do not establish that extra training would fix the unchanged two-epoch gate.

`instrument_train.py` wraps the active `scripts/train.py` without replacing its loss or optimizer. At every training batch it logs pre-update CRF matrices, StageHead emissions, labels, weighted losses, and CE/CRF gradient norms and cosines. `autograd.grad` measures contributions without modifying accumulated parameter gradients. `inspect_rollouts.py` captures the actual StageHead forward output used by `WorldModel.forecast`, including individual trajectories and their mean emissions. It logs the unmasked emissions, raw argmax, Viterbi result, raw and masked 7×7 transition matrices at each step 0–4. A CRF matrix is shared across time, so its per-step values repeat within a checkpoint.

Full numeric records: [training diagnostics](examples/phase3_root_cause/original_cuda/training_diagnostics.jsonl), [per-sample/per-step rollout traces](examples/phase3_root_cause/original_cuda/rollout.json), [input signal audit](examples/phase3_root_cause/input_signal.json), and [commands](examples/phase3_root_cause/commands.json).

### Cause (c): pre-CRF emission degeneracy — CONFIRMED as the immediate collapse mechanism

On the main original CUDA checkpoint, raw emission argmax is identical across **all 25 test histories at each individual step**, before the CRF is applied. Steps 1–2 prefer Reconnaissance; steps 3–4 prefer Benign. Aggregating those two labels across time would conceal the per-step collapse and is not treated as a pass.

Actual mean StageHead logits below are ordered `[Benign, Recon, Initial Access, Lateral Movement, C&C, Exfiltration, Unknown]`. Entropy is divided by `ln(7)`, so 1 is uniform; logit SD is the maximum across the seven class-wise standard deviations over the 25 histories.
''')
    sections.append(table(['Future step','Mean unmasked logits','Raw argmax histogram','Normalized entropy','Max logit SD'],[
        [s['step'],'`['+', '.join(f'{x:.6f}' for x in s['mean_logits'])+']`',str(s['raw_argmax_histogram']),f"{s['mean_normalized_entropy']:.6f}",f"{s['max_across_sample_logit_std']:.6f}"] for s in primary['per_step']]))
    sections.append('''
These weak-confidence, very similar emission vectors do not separate the histories into different predicted stages. The frozen original smoke fixture is also collapsed, but **not near-uniform**: its normalized emission entropy falls from **0.623541 at step 1 to 0.355259 at step 4**, while its Benign winner margin grows from **1.694523 to 2.521769**. Thus “degenerate” here includes a confident single-class bias; it does not mean every failed model has uniform logits.

The original integration input audit explains why an upstream learning problem is plausible without claiming mathematical impossibility:

- Only **2/34 node features** (`bytes_total`, `bytes_per_flow`) and **1/27 edge features** (`bytes`) vary. Their correlation with time is effectively **1.0**; every graph has the same topology.
- Across **45 mixed-label seconds**, BENIGN and PORTSCAN flows have identical nonlabel fields in **45/45** cases. The source generator assigns labels periodically while byte volume increases monotonically.
- Training has **184 Benign vs 60 Recon supervised positions**. Their normalized byte-feature mean separation is only **0.0558744 overall standard deviations**. Validation means are **2.1371967565 vs 2.1371967991**; test means are **2.9194387027 vs 2.9194386800**.

This is direct evidence of weak class signal, imbalance and extrapolation in time-correlated volume. A modulo-four rule is theoretically recoverable from time-correlated bytes, so this report does **not** declare the task unlearnable. Nor do the traces isolate a single encoder layer as defective: they identify the **upstream encoder/dynamics/StageHead learning path**, before CRF decoding, as failing to produce discriminating stage decisions. A successful upstream correction remains unresolved.

### Cause (a): learned stay-transition dominance — affects winner, but does not explain away the diversity failure

The selected original CUDA checkpoint has the following learned scores. Rows are source stages and columns are destinations, in stage-ID order 0–6. These same raw values are logged at all four future steps; the unchanged policy masks illegal entries to `-inf`. A stored score for a reset edge is not permission to use it without an explicit reset.
''')
    sections.append(table(['Source → destination']+[str(i) for i in range(7)],[[i]+[f'{x:.6f}' for x in row] for i,row in enumerate(matrix)]))
    e0=sum(s['emission_logits'][0] for s in sample);e1=sum(s['emission_logits'][1] for s in sample)
    sections.append(f'''
Stay scores over stages 0–5 range from **{primary['transition_summary']['stay_min']:.6f} to {primary['transition_summary']['stay_max']:.6f}**; forward scores range from **{primary['transition_summary']['forward_min']:.6f} to {primary['transition_summary']['forward_max']:.6f}**. In particular, `T[0,0]={matrix[0][0]:.9f}` is slightly **below** `T[0,1]={matrix[0][1]:.9f}`, not a general stay-over-forward preference.

There is nevertheless a measurable tie-breaking effect. For the first logged history, the all-Benign path has emission sum **{e0:.9f}** and transition contribution **{4*matrix[0][0]:.9f}**, total **{e0+4*matrix[0][0]:.9f}**. The all-Recon path has emission sum **{e1:.9f}** and transition contribution **{4*matrix[1][1]:.9f}**, total **{e1+4*matrix[1][1]:.9f}**. Learned transitions narrowly select Benign.

When learned transition scores are set to zero **in memory for a diagnostic decode only**, retaining every hard mask and exactly the same emissions, all four steps instead predict Recon for **25/25** histories. Diversity remains **one stage at every step**. Hence the learned scores can change the collapsed class, but removing them does not fix collapse. The hard ordering also suppresses the raw `Recon → Benign` reversal at later steps; no mask was relaxed to permit it.

### Cause (b): CE/CRF scale imbalance — MEASURED, but not demonstrated as a sufficient cause

The active objective gives CE and sequence CRF NLL weights of 0.5 each. CE averages over target windows, whereas CRF NLL averages sequence totals over the batch. Their effective scales therefore differ. These are actual first-training-batch measurements on the same original integration inputs and initialization:
''')
    sections.append(table(['Experiment','Weighted CE','Weighted CRF NLL','CE head-gradient norm','CRF head-gradient norm','CRF/CE ratio'],[
        [name,f"{numbers[name]['first_batch']['weighted_ce']:.6f}",f"{numbers[name]['first_batch']['weighted_crf']:.6f}",
         f"{numbers[name]['first_batch']['gradients']['stage_head_weight']['ce_norm']:.6f}",f"{numbers[name]['first_batch']['gradients']['stage_head_weight']['crf_norm']:.6f}",f"{numbers[name]['first_batch']['gradients']['stage_head_weight']['crf_to_ce_ratio']:.6f}"]
        for name in ('original_cuda','crf_weight_zero','crf_per_token')]))
    sections.append('''
`crf_weight_zero` sets only the CRF loss weight to 0; the decoder and all masks remain present. `crf_per_token` sets the weight to 0.25, scaling NLL by the original target length of two. These control settings were fixed before their results were observed. Neither is adopted as a production fix.

Over all **16 original integration training batches**, the CRF/CE head-gradient ratio is **2.004687–2.038685**, with cosine **0.995872–0.997350**. The two contributions are almost aligned rather than pulling the head in opposite directions. On the original frozen fixture with seven target windows, first-batch weighted CE/NLL are **1.033069 / 5.861217**, with head-gradient norms **1.043125 / 7.708958**, ratio **7.390255**. That confirms a substantial length-dependent scale difference; it does not establish that it alone causes the frozen fixture's collapse.

Crucially, the original integration model **still collapses at every step when the CRF contribution is removed or normalized**; see section 4. Scale imbalance can affect training and which class wins, but these experiments do not support claiming that changing this weight fixes the root failure. The causal contribution of that imbalance beyond the tested controls remains unproven.

**Cause summary:** (c) is directly observed before masking; (a) has a measured winner/tie-breaking effect but its removal does not restore diversity; (b) has a measured scale imbalance, but two controlled weight changes do not restore diversity. No successful root-cause fix is claimed.

## 2. Four-step diversity and illegal-transition check

The new original-fixture audit runner explicitly calls `model.forecast(..., k=4, ...)`, matching `eval.rollout_steps: 4`. It does not rely on the existing one-step `scripts/eval.py` report. Each step is checked independently over the test histories. Illegal transitions at step `t` count the pair from `t-1` to `t`; no future resets are declared or inferred. Step zero is excluded from diversity. A step passes only with at least two non-Unknown stages, fewer than 100% Unknown predictions, and zero illegal pairs.

All results below use original non-prototype inputs and the unmodified objective/decoder. “Frozen smoke” is the second original failed fixture, not the balanced replacement. The selected checkpoints are epoch 1; final-epoch checks appear in section 4.
''')
    rows=[]
    for name,label in [('original_pipeline','Original pipeline, CPU'),('original_cuda','Original pipeline, CUDA'),('original_frozen_cuda','Original frozen smoke, CUDA')]:
        r=read(OUT/name/'rollout.json')
        for s in r['per_step']:
            rows.append([label,s['step'],s['distinct_non_unknown'],f"{s['illegal_count']}/{s['samples']}",s['unknown_count'],str(s['decoded_histogram']),'PASS' if s['passed'] else 'FAIL'])
    sections.append(table(['Run','Step','Distinct non-Unknown','Illegal pairs','Unknown count','Predicted histogram','Verdict'],rows))
    sections.append('''
Zero illegal transitions does not compensate for diversity failure. The four-step Viterbi horizon can change the class chosen at earlier steps because it optimizes a full path; that is why the original CUDA four-step result can differ from the earlier one-step class while both remain collapsed. Steps 2–4 have no held-out ground-truth target inside these short samples, so this table assesses structural predictions, not four-step forecast accuracy.

The historical PDF's nonzero-illegal-rate wording conflicts with its hard-mask requirement. That conflict is flagged, **not corrected or replaced here**. The requested four-step check above fails anyway. No alternative fixture is used to obtain a pass.

## 3. Actual checkpoint-selection path — PASS: validation-metric-based

The real executed file is `CYBERMIND_REAL/scripts/train.py`. The instrumented wrapper imports that exact file and calls its `main()`; the ordinary measurement wrapper executes the same sibling file. The active training path uses **held-out validation infiltration F1**, not training loss. It does **not** select for stage diversity, stage accuracy, or four-step forecast quality.

Exact active source, `scripts/train.py`, lines **160–166**:
''')
    sections.append('```python\n'+source(160,166)+'\n```')
    sections.append('Exact validation loader, line **190**:\n\n```python\n'+source(190,190)+'\n```')
    sections.append('Exact metric calculation, lines **110–115**:\n\n```python\n'+source(110,115)+'\n```')
    sections.append('''
`validate()` (lines 124–140) runs on `val_loader`. It gathers the infiltration probabilities and labels returned by `batch_loss()` (lines 79–81 and 105–106), then invokes the F1 calculation above. Training losses are recorded in history but are not used in the `improved` comparison.

Exact best-checkpoint and last-checkpoint block, lines **223–236**:
''')
    sections.append('```python\n'+source(223,236)+'\n```')
    sections.append('''
For the original integration CUDA rerun, validation F1 is **0.0 in both epochs**. `best` starts at -1 (line 191), so epoch 1 is saved, and the strict `>` comparison rejects the epoch-2 tie. The `_last.pt` checkpoint is still saved every epoch. For the previous balanced run, the recorded F1 tie was 1.0/1.0; the same rule really did select epoch 1. That selection claim was correct for the active path, although it did not establish stage diversity on the original fixture.

A separate older copy exists at `../multisource_audit/CYBERMIND_REAL/scripts/train.py`. Its lines **59–61** are training-loss based:

```python
        # Best checkpoint is training-loss based; final evaluation remains separate and leakage-free.
        if mean<best:
            best=mean; (root/'checkpoints').mkdir(exist_ok=True); torch.save({'model_state':m.state_dict(),'optimizer_state':opt.state_dict(),'config':cfg,'node_dim':node_dim,'epoch':ep+1,'best_loss':best},root/'checkpoints'/ckpt_name)
```

That older copy would receive **FAIL** for validation-metric selection, but it is not the file executed by these experiments. It must not be conflated with the active implementation. The verdict for the active real path is explicitly **PASS**; no unresolved training-loss-selection gap is asserted for that file.

## 4. Fix verification on the original fixture — NOT FIXED

No evidence-backed decoder patch emerged. A learned-score-free inference control and two CRF loss-weight controls were tested on the original fixture. They did not fix per-step diversity. No production model or loss implementation was modified, and none of these controls is promoted as a fix.

The cells below show **distinct non-Unknown / illegal pairs / Unknown count** for each step. Original integration rows have 25 histories; frozen rows have 3. Selected and final-epoch checkpoints are both included to test whether checkpoint selection hid a successful second epoch.
''')
    rows=[]
    for name,label in [('original_cuda','Unchanged original'),('crf_weight_zero','CRF loss weight 0'),('crf_per_token','CRF loss weight 0.25'),('original_frozen_cuda','Unchanged frozen original')]:
        for suffix,which in [('','selected'),('_last','last')]:
            r=read(OUT/name/f'rollout{suffix}.json')
            rows.append([label,f"{which}, epoch {r['selected_epoch']}"]+[f"{s['distinct_non_unknown']} / {s['illegal_count']} / {s['unknown_count']}" for s in r['per_step']]+['PASS' if r['all_steps_pass'] else 'FAIL'])
    sections.append(table(['Original-data experiment','Checkpoint','Step 1','Step 2','Step 3','Step 4','All-step verdict'],rows))
    sections.append('''
The learned-transition-zero decode also has one non-Unknown stage at all four steps. Neither disabling the CRF training contribution nor reducing it to a per-target-window scale restores diversity. The second-epoch checkpoints remain collapsed, so selecting epoch 1 is not the entire explanation.

**Prototype-style separation disabled/absent:** every experiment in this report uses original inputs with no prototype feature construction. The successful balanced checkpoint is not used. Therefore there is no evidence that a fix works without artificial separation: the non-prototype checks fail. Removing the artificial signals from a replacement fixture is not substituted for testing the original fixture.

The testable extension itself is complete: all four steps now have independently checked results and complete numerical logs. The model failure is not fixed.

## 5. Final verdict

**Phase 3 exit criteria NOT met.**

What remains:

1. Establish and verify an upstream representation/training correction that produces noncollapsed stage predictions on the **unchanged original fixture**, at **each** of rollout steps 1–4. The current diagnosis locates the observed failure before CRF masking and quantifies weak input signal, but does not supply a successful upstream fix.
2. Retain zero illegal transitions and avoid 100% Unknown predictions at every step. These conditions currently pass, but diversity does not.
3. Re-run any actual fix on the same original inputs and gate, with no prototype separation, changed threshold, alternative fixture, or aggregate-across-time shortcut.
4. Resolve any literal PDF-gate contradiction through review rather than silently changing it. No gate has been loosened in this audit.

Checkpoint selection in the active real path is verified as validation-based; that item does not remain open. Phase 4 remains prohibited pending delivery and review of this report.

### Evidence integrity and reproduction

`preservation_and_reproduction.json` verifies all **49 frozen baseline files**, **112 original Phase 3 evidence files + 27 local tensor/checkpoint files**, and **14 balanced-era evidence files + 5 local tensor/checkpoint files** are unchanged. The balanced files were hash-checked only, not used for a model run. An independent counter recomputed the per-step illegal, Unknown and diversity counts from the logged paths.

New instrumentation and evidence live only under `examples/phase3_root_cause/`; local checkpoints/tensors are excluded from Git and fingerprinted in `manifest.json`. The active model, decoder, training loop and prohibited Phase 4 configs are untouched. The command log records all original-data runs; diagnostic process success is never interpreted as a phase-gate pass. All data are synthetic and none of these results is a real-corpus accuracy claim.
''')
    (ROOT/'PHASE3_ROOT_CAUSE_AUDIT.md').write_text('\n\n'.join(sections),encoding='utf-8')


if __name__=='__main__':main()
