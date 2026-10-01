#!/usr/bin/env python3
"""Offline analyst console with capture replay and encrypted local cases."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile

import streamlit as st
import torch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.analyst.case_qa import answer_case_question, compare_case_reports
from cybermind.analyst.ui_theme import render_header
from cybermind.analyst.case_security import (
    account_path, create_account, decrypt_report, encrypt_report, verify_account)
from cybermind.analyst.view import (
    load_case, load_uploaded_session, select_uploaded_sequence, forecast_rows,
    network_dot, compare_isolations, input_shift_summary)
from cybermind.analyst.stage_evidence import (
    analyze_stage_evidence, annotate_forecast_stage_coverage)

st.set_page_config(page_title='CYBERMIND Analyst Console', layout='wide')
render_header(st)

account = account_path()
if not account.is_file():
    st.info('Create a local analyst password to open and seal encrypted case reports.')
    with st.form('create_local_account'):
        first = st.text_input('New local password (at least 12 characters)', type='password')
        second = st.text_input('Confirm password', type='password')
        submitted = st.form_submit_button('Create local account')
    if submitted:
        try:
            if first != second:
                raise ValueError('Passwords do not match.')
            create_account(account, first)
            st.session_state['authenticated'] = True
            st.rerun()
        except (ValueError, FileExistsError, OSError) as error:
            st.error(str(error))
    st.stop()

if not st.session_state.get('authenticated', False):
    with st.form('local_login'):
        password = st.text_input('Local analyst password', type='password')
        submitted = st.form_submit_button('Unlock analyst console')
    if submitted:
        if verify_account(account, password):
            st.session_state['authenticated'] = True
            st.rerun()
        st.error('Login failed.')
    st.stop()

if st.sidebar.button('Log out'):
    st.session_state['authenticated'] = False
    st.session_state.pop('opened_report', None)
    st.session_state.pop('sealed_case', None)
    st.rerun()

workflow = st.sidebar.radio('Case workflow', ('Analyze traffic', 'Open encrypted report'))
if workflow == 'Open encrypted report':
    sealed = st.file_uploader('Encrypted CYBERMIND case', type=['cmcase'])
    comparison_file = st.file_uploader(
        'Optional second case for comparison', type=['cmcase'], key='comparison_case_file')
    password = st.text_input('Confirm local password to decrypt', type='password')
    sealed_id = ':'.join(
        hashlib.sha256(item.getvalue()).hexdigest() if item else ''
        for item in (sealed, comparison_file))
    if st.session_state.get('sealed_id') != sealed_id:
        st.session_state['sealed_id'] = sealed_id
        st.session_state.pop('opened_report', None)
        st.session_state.pop('comparison_report', None)
    if st.button('Open case', disabled=sealed is None):
        st.session_state.pop('opened_report', None)
        st.session_state.pop('comparison_report', None)
        if not verify_account(account, password):
            st.error('Login verification failed.')
        else:
            try:
                opened = decrypt_report(sealed.getvalue(), password)
                comparison = (decrypt_report(comparison_file.getvalue(), password)
                              if comparison_file else None)
                st.session_state['opened_report'] = opened
                st.session_state['comparison_report'] = comparison
            except ValueError as error:
                st.error(str(error))
    report = st.session_state.get('opened_report')
    if report:
        st.subheader('Opened case')
        st.json(report)
        comparison = st.session_state.get('comparison_report')
        if comparison:
            st.subheader('Saved-case comparison')
            st.dataframe(compare_case_reports(report, comparison), hide_index=True)
            st.caption('Side-by-side saved evidence only; neither case is re-scored or treated as ground truth.')
        question = st.text_input('Ask about this case', key='opened_case_question')
        if question:
            answer = answer_case_question(question, report)
            st.write(answer['answer'])
            st.caption('Evidence: ' + ', '.join(answer['evidence']) if answer['evidence'] else 'No case evidence matched.')
    st.stop()

@st.cache_resource(show_spinner='Parsing capture and building observed histories…')
def cached_uploaded_session(checkpoint_path, checkpoint_stamp, name, payload):
    suffix = Path(name).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(payload)
        temporary_path = Path(handle.name)
    try:
        session = load_uploaded_session(checkpoint_path, temporary_path)
        session[3]['dataset'] = name
        session[3]['uploaded_filename'] = name
        return session
    finally:
        temporary_path.unlink(missing_ok=True)

path = st.sidebar.text_input(
    'Local trusted checkpoint',
    os.environ.get('CYBERMIND_CHECKPOINT', str(ROOT / 'checkpoints/final_grouped/best.pt')))
source_mode = st.sidebar.radio('Input source', ('Upload PCAP/CSV', 'Prepared test sequence'))
uploaded = st.sidebar.file_uploader(
    'Offline network capture', type=['pcap', 'pcapng', 'csv']) if source_mode == 'Upload PCAP/CSV' else None
index = int(st.sidebar.number_input(
    'Test sequence index', min_value=0, value=0, step=1)) if source_mode == 'Prepared test sequence' else 0
st.sidebar.caption('Load only trusted local checkpoints. PyTorch checkpoint files can execute serialized objects.')
if not Path(path).is_file():
    st.info('Choose a local checkpoint.')
    st.stop()
try:
    if source_mode == 'Upload PCAP/CSV':
        if uploaded is None:
            st.info('Upload a local PCAP, PCAPNG, or packet-complete CSV. Processing remains offline.')
            st.stop()
        session = cached_uploaded_session(
            path, Path(path).stat().st_mtime_ns, uploaded.name, uploaded.getvalue())
        count = len(session[2])
        index = st.sidebar.slider(
            'Replay observed window', 0, count - 1, count - 1,
            key=f"replay_{hashlib.sha256(uploaded.getvalue()).hexdigest()[:12]}")
        model, cfg, sample, lineage, count = select_uploaded_sequence(session, index)
        st.sidebar.caption('Each replay position forecasts only from traffic observed up to that window.')
    else:
        model, cfg, sample, lineage, count = load_case(path, ROOT, index)
except Exception as error:
    st.error(f'Cannot load this case: {error}')
    st.stop()

st.sidebar.write(f'{count} usable sequences available')
k = int(cfg['eval']['rollout_steps'])
draws = int(cfg['eval'].get('n_rollouts', 16))
seed = int(cfg['eval'].get('rollout_seed', 0))
observed = sample.states if source_mode == 'Upload PCAP/CSV' else sample.states[:-1]
with torch.no_grad():
    out = model.forecast(observed, k, n_rollouts=draws, seed=seed, explain=False)
rows = forecast_rows(out, model, observed[-1].timestamp, sample.window_seconds)
checkpoint_payload = torch.load(path, map_location='cpu', weights_only=False)
stage_evidence = analyze_stage_evidence(
    observed, checkpoint_payload.get('normalization'), rows[-1]['risk'])
rows = annotate_forecast_stage_coverage(rows, stage_evidence)
case_key = (lineage['checkpoint_sha256'], lineage['dataset_sha256'], source_mode, index, k, draws, seed)
if st.session_state.get('case_key') != case_key:
    st.session_state['case_key'] = case_key
    st.session_state['interventions'] = []
    st.session_state['explanation'] = None
    st.session_state.pop('sealed_case', None)

flow_rows = sample.metadata.get('observed_flow_rows', [])
flagged_count = sum(bool(flow.get('review_flag')) for flow in flow_rows)
shift = input_shift_summary(observed)
st.markdown('<div class="cm-eyebrow">Active investigation</div>', unsafe_allow_html=True)
st.caption(f"Source: {lineage.get('dataset', 'unavailable')} · Checkpoint epoch {lineage.get('checkpoint_epoch', 'unknown')} · Replay window {index + 1} of {count}")

m1, m2, m3, m4 = st.columns(4)
m1.metric('Final-horizon risk', f"{rows[-1]['risk']:.1%}")
m2.metric('Observed hosts', len(observed[-1].node_ids))
m3.metric('Observed links', observed[-1].edge_index.shape[1])
m4.metric('Review-flagged flows', flagged_count if source_mode == 'Upload PCAP/CSV' else '—')

overview_tab, traffic_tab, evidence_tab, actions_tab, reports_tab = st.tabs(
    ['◉  Overview', '≋  Traffic', '◇  Evidence', '⊞  Actions', '▣  Case file'])

with overview_tab:
    st.markdown('### Forecast trajectory')
    st.markdown('<div class="cm-section-note">Four future windows from the selected observed history. Risk scores are predictions, not observed outcomes.</div>', unsafe_allow_html=True)
    chart_col, graph_col = st.columns([1.25, 1])
    with chart_col:
        st.line_chart(
            pd.DataFrame([{'window': 'Now' if row['step'] == 0 else f"+{row['step']}",
                           'risk': row['risk']} for row in rows]).set_index('window'),
            height=290)
        st.dataframe(
            rows, hide_index=True, use_container_width=True,
            column_order=['horizon', 'risk', 'reported_stage', 'model_stage',
                          'evidence_basis', 'transition_legal'],
            column_config={'risk': st.column_config.NumberColumn('Risk', format='%.3f')})
        st.caption('Reported stage may be a telemetry-rule annotation or abstention. It is not attack ground truth.')
    with graph_col:
        st.markdown('### Latest observed topology')
        effects = {r['host_index']: r['risk_reduction']
                   for r in st.session_state['interventions'] if r['host_index'] is not None}
        st.graphviz_chart(network_dot(observed[-1], effects), use_container_width=True)
        st.caption('Observed connectivity only; display capped at 80 hosts. Highlighting shows model-space sensitivity.')
    if source_mode == 'Upload PCAP/CSV':
        st.markdown('### Capture replay')
        observed_time = pd.Timestamp(
            observed[-1].metadata['window_start'], unit='s', tz='UTC').isoformat()
        st.caption(f"Observed history {index + 1} of {count} · {observed_time}. Use the sidebar slider to inspect an earlier point.")
        replay_key = (lineage['checkpoint_sha256'], lineage['dataset_sha256'])
        if st.session_state.get('replay_key') != replay_key:
            st.session_state['replay_key'] = replay_key
            st.session_state['replay_risks'] = {}
        st.session_state['replay_risks'][index] = rows[-1]['risk']
        replay_points = pd.DataFrame(
            [{'observed_window': position + 1, 'final_risk': risk}
             for position, risk in sorted(st.session_state['replay_risks'].items())])
        st.line_chart(replay_points.set_index('observed_window'), height=170)
        st.caption('Only replay positions visited in this session appear above.')

with traffic_tab:
    st.markdown('### Observed traffic')
    if source_mode == 'Upload PCAP/CSV':
        st.caption(f'{len(flow_rows)} flows shown from the selected observed window, capped at 200.')
        if flow_rows:
            st.dataframe(flow_rows, hide_index=True, use_container_width=True)
        else:
            st.info('No flow rows are available for this window.')
        st.caption('Review flags are packet-telemetry cues, not per-flow model scores or attack labels.')
    else:
        st.info('Flow-level triage is available for uploaded captures.')
    st.markdown('### Input feature-range check')
    if shift['available']:
        st.write(f"{shift['exceeded_values']} of {shift['total_values']} normalized values exceed ±{shift['threshold_std']:.0f} training standard deviations.")
        if shift['exceeded_values']:
            st.warning('Some values fall far outside the training-normalized range. Review this input before trusting the forecast.')
            st.dataframe(shift['top_features'], hide_index=True, use_container_width=True)
        st.caption(shift['limitation'])
    else:
        st.caption(shift['reason'])

with actions_tab:
    st.markdown('### Host-isolation sensitivity')
    st.caption('Compare the same observed history under an edge-cut simulation. No network action is executed.')
    hosts = st.multiselect('Hosts to simulate', range(len(observed[-1].node_ids)),
                           format_func=lambda i: observed[-1].node_ids[i])
    if st.button('Run simulations', disabled=not hosts, type='primary'):
        with st.spinner('Comparing matched random draws…'):
            st.session_state['interventions'] = compare_isolations(
                model, observed, hosts, k, draws, seed)
    comparisons = st.session_state['interventions']
    if comparisons:
        st.dataframe(comparisons, hide_index=True, use_container_width=True)
        best = comparisons[0]
        if best['risk_reduction'] > 0:
            st.success(f"Lowest simulated risk: {best['host']} ({best['future_risk']:.1%}). Analyst review required.")
        else:
            st.info('No simulated isolation reduces model risk.')
    st.caption('This tests model sensitivity, not measured containment effectiveness or causality.')

with evidence_tab:
    st.markdown('### Stage evidence')
    st.dataframe(stage_evidence, hide_index=True, use_container_width=True,
                 column_order=['stage', 'status', 'basis', 'hosts', 'indicators', 'limitation'])
    st.caption('Rules for stages 3–5 do not change model risk or count as trained stage accuracy.')
    st.markdown('### Model explanation')
    if st.button('Compute feature sensitivity'):
        with st.spinner('Computing feature sensitivity and temporal attention…'):
            with torch.no_grad():
                st.session_state['explanation'] = model.forecast(
                    observed, k, n_rollouts=draws, seed=seed)['explanation']
    if st.session_state['explanation'] is not None:
        st.json(st.session_state['explanation'])
    else:
        st.caption('Run the explanation to inspect model sensitivity for this selected window.')
    st.caption('Attention and perturbations are not causal explanations.')

report = {
    'format': 'CYBERMIND-REPORT-v1', 'lineage': lineage, 'forecast': rows,
    'observed_flows': flow_rows, 'stage_evidence': stage_evidence, 'input_shift': shift,
    'interventions': st.session_state['interventions'],
    'explanation': st.session_state['explanation'],
    'seed': seed, 'n_rollouts': draws,
    'interpretation': 'Model-based forecast for analyst review; no causal or autonomous-response claim.',
}
report = json.loads(json.dumps(report, default=str, allow_nan=False))

with evidence_tab:
    st.markdown('### Ask this case')
    question = st.text_input(
        'Question about risk, stages, flows, host changes, or provenance',
        placeholder='Why was this window flagged?')
    if question:
        answer = answer_case_question(question, report, observed)
        st.info(answer['answer'])
        st.caption('Evidence: ' + ', '.join(answer['evidence'])
                   if answer['evidence'] else 'No case evidence matched.')
    st.caption('Offline, deterministic evidence search. No cloud model or invented attack narrative.')

with reports_tab:
    st.markdown('### Secure case export')
    st.caption('Preserve the selected forecast and its evidence as an encrypted, password-protected local case file.')
    with st.expander('Case provenance', expanded=False):
        st.json(lineage)
        st.caption('Uploaded captures remain unlabeled; replay never inspects later windows.')
    export_password = st.text_input('Confirm local password to seal this case', type='password')
    if st.button('Create encrypted case report', type='primary'):
        if not verify_account(account, export_password):
            st.error('Login verification failed.')
        else:
            try:
                st.session_state['sealed_case'] = encrypt_report(report, export_password)
            except ValueError as error:
                st.error(str(error))
    if st.session_state.get('sealed_case'):
        st.download_button('Download encrypted .cmcase', st.session_state['sealed_case'],
                           file_name=f'cybermind_case_{index}.cmcase',
                           mime='application/octet-stream')
