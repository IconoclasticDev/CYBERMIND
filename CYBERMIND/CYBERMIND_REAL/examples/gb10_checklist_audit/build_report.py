"""Read-only local evidence collection; no installs, training or source edits."""
from pathlib import Path
import ast
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/GB10_CHECKLIST_REPORT.md'
parts = ['# GB10 verification checklist: evidence report\n\n'
         'Scope: current local Windows project, not the real GB10 host. No GB10 connection or real corpus was provided. '
         'This is a reporting pass; no dependencies were installed and no training was launched. '
         'Item suffixes number the bullets in each section of the supplied checklist. '
         'PASS for source items means present in the inspected local source, not deployed/verified on GB10. '
         'UNKNOWN means the required host/data/runtime evidence is absent.\n']


def file(path):
    return (ROOT / path).read_text(encoding='utf-8-sig')


def block(text, language='text'):
    fence = '````' if '```' in text else '```'
    parts.append(f'{fence}{language}\n{text.rstrip()}\n{fence}\n')


def item(number, status, note):
    parts.append(f'## {number} — {status}\n\n{note}\n')


def source(path, functions=None):
    text = file(path)
    parts.append(f'Source: `{path}`\n')
    if functions is None:
        block(text, 'python' if path.endswith('.py') else 'text')
        return
    lines = text.splitlines()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in functions:
            parts.append(f'Lines {node.lineno}–{node.end_lineno}:\n')
            block('\n'.join(lines[node.lineno-1:node.end_lineno]), 'python')


def command(args):
    parts.append('Command (project root):\n')
    block(subprocess.list2cmdline(args))
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    block(result.stdout if result.stdout else '(no stdout)')
    if result.stderr:
        parts.append('stderr:\n')
        block(result.stderr)
    parts.append(f'Exit code: `{result.returncode}`\n')
    return result


item('0.1', 'UNKNOWN', 'GB10 OS/architecture not checked: no target-host shell. The following is local evidence only; Linux commands were not represented as GB10 results.')
command([sys.executable, '-c', 'import platform; print(platform.system()); print(platform.machine()); print(platform.platform())'])
item('0.2', 'UNKNOWN', 'GB10 visibility/driver version: target-host nvidia-smi was not run. No GB10 output is available.')
item('0.3', 'UNKNOWN', 'GB10 toolkit/driver CUDA version: no target-host nvcc or nvidia-smi output. A driver-advertised CUDA version alone would not establish the installed toolkit version.')
item('0.4', 'UNKNOWN', 'cu130 aarch64 PyTorch on GB10: unverified. Local environment is CPU-only; nothing was installed in this reporting pass.')
command([sys.executable, '-c', 'import torch; print(torch.__version__); print(torch.version.cuda)'])
item('0.5', 'UNKNOWN', 'GB10 device/capability: no target-host output. Requested expression run locally below fails on the CPU build; it does not establish anything about the GB10.')
command([sys.executable, '-c', 'import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_capability(0))'])
item('0.6', 'UNKNOWN', 'PyG on GB10 is unknown. Local import result follows. Additional inconsistency: current gpu_preflight.py treats missing PyG as a failure, whereas this checklist says it should not block fallback training. That policy mismatch remains unfixed in this report-only pass.')
command([sys.executable, '-c', "import torch_geometric; print('PyG OK', torch_geometric.__version__)"])
item('0.7', 'UNKNOWN', 'GB10 encoder branch cannot be inspected without that runtime. Local PyG import succeeds; local encoder selection is printed below. Source confirms fallback only when the import fails.')
command([sys.executable, '-c', "import sys; sys.path.insert(0,'src'); from cybermind.models.graph_encoder import HAS_PYG, GATv2GraphEncoder; m=GATv2GraphEncoder(3,8,8,2); print('HAS_PYG =', HAS_PYG); print('conv1 =', type(m.conv1).__name__)"])
source('src/cybermind/models/graph_encoder.py')
item('0.8', 'UNKNOWN', 'bf16 on GB10 remains unverified. This result belongs to the local CPU runtime.')
command([sys.executable, '-c', 'import torch; print(torch.cuda.is_bf16_supported())'])

item('1.1', 'PASS', 'Required local directories exist and are nonempty. Windows-compatible listing used instead of Unix find/ls.')
command([sys.executable, '-c', "from pathlib import Path; roots=['src/cybermind','scripts','configs','tests']; [(print(p, 'exists=',Path(p).is_dir(),'nonempty=',any(Path(p).iterdir())), [print(x) for x in sorted(Path(p).iterdir())]) for p in roots]"])
item('1.2', 'PASS', 'GB10 configuration exists. Full contents:')
source('configs/gb10_full.yaml')
item('1.3', 'PASS', 'configs/final.yaml exists; this is not a missing-file reference. It is a separate older configuration and does not have the GB10 normalization/bf16 requirements.')
command([sys.executable, '-c', "from pathlib import Path; print('configs/final.yaml exists:',Path('configs/final.yaml').is_file())"])
source('configs/final.yaml')
item('1.4', 'PASS', 'The referenced report exists. Its full contents are reproduced in Appendix A, as requested. It is prior reporting, not independent proof of GB10 readiness.')
command([sys.executable, '-c', "from pathlib import Path; print('docs/PHASE01_FINAL_REPORT.md exists:',Path('docs/PHASE01_FINAL_REPORT.md').is_file())"])
item('1.5', 'PASS', 'Both scripts and normalization module exist. The package-relative data/normalization.py is src/cybermind/data/normalization.py, not a top-level data script. Full contents appear in Appendix B.')
command([sys.executable, '-c', "from pathlib import Path; [print(p,Path(p).is_file()) for p in ['scripts/phase01_smoke.py','scripts/gpu_preflight.py','src/cybermind/data/normalization.py']]"])

item('2.1', 'PASS', 'fp32 normalization is implemented, persisted, fitted on training only and applied across splits. Graph construction also accepts a normalizer or loads its path; feature_extract.py need not call it independently.')
source('src/cybermind/data/normalization.py', ['__init__', 'update', 'fit', 'transform', 'save'])
source('scripts/prepare_data.py', ['prepare_frames'])
source('src/cybermind/data/graph_builder.py', ['build_graph_state'])
item('2.2', 'PASS', 'Requested IPv4 packet features are computed by the following functions. Scan signatures are heuristics; capture-local state and absence of IPv6 support remain limitations.')
source('src/cybermind/data/pcap_extract.py', ['_scan_features', '_add_sequence', '_row', 'pcap_to_dataframe'])
item('2.3', 'PASS', 'Seven labels include distinct C2. Important precision: the adapter calls the Python classifier, not a YAML loader. The equivalent taxonomy is implemented in stages.py; editing YAML alone does not change runtime classification. The existing taxonomy test checks the YAML entries against that classifier.')
source('knowledge/stage_mapping.yaml')
source('src/cybermind/data/adapters/unified.py', ['_stage'])
source('src/cybermind/data/stages.py')
source('tests/test_packet_taxonomy.py', ['test_named_taxonomy_and_unknowns'])
item('2.4', 'PASS', 'Environment grouping and chronological sorting occur before sequence construction. The adapter explicitly preserves environment_id.')
source('scripts/prepare_data.py', ['chain_environments'])
command(['rg', '-n', '-A', '2', '-B', '1', 'environment_id', 'src/cybermind/data/adapters/unified.py'])
item('2.5', 'PASS', 'Automatic explanations are invoked inside forecast(); app/eval call it and emit its explanation. The checklist keyword search in app/eval alone has no matches because implementation is delegated to model/attribution modules. Literal search output and actual call chain follow.')
command(['rg', '-n', 'attribution|need_weights|occlusion', 'scripts/app.py', 'scripts/eval.py'])
command(['rg', '-n', 'forecast|explanation', 'scripts/app.py', 'scripts/eval.py'])
source('src/cybermind/models/world_model.py', ['forecast'])
source('src/cybermind/models/temporal_encoder.py', ['forward'])
source('src/cybermind/explainability/attribution.py', ['gradient_feature_attribution', 'explain_forecast'])
item('2.6', 'PASS', 'Training-derived negative/positive weight is passed into BCE. Counts are target occurrences in overlapping sequences, not deduplicated windows. No upper cap is implemented; real-data suitability is UNKNOWN under 4.3.')
source('src/cybermind/losses.py', ['infiltration_loss'])
source('scripts/train.py', ['training_class_weight'])
command(['rg', '-n', 'pos_weight|weight, counts', 'scripts/train.py'])
item('2.7', 'PASS', 'Consistency is computed and included in weighted summed total. Full batch_loss code:')
source('scripts/train.py', ['batch_loss'])
item('2.8', 'PASS', 'Dynamics returns mean/log-variance and reparameterizes; forecast expands the initial latent to N trajectories before rollout.')
source('src/cybermind/models/dynamics.py')
source('src/cybermind/models/world_model.py', ['_forecast_core'])
item('2.9', 'PASS', 'Best checkpoint uses validation F1 rather than training loss.')
command(['rg', '-n', '-A', '18', 'metrics = validate', 'scripts/train.py'])

item('3.1', 'FAIL', 'Legacy command blocks remain despite the top banner. Quickstart uses smoke.yaml and gpu_128gb.yaml; One-command training resumes best_128gb.pt and its launcher defaults to gpu_128gb.yaml; Final pre-training automation explicitly uses gpu_128gb.yaml; One-command lab training invokes a helper hardcoded to gpu_128gb.yaml. No edits were made in this reporting pass.')
command(['rg', '-n', 'gpu_128gb|best_128gb|smoke.yaml|final.yaml|^##', 'README.md'])
command(['rg', '-n', 'gpu_128gb|best_128gb|launch_training', 'scripts/one_click_train.py', 'scripts/run_training_from_zero.sh', 'scripts/launch_training.py'])
item('3.2', 'FAIL', 'The file is .gitignore. *.pt, results/*.json and results/*.png are excluded: ordinary git add/push will omit matching untracked checkpoints/results unless explicitly included. Already-tracked files are not affected by ignore rules. This workspace is not currently a Git repository, so tracked/force-added status cannot be checked. Submission-artifact inclusion remains unresolved.')
source('.gitignore')
command(['git', 'rev-parse', '--is-inside-work-tree'])

item('4.1', 'UNKNOWN', 'No real single-day CIC subset was prepared or profiled. Prior runs were synthetic. Local data directory listing and integration evidence follow; these do not describe any remote GB10 storage.')
command([sys.executable, '-c', "from pathlib import Path; [print(p) for p in sorted(Path('data').rglob('*')) if p.is_file()]"])
source('examples/phase01_integration/verification.json')
item('4.2', 'UNKNOWN', 'No measured memory/file-count series exists. Linear or worse-than-linear scaling cannot be concluded. No extrapolation fabricated.')
item('4.3', 'UNKNOWN', 'Real positive/negative ratio and stability of pos_weight have not been measured. Source under 2.6 shows uncapped negative/positive weighting. Existing synthetic training log is quoted solely as fixture evidence:')
command(['rg', '-n', 'class_counts|pos_weight', 'examples/phase01_integration/step_3.log'])
item('4.4', 'UNKNOWN', 'Real any-attack versus majority-vote positive-window fractions have not been calculated. The actual rule is quoted below; a passing synthetic regression does not supply those real-data percentages.')
command(['rg', '-n', '-B', '2', '-A', '1', 'infil =', 'src/cybermind/data/graph_builder.py'])
item('4.5', 'UNKNOWN', 'Real PCAP availability and packet-to-label alignment are unverified. Legacy PCAP helper uses filename-derived labels, which are not genuine packet-level ground truth.')
source('scripts/pcap_to_corpus.py', ['infer_label'])
command(['rg', '-n', 'infer_label|pcap_to_dataframe', 'scripts/pcap_to_corpus.py'])

item('5.1', 'UNKNOWN', 'GB10 access duration was not supplied and cannot be inferred from code.')
item('5.2', 'UNKNOWN', 'Target-host preflight was not run. Local preflight FAILS; full current stdout/stderr and exit code follow. This is not a GB10 result.')
command([sys.executable, 'scripts/gpu_preflight.py', '--config', 'configs/gb10_full.yaml'])
item('5.3', 'UNKNOWN', 'No one-epoch GB10 run or GPU-memory profile exists. Earlier two-epoch CPU smoke training is not a substitute. No training was started during this reporting pass.')
item('5.4', 'UNKNOWN', 'Early stopping is configured and the source contains an active break condition (code PASS), but a run actually reaching that condition has not been demonstrated; GB10 firing behavior remains UNKNOWN.')
command(['rg', '-n', 'early_stopping|min_delta|selection_metric', 'configs/gb10_full.yaml'])
command(['rg', '-n', '-A', '4', '-B', '2', 'stale >=', 'scripts/train.py'])

item('6.1', 'PASS', 'Deferred boundary preserved in inspected forecast/app/eval paths: variance is returned as dispersion; no operational variance-confidence gate is applied. Real validation of uncertainty is still not done.')
command(['rg', '-n', 'variance|confidence|threshold', 'src/cybermind/models/world_model.py', 'scripts/app.py', 'scripts/eval.py'])
item('6.2', 'PASS', 'Primary source is restricted to CIC-IDS2018; held-out sources are rejected on primary paths. This verifies code separation, not the contents of an absent real training dataset.')
source('scripts/build_corpus.py', ['validate_source'])
source('scripts/prepare_data.py', ['chain_environments'])
item('6.3', 'PASS', 'The inspected world-model forecast runs forward on the supplied states without a flow-threshold prefilter. The forecast and _forecast_core methods quoted in 2.5 and 2.8 show the unconditional path; evaluation thresholds act after predictions.')
command(['rg', '-n', 'forecast|threshold|for sample', 'scripts/eval.py'])

parts.append('## Previous test evidence (not rerun in this reporting pass)\n')
source('examples/phase01_integration/pytest.log')
parts.append('## Appendix A — full prior Phase 0–1 report\n')
source('docs/PHASE01_FINAL_REPORT.md')
parts.append('## Appendix B — full requested implementation files\n')
for path in ['scripts/phase01_smoke.py', 'scripts/gpu_preflight.py', 'src/cybermind/data/normalization.py']:
    source(path)
OUT.write_text('\n'.join(parts), encoding='utf-8')
print(OUT)
print('Checklist items: 36; PASS: 17; FAIL: 2; UNKNOWN: 17.')
print('Source and training artifacts unchanged; report/evidence builder written only.')
