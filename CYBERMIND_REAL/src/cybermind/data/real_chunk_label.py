"""Pinned corrected and original-schedule labels for the reviewed real chunk."""
from __future__ import annotations

import numpy as np
import pandas as pd

CORRECTED_SOURCE = 'Distrinet CNS2022 corrected CSE-CIC-IDS2018 rules, commit f0ce502818e59e6cd062720ab2286c5ff6f2bdec'
ORIGINAL_SOURCE = 'UNB CSE-CIC-IDS2018 Table 2 schedule, retrieved 2026-09-16'
LABEL_METHOD = 'inclusive UTC session_start; zero tolerance; directional endpoint semantics'

DROPBOX = {'162.125.3.1', '162.125.3.5', '162.125.3.6', '162.125.248.1', '162.125.18.133'}
DROPBOX_AUX = {'104.16.100.29', '13.32.168.125', '52.85.112.72'}
FEB28_DROPBOX_AUX = {
    '104.16.100.29', '104.16.99.29', '52.84.128.3',
    '52.85.101.236', '52.85.131.81', '52.85.95.206',
}
FEB28_NMAP_TARGETS = {
    '172.31.69.1', '172.31.69.4', '172.31.69.5', '172.31.69.6',
    '172.31.69.7', '172.31.69.8', '172.31.69.9', '172.31.69.10',
    '172.31.69.11', '172.31.69.12', '172.31.69.13', '172.31.69.14',
    '172.31.69.15', '172.31.69.16', '172.31.69.17', '172.31.69.18',
    '172.31.69.19', '172.31.69.20', '172.31.69.21', '172.31.69.22',
    '172.31.69.23',
}
NMAP_TARGETS = {
    '172.31.69.1', '172.31.69.11', '172.31.69.12', '172.31.69.16',
    '172.31.69.8', '172.31.69.9', '172.31.69.10', '172.31.69.14',
    '172.31.69.4', '172.31.69.5', '172.31.69.6', '172.31.69.17',
    '172.31.69.20', '172.31.69.23', '172.31.69.24', '172.31.69.19',
    '172.31.69.7', '172.31.69.15', '172.31.69.18', '172.31.69.22',
    '172.31.69.21',
}
BOT_VICTIMS = {
    '172.31.69.23', '172.31.69.17', '172.31.69.14', '172.31.69.12',
    '172.31.69.10', '172.31.69.8', '172.31.69.6', '172.31.69.26',
    '172.31.69.29', '172.31.69.30',
}


def _seconds(frame: pd.DataFrame) -> pd.Series:
    value = pd.to_datetime(frame['session_start'], format='ISO8601', utc=True, errors='raise')
    # Do not assume pandas' internal datetime resolution (ns vs us).
    return (value - pd.Timestamp(0, tz='UTC')).dt.total_seconds()


def _window(seconds, start, end):
    return seconds.ge(start) & seconds.le(end)


def _windows(seconds, ranges):
    mask = pd.Series(False, index=seconds.index)
    for start, end in ranges:
        mask |= _window(seconds, start, end)
    return mask


def _assign(result, mask, label, category, rule_id):
    result.loc[mask, 'label'] = label
    result.loc[mask, 'attempted_category'] = category
    result.loc[mask, 'corrected_rule_id'] = rule_id


def corrected_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the pinned notebook rules in notebook order.

    The approved R0 representation is directional rather than biflow. Rules that
    require reverse-direction aggregates/RST flags remain broad-label matches and
    are explicitly marked unresolved; their missing predicates are never guessed.
    """
    required = {'session_start', 'src', 'dst', 'src_port', 'dst_port', 'payload_size_max', 'capture_date'}
    missing = required - set(frame)
    if missing:
        raise ValueError(f'Missing corrected-label inputs: {sorted(missing)}')
    seconds = _seconds(frame)
    result = pd.DataFrame(index=frame.index)
    result['label'] = 'BENIGN'
    result['attempted_category'] = -1
    result['corrected_rule_id'] = 'CORRECTED_REST_BENIGN'
    result['corrected_refinement_status'] = 'complete'
    src, dst = frame.src.astype(str), frame.dst.astype(str)
    sport = pd.to_numeric(frame.src_port, errors='raise')
    dport = pd.to_numeric(frame.dst_port, errors='raise')
    payload_zero = pd.to_numeric(frame.payload_size_max, errors='raise').eq(0)

    feb = frame.capture_date.astype(str).eq('2018-02-14')
    _assign(result, feb & src.eq('18.221.219.4') & dst.eq('172.31.69.25')
            & _window(seconds, 1518618806, 1518624631),
            'FTP-BruteForce - Attempted', 1, 'D_FTP_ATTEMPTED_C1')
    _assign(result, feb & src.eq('13.58.98.64') & dst.eq('172.31.69.25') & dport.eq(21)
            & _window(seconds, 1518631281.199541, 1518631281.502585),
            'FTP-BruteForce - Attempted', 4, 'D_FTP_ATTEMPTED_C4')
    ssh = (feb & src.eq('13.58.98.64') & dst.eq('172.31.69.25') & dport.eq(22)
           & _window(seconds, 1518631310, 1518636750))
    _assign(result, ssh, 'SSH-BruteForce', -1, 'D_SSH')
    _assign(result, ssh & payload_zero, 'SSH-BruteForce - Attempted', 0, 'D_SSH_ATTEMPTED_C0')

    feb28 = frame.capture_date.astype(str).eq('2018-02-28')
    feb28_drop_windows = ((1519828404, 1519829172), (1519839771, 1519839824))
    feb28_drop_base = feb28 & src.eq('172.31.69.24') & _windows(seconds, feb28_drop_windows)
    feb28_drop = feb28_drop_base & dst.isin(DROPBOX)
    _assign(result, feb28_drop, 'Infiltration - Dropbox Download', -1, 'D_0228_INF_DROPBOX')
    _assign(result, feb28_drop & payload_zero,
            'Infiltration - Dropbox Download - Attempted', 0,
            'D_0228_INF_DROPBOX_ATTEMPTED_C0')
    _assign(result, feb28_drop_base & dst.isin(FEB28_DROPBOX_AUX),
            'Infiltration - Dropbox Download - Attempted', 4,
            'D_0228_INF_DROPBOX_ATTEMPTED_C4')
    feb28_comm_windows = ((1519829140, 1519834135), (1519839839, 1519843200))
    feb28_comm = (feb28 & src.eq('172.31.69.24') & dst.eq('13.58.225.34')
                  & _windows(seconds, feb28_comm_windows))
    _assign(result, feb28_comm, 'Infiltration - Communication Victim Attacker', -1,
            'D_0228_INF_COMM')
    _assign(result, feb28_comm & payload_zero,
            'Infiltration - Communication Victim Attacker - Attempted', 0,
            'D_0228_INF_COMM_ATTEMPTED_C0')
    feb28_nmap = (feb28 & src.eq('172.31.69.24') & dst.isin(FEB28_NMAP_TARGETS) & ~sport.eq(68)
                  & _window(seconds, 1519829182, 1519843140.746247))
    _assign(result, feb28_nmap, 'Infiltration - NMAP Portscan', -1, 'D_0228_INF_NMAP')

    mar1 = frame.capture_date.astype(str).eq('2018-03-01')
    drop_windows = ((1519912390, 1519912760), (1519913032, 1519918454))
    drop_base = mar1 & src.eq('172.31.69.13') & _windows(seconds, drop_windows)
    drop = drop_base & dst.isin(DROPBOX)
    _assign(result, drop, 'Infiltration - Dropbox Download', -1, 'D_INF_DROPBOX')
    _assign(result, drop & payload_zero, 'Infiltration - Dropbox Download - Attempted', 0,
            'D_INF_DROPBOX_ATTEMPTED_C0')
    _assign(result, drop_base & dst.isin(DROPBOX_AUX),
            'Infiltration - Dropbox Download - Attempted', 4, 'D_INF_DROPBOX_ATTEMPTED_C4')
    comm_windows = ((1519912674, 1519912745), (1519913075, 1519928245),
                    (1519928295, 1519933041))
    comm = (mar1 & src.eq('172.31.69.13') & dst.eq('13.58.225.34')
            & _windows(seconds, comm_windows))
    _assign(result, comm, 'Infiltration - Communication Victim Attacker', -1, 'D_INF_COMM')
    _assign(result, comm & payload_zero,
            'Infiltration - Communication Victim Attacker - Attempted', 0,
            'D_INF_COMM_ATTEMPTED_C0')
    nmap = (mar1 & src.eq('172.31.69.13') & dst.isin(NMAP_TARGETS) & ~sport.eq(68)
            & _window(seconds, 1519913388.354333, 1519933092.182726))
    _assign(result, nmap, 'Infiltration - NMAP Portscan', -1, 'D_INF_NMAP')

    mar2 = frame.capture_date.astype(str).eq('2018-03-02')
    master = '18.219.211.138'
    bot = mar2 & (src.eq(master) | dst.eq(master)) & _window(seconds, 1520000008, 1520020492)
    _assign(result, bot, 'Botnet Ares', -1, 'D_BOT_ARES')
    # The pinned notebook next applies two biflow-only attempted refinements:
    # category 2 requires Bwd RST Flags, and category 0 requires both forward and
    # backward payload totals. Neither predicate exists in the approved R0
    # directional schema, so candidates retain the broad label and are flagged.
    c2_candidate = (bot & dst.eq(master) & ~payload_zero
                    & _window(seconds, 1520020424, 1520020492))
    c0_candidate = bot & payload_zero
    result.loc[c2_candidate, 'corrected_refinement_status'] = 'unresolved_missing_bwd_rst_flags'
    result.loc[c0_candidate, 'corrected_refinement_status'] = 'unresolved_missing_reverse_payload_total'

    return result


def original_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply UNB Table 2 literally: attacker→victim endpoints and UTC+4 times."""
    seconds = _seconds(frame)
    result = pd.DataFrame(index=frame.index)
    result['original_cic_label'] = 'BENIGN'
    result['original_rule_id'] = 'ORIGINAL_REST_BENIGN'
    src, dst = frame.src.astype(str), frame.dst.astype(str)
    date = frame.capture_date.astype(str)

    def assign(mask, label, rule):
        result.loc[mask, 'original_cic_label'] = label
        result.loc[mask, 'original_rule_id'] = rule

    feb = date.eq('2018-02-14')
    assign(feb & src.isin({'172.31.70.4', '18.221.219.4'})
           & dst.isin({'172.31.69.25', '18.217.21.148'})
           & _window(seconds, 1518618720, 1518624599.999999), 'FTP-BruteForce', 'O_FTP_TABLE2')
    assign(feb & src.isin({'172.31.70.6', '13.58.98.64'})
           & dst.isin({'172.31.69.25', '18.217.21.148'})
           & _window(seconds, 1518631260, 1518636719.999999), 'SSH-Bruteforce', 'O_SSH_TABLE2')

    feb28 = date.eq('2018-02-28')
    original_feb28_windows = ((1519829400, 1519833899.999999),
                              (1519839720, 1519843199.999999))
    assign(feb28 & src.eq('13.58.225.34')
           & dst.isin({'172.31.69.24', '18.221.148.137'})
           & _windows(seconds, original_feb28_windows), 'Infiltration', 'O_0228_INF_TABLE2')

    mar1 = date.eq('2018-03-01')
    original_inf_windows = ((1519912620, 1519916159.999999),
                            (1519927200, 1519933079.999999))
    assign(mar1 & src.eq('13.58.225.34')
           & dst.isin({'172.31.69.13', '18.216.254.154'})
           & _windows(seconds, original_inf_windows), 'Infiltration', 'O_INF_TABLE2')

    mar2 = date.eq('2018-03-02')
    original_bot_windows = ((1519999860, 1520004899.999999),
                            (1520015040, 1520020559.999999))
    assign(mar2 & src.eq('18.219.211.138') & dst.isin(BOT_VICTIMS)
           & _windows(seconds, original_bot_windows), 'Bot', 'O_BOT_TABLE2')
    return result


def stage_for_label(labels: pd.Series) -> pd.Series:
    result = pd.Series(6, index=labels.index, dtype='int64')
    result.loc[labels.eq('BENIGN')] = 0
    result.loc[labels.str.contains('NMAP Portscan', regex=False)] = 1
    result.loc[labels.str.contains('FTP-BruteForce', regex=False)
               | labels.str.contains('SSH-BruteForce', regex=False)
               | labels.str.contains('Dropbox Download', regex=False)] = 2
    result.loc[labels.str.contains('Botnet Ares', regex=False)] = 4
    return result
