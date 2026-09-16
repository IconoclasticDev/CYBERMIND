#!/usr/bin/env python3
"""Joint training with train-only class weights and validation F1 selection."""
from pathlib import Path
import argparse
from collections import Counter
import json
import math
import os
import re
import sys
from contextlib import nullcontext
from dataclasses import replace
import torch
import torch.nn.functional as F
from torch.optim import AdamW
from torch.utils.data import DataLoader
from tqdm import tqdm
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.data.dataset import GraphSequenceDataset, collate_identity
from cybermind.models.world_model import WorldModel
from cybermind.losses import (gaussian_transition_loss, infiltration_loss, stage_loss,
                              binary_brier, graph_consistency_loss, crf_stage_loss)
from cybermind.utils.config import load_config, edge_model_kwargs, stage_model_kwargs
from cybermind.utils.repro import seed_everything
from cybermind.utils.checkpoint_selection import CheckpointSelection


def atomic_torch_save(payload, path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    torch.save(payload, temporary)
    temporary.replace(path)


def atomic_json_write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def append_durable_jsonl(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, separators=(',', ':')) + '\n')
        handle.flush()
        os.fsync(handle.fileno())


@torch.no_grad()
def rollout_stage_monitor(model, dataset, cfg, device):
    """Evaluate the fixed four-step diversity signal on the validation split."""
    options = cfg['train']['collapse_monitor']
    steps = int(options.get('rollout_steps', 4))
    n_rollouts = int(options.get('n_rollouts', cfg.get('eval', {}).get('n_rollouts', 4)))
    histograms = [Counter() for _ in range(steps)]
    illegal = [0] * steps
    allowed = model.stage_decoder.allowed_transitions
    model.eval()
    for sample in dataset:
        observed = [replace(state, x=state.x.to(device, non_blocking=True),
                            edge_index=state.edge_index.to(device, non_blocking=True),
                            edge_attr=state.edge_attr.to(device, non_blocking=True))
                    for state in sample.states[:-1]]
        result = model.forecast(observed, k=steps, n_rollouts=n_rollouts,
                                seed=int(options.get('seed', 0)), explain=False)
        decoded = result['decoded_stages']
        for index in range(steps):
            source, destination = int(decoded[index]), int(decoded[index + 1])
            histograms[index][destination] += 1
            illegal[index] += int(not bool(allowed[source, destination]))
    records = []
    sample_count = len(dataset)
    for index, histogram in enumerate(histograms, start=1):
        distinct = len(set(histogram) - {6})
        unknown = histogram.get(6, 0)
        collapsed = distinct < 2 or unknown == sample_count
        records.append({'step': index, 'samples': sample_count,
                        'decoded_histogram': {str(key): value for key, value in sorted(histogram.items())},
                        'distinct_non_unknown': distinct, 'unknown_count': unknown,
                        'illegal_count': illegal[index - 1], 'single_stage_collapse': collapsed})
    return {'split': 'val', 'rollout_steps': steps, 'n_rollouts': n_rollouts,
            'seed': int(options.get('seed', 0)), 'per_step': records,
            'collapsed': any(record['single_stage_collapse'] for record in records)}


def training_class_weight(dataset):
    # Count exactly the target-window occurrences consumed by the training loss.
    labels = [float(s.y_infiltration) for sample in dataset for s in sample.states[1:]]
    if not labels or any(y not in (0., 1.) for y in labels):
        raise ValueError('Training infiltration labels must be binary and nonempty.')
    positive = int(sum(labels)); negative = len(labels) - positive
    if not positive or not negative:
        raise ValueError('Training split must contain benign and infiltration target windows.')
    return negative / positive, {'positive': positive, 'negative': negative}


def stage_class_balance_enabled(loss_config):
    enabled = loss_config.get('stage_class_balance', False)
    if not isinstance(enabled, bool):
        raise ValueError('loss.stage_class_balance must be a boolean.')
    return enabled


def training_stage_class_weights(dataset, num_stages):
    """Inverse-frequency weights from training target occurrences only.

    Repeated windows are counted as consumed by batch_loss. Absent classes get
    neutral weight 1; present classes each have equal total weighted mass.
    """
    if not isinstance(num_stages, int) or isinstance(num_stages, bool) or num_stages < 1:
        raise ValueError('num_stages must be a positive integer.')
    counts = [0] * num_stages
    for sample in dataset:
        for state in sample.states[1:]:
            label = state.y_stage
            if not isinstance(label, int) or isinstance(label, bool) or not 0 <= label < num_stages:
                raise ValueError('Training stage labels must be integer IDs in the taxonomy.')
            counts[label] += 1
    total = sum(counts)
    present = sum(count > 0 for count in counts)
    if not total:
        raise ValueError('Training stage supervision must be nonempty.')
    weights = [total / (present * count) if count else 1. for count in counts]
    return weights, counts


def configure_stage_class_weights(cfg, training_dataset):
    """Resolve once from train; the saved config is reused for validation."""
    if stage_class_balance_enabled(cfg['loss']):
        weights, counts = training_stage_class_weights(training_dataset, cfg['model']['num_stages'])
        cfg['loss']['stage_class_weights'] = weights
        cfg['loss']['stage_class_counts'] = counts


def stage_cross_entropy(logits, labels, loss_config):
    if not stage_class_balance_enabled(loss_config):
        return stage_loss(logits.float(), labels)
    weights = loss_config.get('stage_class_weights')
    if (not isinstance(weights, (list, tuple)) or len(weights) != logits.size(-1)
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) or value <= 0 for value in weights)):
        raise ValueError('loss.stage_class_weights must contain one finite positive weight per stage.')
    weight = torch.tensor(weights, dtype=torch.float32, device=logits.device)
    return F.cross_entropy(logits.float(), labels, weight=weight)


def assert_split_disjoint(train, val):
    def keys(dataset):
        return {(s.scenario_id, s.timestamp) for sample in dataset for s in sample.states}
    if keys(train) & keys(val):
        raise ValueError('Training and validation share graph windows; regenerate chronological splits.')


def validate_training_provenance(processed, cfg, datasets, normalization):
    if not cfg['data'].get('require_normalization', False):
        return
    from cybermind.data.normalization import FeatureNormalizer
    normalizer = FeatureNormalizer(normalization)
    metadata = json.loads((processed / 'metadata.json').read_text())
    if metadata.get('purpose') != 'primary' or metadata.get('primary_source') != 'CIC-IDS2018':
        raise ValueError('GB10 training requires a newly prepared primary CIC-IDS2018 corpus.')
    if metadata.get('normalization_fingerprint') != normalizer.fingerprint:
        raise ValueError('Corpus normalization fingerprint does not match stored constants.')
    seen = set()
    for dataset in datasets:
        for sample in dataset:
            for state in sample.states:
                if id(state) in seen: continue
                seen.add(id(state))
                if state.metadata.get('source') != 'CIC-IDS2018':
                    raise ValueError('Held-out or unknown-source graph found in production data.')
                if state.metadata.get('normalization_fingerprint') != normalizer.fingerprint:
                    raise ValueError('Unnormalized or differently normalized graph found in production data.')
                if cfg['data'].get('require_packet_features', False) and state.metadata.get('packet_feature_coverage', 0.) < 1.:
                    raise ValueError('Feature-complete training requires packet telemetry for all source rows; enrich flow CSVs from packet captures first.')


def batch_loss(model, batch, cfg, device, *, return_predictions=False):
    states = []
    for sample in batch:
        if len(sample.states) < 2:
            raise ValueError('Each training sequence needs at least two windows.')
        states.append([replace(s, x=s.x.to(device, non_blocking=True),
                               edge_index=s.edge_index.to(device, non_blocking=True),
                               edge_attr=s.edge_attr.to(device, non_blocking=True))
                       for s in sample.states])
    z = model.forward_batch(states)['temporal_latents']
    distribution = model.dynamics(z[:, :-1])
    mean, logvar = distribution['mean'], distribution['logvar']
    target = z[:, 1:].detach()
    l_trans = gaussian_transition_loss(mean, target, logvar)
    pred = model.dynamics.sample(mean, logvar) if model.training else mean
    logits = model.infiltration_head(pred).reshape(-1)
    labels = torch.tensor([s.y_infiltration for ss in states for s in ss[1:]], dtype=torch.float32, device=device)
    l_infil = infiltration_loss(logits, labels, cfg['loss'].get('pos_weight'))
    l_brier = binary_brier(logits, labels)
    stage_logits = model.stage_head(pred).reshape(-1, cfg['model']['num_stages'])
    stage_labels = torch.tensor([s.y_stage for ss in states for s in ss[1:]], dtype=torch.long, device=device)
    if torch.any((stage_labels < 0) | (stage_labels >= cfg['model']['num_stages'])):
        raise ValueError('Invalid stage ID; rebuild data with the current taxonomy.')
    l_stage = stage_cross_entropy(stage_logits, stage_labels, cfg['loss'])
    l_consistency = graph_consistency_loss(z)
    components = {'transition': l_trans, 'infiltration': l_infil, 'stage': l_stage,
                  'calibration': l_brier, 'graph_consistency': l_consistency}
    if cfg['loss'].get('use_crf_stage', False):
        if not model.use_crf_stage:
            raise ValueError('CRF loss requires a model constructed with use_crf_stage=True.')
        resets = [[s.metadata.get('campaign_reset', False) for s in sequence[1:]] for sequence in states]
        if any(not isinstance(value, bool) for row in resets for value in row):
            raise ValueError('Graph metadata campaign_reset must be an explicit boolean.')
        reset_mask = torch.tensor(resets,dtype=torch.bool,device=device)
        components['crf_stage'] = crf_stage_loss(model.stage_decoder,
            stage_logits.reshape(z.size(0),z.size(1)-1,-1),
            stage_labels.reshape(z.size(0),z.size(1)-1),reset_mask=reset_mask)
    total = sum(cfg['loss'].get(name, .1 if name == 'graph_consistency' else
                              cfg['loss'].get('stage', .5) if name == 'crf_stage' else 0.) * value
                for name, value in components.items())
    parts = {k: float(v.detach()) for k, v in components.items()}
    if return_predictions:
        return total, parts, torch.sigmoid(logits.float()).detach(), labels.detach()
    return total, parts


def validation_metrics(probabilities, labels, threshold=.5):
    pred = probabilities >= threshold; truth = labels.bool()
    tp = int((pred & truth).sum()); fp = int((pred & ~truth).sum()); fn = int((~pred & truth).sum())
    precision = tp / max(tp + fp, 1); recall = tp / max(tp + fn, 1)
    return {'precision': precision, 'recall': recall, 'f1': 2 * tp / max(2 * tp + fp + fn, 1),
            'threshold': threshold, 'positive': int(truth.sum()), 'negative': int((~truth).sum())}


def autocast_context(device, precision):
    if precision == 'fp32':
        return nullcontext()
    return torch.autocast(device_type=device.type, dtype=torch.bfloat16 if precision == 'bf16' else torch.float16)


def validate(model, loader, cfg, device, precision):
    model.eval(); sums = {}; count = 0; probabilities = []; labels = []
    with torch.no_grad():
        for batch in loader:
            with autocast_context(device, precision):
                loss, parts, p, y = batch_loss(model, batch, cfg, device, return_predictions=True)
            if not torch.isfinite(loss):
                raise FloatingPointError('Non-finite validation loss.')
            n = y.numel(); count += n
            for key, value in {'loss': float(loss), **parts}.items():
                sums[key] = sums.get(key, 0.) + value * n
            probabilities.append(p.cpu()); labels.append(y.cpu())
    ys = torch.cat(labels)
    if not ys.any() or ys.bool().all():
        raise ValueError('Validation split needs both classes for meaningful infiltration F1.')
    return {**{k: v / count for k, v in sums.items()},
            **validation_metrics(torch.cat(probabilities), ys, cfg['train'].get('selection_threshold', .5))}


def apply_run_name(cfg, run_name):
    """Isolate ablation outputs while keeping the four input YAMLs comparable."""
    if run_name is None:
        return
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_name):
        raise ValueError('run-name must contain only letters, digits, underscores or hyphens')
    for key, default in [('checkpoint', 'best.pt'), ('history_path', 'results/train_history.json')]:
        path = Path(cfg['train'].get(key, default))
        cfg['train'][key] = str(path.with_name(f'{path.stem}_{run_name}{path.suffix}'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True); parser.add_argument('--resume')
    parser.add_argument('--epochs', type=int, default=0)
    parser.add_argument('--run-name', help='Suffix checkpoint/history filenames to isolate ablation runs')
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto')
    args = parser.parse_args(); cfg = load_config(args.config); seed_everything(cfg.get('seed', 42))
    apply_run_name(cfg, args.run_name)
    root = Path(__file__).resolve().parents[1]
    device = torch.device(('cuda' if torch.cuda.is_available() else 'cpu') if args.device == 'auto' else args.device)
    precision = cfg['train'].get('precision', 'fp32')
    if precision not in ('fp32', 'bf16', 'fp16'):
        raise ValueError('precision must be fp32, bf16, or fp16.')
    if cfg['train'].get('require_cuda', False) and device.type != 'cuda':
        raise RuntimeError('This production config requires CUDA; use phase01_smoke.yaml for CPU checks.')
    if device.type == 'cuda' and precision == 'bf16' and not torch.cuda.is_bf16_supported():
        raise RuntimeError('This CUDA runtime does not support bf16.')
    if device.type == 'cpu' and precision == 'fp16':
        raise ValueError('CPU fp16 training is unsupported; use fp32 or bf16.')
    selection = CheckpointSelection(cfg['train'])
    processed = root / cfg['data']['processed_dir']
    train = GraphSequenceDataset(processed / 'train.pt'); val = GraphSequenceDataset(processed / 'val.pt')
    if not len(train) or not len(val):
        raise ValueError('Training and held-out validation must both be nonempty.')
    assert_split_disjoint(train, val)
    weight, counts = training_class_weight(train); cfg['loss']['pos_weight'] = weight
    configure_stage_class_weights(cfg, train)
    normalization_path = processed / 'normalization.json'
    normalization = json.loads(normalization_path.read_text()) if normalization_path.exists() else None
    if cfg['data'].get('require_normalization', False) and normalization is None:
        raise ValueError('Training-only normalization.json is required; run prepare_data in Phase 2.')
    validate_training_provenance(processed, cfg, (train, val), normalization)
    node_dim = train[0].states[0].x.size(1)
    model_cfg = {k: cfg['model'][k] for k in ('graph_hidden', 'graph_out', 'temporal_dim', 'nhead', 'temporal_layers', 'num_stages', 'dropout')}
    model_cfg['graph_heads'] = cfg['model'].get('graph_heads', 8)
    edge_options = edge_model_kwargs(cfg['model'], observed_edge_dim=train[0].states[0].edge_attr.size(1))
    model_cfg.update(edge_options)
    model_cfg.update(stage_model_kwargs(cfg))
    if edge_options['use_edge_features']:
        # Checkpoints must reconstruct the same edge projection at inference.
        cfg['model'].update(edge_options)
    model = WorldModel(node_dim, **model_cfg).to(device)
    optimizer = AdamW(model.parameters(), lr=cfg['train']['lr'], weight_decay=cfg['train']['weight_decay'])
    # bf16 uses its native exponent range and does not instantiate GradScaler.
    scaler = torch.amp.GradScaler('cuda') if device.type == 'cuda' and precision == 'fp16' else None
    bs = int(cfg['train'].get('batch_size', 1)); accum = int(cfg['train'].get('grad_accumulation', 1))
    if bs < 1 or accum < 1: raise ValueError('Batch size and accumulation must be positive.')
    common = dict(collate_fn=collate_identity, num_workers=int(cfg['train'].get('num_workers', 0)), pin_memory=device.type == 'cuda')
    loader = DataLoader(train, batch_size=bs, shuffle=True, **common)
    val_loader = DataLoader(val, batch_size=bs, shuffle=False, **common)
    start_epoch = 0; best = -1.; stale = 0; history = []
    if args.resume:
        ck = torch.load(args.resume, map_location='cpu', weights_only=False)
        if ck.get('selection_metric') != selection.metric:
            raise ValueError('Resume requires the same validation selection policy.')
        if selection.metric == 'val_f1_stage_band':
            for key in ('selection_f1_tolerance', 'selection_stage_metric'):
                if ck['config']['train'].get(key) != cfg['train'].get(key):
                    raise ValueError('Resume cannot change the reviewed selection parameters.')
        model.load_state_dict(ck['model_state']); optimizer.load_state_dict(ck['optimizer_state'])
        if scaler is not None and ck.get('scaler_state'): scaler.load_state_dict(ck['scaler_state'])
        start_epoch = ck['epoch']; best = ck['best_metric']; stale = ck.get('epochs_without_improvement', 0)
        history = ck.get('history', [])
        for record in history:
            selection.update(record['epoch'], record['val'])
        if not history:
            raise ValueError('Resume requires validation history to reconstruct selection.')
        if selection.best_f1 != best:
            raise ValueError('Checkpoint selection state does not match its validation history.')
        if 'rng_state' in ck:
            import random, numpy as np
            random.setstate(ck['rng_state']['python'])
            np.random.set_state(ck['rng_state']['numpy'])
            torch.set_rng_state(ck['rng_state']['torch'])
            if device.type == 'cuda' and ck['rng_state']['cuda'] is not None:
                torch.cuda.set_rng_state_all(ck['rng_state']['cuda'])
    checkpoint = root / 'checkpoints' / cfg['train']['checkpoint']; checkpoint.parent.mkdir(parents=True, exist_ok=True)
    if args.resume:
        # A last-epoch resume may retain an older selected model. Never silently
        # lose that model just because the continuation uses a new output path.
        previous_best = checkpoint if checkpoint.exists() else root / 'checkpoints' / ck['config']['train']['checkpoint']
        if not previous_best.exists():
            raise ValueError('Resume requires the previously selected checkpoint as well as the last checkpoint.')
        selected_payload = torch.load(previous_best, map_location='cpu', weights_only=False)
        if selected_payload['epoch'] != selection.selected_epoch or selected_payload.get('selection_metric') != selection.metric:
            raise ValueError('Previously selected checkpoint does not match the reconstructed selection state.')
        if not checkpoint.exists():
            torch.save(selected_payload, checkpoint)
        del selected_payload
    history_path = root / cfg['train'].get('history_path', 'results/train_history.json'); history_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_jsonl = root / cfg['train'].get('metrics_jsonl_path', str(history_path.with_suffix('.jsonl')))
    status_path = root / cfg['train'].get('status_path', str(history_path.with_name(history_path.stem + '_status.json')))
    epoch_directory = root / cfg['train'].get('epoch_checkpoint_dir', str(checkpoint.with_name(checkpoint.stem + '_epochs')))
    checkpoint_every = int(cfg['train'].get('checkpoint_every', 0))
    if checkpoint_every < 0:
        raise ValueError('train.checkpoint_every must be nonnegative')
    monitor = cfg['train'].get('collapse_monitor', {})
    if monitor and (not isinstance(monitor, dict) or monitor.get('split', 'val') != 'val'):
        raise ValueError('collapse_monitor must be a mapping on the validation split')
    epochs = args.epochs if args.epochs > 0 else int(cfg['train']['epochs'])
    atomic_json_write(status_path, {'status': 'running', 'start_epoch': start_epoch + 1,
                                    'target_epochs': epochs, 'last_completed_epoch': start_epoch})
    print({'device': str(device), 'precision': precision, 'class_counts': counts, 'pos_weight': weight, 'selection': selection.metric})
    for ep in range(start_epoch, epochs):
        model.train(); sums = {}; count = 0; optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(tqdm(loader, desc=f'epoch {ep+1}')):
            group_start = (step // accum) * accum
            # Scale by samples, including a smaller final batch/accumulation group.
            group_samples = min(accum * bs, len(train) - group_start * bs)
            with autocast_context(device, precision):
                raw_loss, parts = batch_loss(model, batch, cfg, device)
                loss = raw_loss * len(batch) / group_samples
            if not torch.isfinite(loss): raise FloatingPointError('Non-finite training loss.')
            (scaler.scale(loss) if scaler else loss).backward()
            if (step + 1) % accum == 0 or step + 1 == len(loader):
                if scaler: scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), cfg['train']['grad_clip'], error_if_nonfinite=True)
                if scaler: scaler.step(optimizer); scaler.update()
                else: optimizer.step()
                optimizer.zero_grad(set_to_none=True)
            count += len(batch)
            for key, value in {'loss': float(raw_loss.detach()), **parts}.items(): sums[key] = sums.get(key, 0.) + value * len(batch)
        metrics = validate(model, val_loader, cfg, device, precision)
        rec = {'epoch': ep + 1, 'train': {k: v / count for k, v in sums.items()}, 'val': metrics}
        monitor_due = (monitor.get('enabled', False) and ep + 1 >= int(monitor.get('start_epoch', 1)) and
                       (ep + 1 - int(monitor.get('start_epoch', 1))) % int(monitor.get('cadence_epochs', 1)) == 0)
        if monitor_due:
            rec['rollout_monitor'] = rollout_stage_monitor(model, val, cfg, device)
        history.append(rec); print(rec)
        improved = selection.update(ep + 1, metrics)
        stale = 0 if improved else stale + 1
        best = selection.best_f1
        import random, numpy as np
        payload = {'model_state': model.state_dict(), 'optimizer_state': optimizer.state_dict(),
                   'scaler_state': scaler.state_dict() if scaler else None, 'config': cfg, 'node_dim': node_dim,
                   'epoch': ep + 1, 'best_metric': best, 'selection_metric': selection.metric, 'validation': metrics,
                   'selection_state': selection.state_dict(),
                   'rng_state': {'python': random.getstate(), 'numpy': np.random.get_state(),
                                 'torch': torch.get_rng_state(),
                                 'cuda': torch.cuda.get_rng_state_all() if device.type == 'cuda' else None},
                   'class_counts': counts, 'pos_weight': weight, 'normalization': normalization,
                   'normalization_path': str(normalization_path) if normalization else None,
                   'epochs_without_improvement': stale, 'history': history}
        if improved: atomic_torch_save(payload, checkpoint)
        atomic_torch_save(payload, checkpoint.with_name(checkpoint.stem + '_last.pt'))
        if checkpoint_every and (ep + 1) % checkpoint_every == 0:
            atomic_torch_save(payload, epoch_directory / f'epoch_{ep + 1:04d}.pt')
        atomic_json_write(history_path, history)
        append_durable_jsonl(metrics_jsonl, rec)
        if rec.get('rollout_monitor', {}).get('collapsed') and monitor.get('stop_on_collapse', False):
            atomic_json_write(status_path, {'status': 'stopped_on_first_collapse',
                                            'last_completed_epoch': ep + 1,
                                            'rollout_monitor': rec['rollout_monitor']})
            print('Stopping on first observed validation rollout collapse.'); break
        atomic_json_write(status_path, {'status': 'running', 'last_completed_epoch': ep + 1,
                                        'target_epochs': epochs, 'epochs_without_improvement': stale})
        if stale >= int(cfg['train'].get('early_stopping_patience', 10)):
            atomic_json_write(status_path, {'status': 'early_stopped', 'last_completed_epoch': ep + 1,
                                            'epochs_without_improvement': stale})
            print('Early stopping on validation checkpoint selection.'); break
    else:
        atomic_json_write(status_path, {'status': 'completed_epoch_budget', 'last_completed_epoch': epochs})
    print('Best validation checkpoint:', checkpoint)


if __name__ == '__main__':
    main()
