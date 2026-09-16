from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.data.pcap_extract import PACKET_FEATURES
from cybermind.data.temporal import make_sequences


def _frame(seconds):
    rows = []
    for second in seconds:
        row = {
            'timestamp': pd.Timestamp(second, unit='s', tz='UTC'),
            'src': '10.0.0.1', 'dst': '10.0.0.2', 'label': 'BENIGN',
            'infiltration': 0.0, 'stage': 0, 'protocol': 6, 'src_port': 1,
            'dst_port': 2, 'duration': 0.0, 'bytes_fwd': 1.0, 'bytes_bwd': 0.0,
            'packets_fwd': 1.0, 'packets_bwd': 0.0, 'mean_fwd_iat': 0.0,
            'mean_bwd_iat': 0.0,
        }
        row.update({name: 1.0 for name in PACKET_FEATURES})
        rows.append(row)
    return pd.DataFrame(rows)


def test_sequence_histories_do_not_bridge_empty_time_gaps():
    samples = make_sequences(_frame([0, 1, 100, 101]), 'gap-test',
                             window_seconds=1, stride_seconds=1, history=2)

    assert len(samples) == 2
    assert [[state.metadata['window_start'] for state in sample.states] for sample in samples] == [
        [0.0, 1.0], [100.0, 101.0]
    ]


def test_indexed_windows_preserve_overlap_boundaries():
    samples = make_sequences(_frame([0, 30, 59, 60, 89, 90]), 'overlap-test',
                             window_seconds=60, stride_seconds=30, history=2)

    assert [state.metadata['window_start'] for state in samples[0].states] == [0.0, 30.0]
    assert samples[0].states[0].metadata['window_end'] == 60.0
