"""Validation-only checkpoint selection, including the reviewed sequential rule."""
import math


class CheckpointSelection:
    def __init__(self, train_config):
        self.metric = train_config.get('selection_metric', 'val_f1')
        if self.metric not in ('val_f1', 'val_f1_stage_band'):
            raise ValueError('Unsupported checkpoint selection metric.')
        self.min_delta = train_config.get('min_delta', 0.)
        self.tolerance = None
        if self.metric == 'val_f1_stage_band':
            value = train_config.get('selection_f1_tolerance')
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('Reviewed selection requires an explicit finite F1 tolerance in [0,1].')
            if train_config.get('selection_stage_metric') != 'stage':
                raise ValueError('Reviewed tie-breaker must be validation stage cross-entropy (stage).')
            if self.min_delta != 0:
                raise ValueError('Reviewed sequential rule requires min_delta=0.')
            self.tolerance = float(value)
        self.best_f1 = -1.
        self.best_stage_ce = float('inf')
        self.selected_epoch = None

    def update(self, epoch, metrics):
        f1 = metrics['f1']
        if not math.isfinite(f1) or not 0 <= f1 <= 1:
            raise ValueError('Validation F1 must be finite and in [0,1].')
        if self.metric == 'val_f1':
            improved = f1 > self.best_f1 + self.min_delta
            if improved:
                self.best_f1, self.selected_epoch = f1, epoch
            return improved
        stage_ce = metrics['stage']
        if not math.isfinite(stage_ce) or stage_ce < 0:
            raise ValueError('Validation stage cross-entropy must be finite and nonnegative.')
        # Literal reviewer pseudocode: do not silently replace with a global-max
        # band, retroactive ranking, or test-set diversity selection.
        if f1 > self.best_f1 + self.tolerance:
            self.best_f1, self.best_stage_ce, self.selected_epoch = f1, stage_ce, epoch
            return True
        elif f1 >= self.best_f1 - self.tolerance:
            if stage_ce < self.best_stage_ce:
                self.best_stage_ce, self.selected_epoch = stage_ce, epoch
                self.best_f1 = max(self.best_f1, f1)
                return True
        return False

    def state_dict(self):
        return dict(metric=self.metric, tolerance=self.tolerance, best_f1=self.best_f1,
                    best_stage_ce=self.best_stage_ce if self.metric != 'val_f1' else None,
                    selected_epoch=self.selected_epoch)
