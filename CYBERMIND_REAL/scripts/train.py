#!/usr/bin/env python3
"""Joint training with train-only class weights and validation F1 selection."""
from pathlib import Path
import argparse
import json
import sys
from contextlib import nullcontext
from dataclasses import replace
import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader
from tqdm import tqdm
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.data.dataset import GraphSequenceDataset, collate_identity
from cybermind.models.world_model import WorldModel
from cybermind.losses import (gaussian_transition_loss, infiltration_loss, stage_loss,
                              binary_brier, graph_consistency_loss)
from cybermind.utils.config import load_config
from cybermind.utils.repro import seed_everything


def training_class_weight(dataset):
    # Count exactly the target-window occurrences consumed by the training loss.
    labels = [float(s.y_infiltration) for sample in dataset for s in sample.states[1:]]
    if not labels or any(y not in (0., 1.) for y in labels):
        raise ValueError('Training infiltration labels must be binary and nonempty.')
    positive = int(sum(labels)); negative = len(labels) - positive
    if not positive or not negative:
        raise ValueError('Training split must contain benign and infiltration target windows.')
    return negative / positive, {'positive': positive, 'negative': negative}


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
    l_stage = stage_loss(stage_logits.float(), stage_labels)
    l_consistency = graph_consistency_loss(z)
    components = {'transition': l_trans, 'infiltration': l_infil, 'stage': l_stage,
                  'calibration': l_brier, 'graph_consistency': l_consistency}
    total = sum(cfg['loss'].get(name, .1 if name == 'graph_consistency' else 0.) * value
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True); parser.add_argument('--resume')
    parser.add_argument('--epochs', type=int, default=0)
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto')
    args = parser.parse_args(); cfg = load_config(args.config); seed_everything(cfg.get('seed', 42))
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
    if cfg['train'].get('selection_metric', 'val_f1') != 'val_f1':
        raise ValueError('Supported checkpoint selection metric is val_f1.')
    processed = root / cfg['data']['processed_dir']
    train = GraphSequenceDataset(processed / 'train.pt'); val = GraphSequenceDataset(processed / 'val.pt')
    if not len(train) or not len(val):
        raise ValueError('Training and held-out validation must both be nonempty.')
    assert_split_disjoint(train, val)
    weight, counts = training_class_weight(train); cfg['loss']['pos_weight'] = weight
    normalization_path = processed / 'normalization.json'
    normalization = json.loads(normalization_path.read_text()) if normalization_path.exists() else None
    if cfg['data'].get('require_normalization', False) and normalization is None:
        raise ValueError('Training-only normalization.json is required; run prepare_data in Phase 2.')
    validate_training_provenance(processed, cfg, (train, val), normalization)
    node_dim = train[0].states[0].x.size(1)
    model_cfg = {k: cfg['model'][k] for k in ('graph_hidden', 'graph_out', 'temporal_dim', 'nhead', 'temporal_layers', 'num_stages', 'dropout')}
    model_cfg['graph_heads'] = cfg['model'].get('graph_heads', 8)
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
        if ck.get('selection_metric') != 'val_f1':
            raise ValueError('Resume requires a checkpoint selected by validation F1 under the new pipeline.')
        model.load_state_dict(ck['model_state']); optimizer.load_state_dict(ck['optimizer_state'])
        if scaler is not None and ck.get('scaler_state'): scaler.load_state_dict(ck['scaler_state'])
        start_epoch = ck['epoch']; best = ck['best_metric']; stale = ck.get('epochs_without_improvement', 0)
        history = ck.get('history', [])
    checkpoint = root / 'checkpoints' / cfg['train']['checkpoint']; checkpoint.parent.mkdir(parents=True, exist_ok=True)
    history_path = root / cfg['train'].get('history_path', 'results/train_history.json'); history_path.parent.mkdir(parents=True, exist_ok=True)
    epochs = args.epochs if args.epochs > 0 else int(cfg['train']['epochs'])
    print({'device': str(device), 'precision': precision, 'class_counts': counts, 'pos_weight': weight, 'selection': 'val_f1'})
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
        history.append(rec); print(rec)
        improved = metrics['f1'] > best + cfg['train'].get('min_delta', 0.)
        stale = 0 if improved else stale + 1
        if improved: best = metrics['f1']
        payload = {'model_state': model.state_dict(), 'optimizer_state': optimizer.state_dict(),
                   'scaler_state': scaler.state_dict() if scaler else None, 'config': cfg, 'node_dim': node_dim,
                   'epoch': ep + 1, 'best_metric': best, 'selection_metric': 'val_f1', 'validation': metrics,
                   'class_counts': counts, 'pos_weight': weight, 'normalization': normalization,
                   'normalization_path': str(normalization_path) if normalization else None,
                   'epochs_without_improvement': stale, 'history': history}
        if improved: torch.save(payload, checkpoint)
        torch.save(payload, checkpoint.with_name(checkpoint.stem + '_last.pt'))
        history_path.write_text(json.dumps(history, indent=2))
        if stale >= int(cfg['train'].get('early_stopping_patience', 10)):
            print('Early stopping on validation F1.'); break
    print('Best validation checkpoint:', checkpoint)


if __name__ == '__main__':
    main()
