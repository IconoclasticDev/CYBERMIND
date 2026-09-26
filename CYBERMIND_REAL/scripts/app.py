#!/usr/bin/env python3
"""Offline analyst console; inference always uses an explicitly selected local checkpoint."""
from pathlib import Path
import os, sys, json, tempfile
import torch
import streamlit as st
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.analyst.view import (load_case, load_uploaded_case, forecast_rows,
                                    network_dot, compare_isolations)

st.set_page_config(page_title='CYBERMIND Analyst Console', layout='wide')
st.title('CYBERMIND Analyst Console')
st.caption('Offline research interface. Forecasts are model outputs for analyst review; they do not execute network actions or establish causal effects.')
path = st.sidebar.text_input('Local trusted checkpoint', os.environ.get('CYBERMIND_CHECKPOINT', str(ROOT / 'checkpoints/best_gb10.pt')))
source_mode = st.sidebar.radio('Input source', ('Upload PCAP/CSV', 'Prepared test sequence'))
uploaded = st.sidebar.file_uploader('Offline network capture', type=['pcap', 'pcapng', 'csv']) if source_mode == 'Upload PCAP/CSV' else None
index = int(st.sidebar.number_input('Test sequence index', min_value=0, value=0, step=1)) if source_mode == 'Prepared test sequence' else 0
st.sidebar.caption('Only load trusted local checkpoints. PyTorch checkpoint loading executes serialized Python objects.')
if not Path(path).is_file():
    st.info('Choose a local checkpoint to inspect. Synthetic verification can run on CPU; GPU training is not required for this console.')
    st.stop()
try:
    if source_mode == 'Upload PCAP/CSV':
        if uploaded is None:
            st.info('Upload a local PCAP, PCAPNG, or CSV. Processing and inference remain offline.')
            st.stop()
        suffix = Path(uploaded.name).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(uploaded.getvalue())
            temporary_path = Path(handle.name)
        try:
            model, cfg, sample, lineage, count = load_uploaded_case(path, temporary_path)
            lineage['uploaded_filename'] = uploaded.name
            lineage['dataset'] = uploaded.name
        finally:
            temporary_path.unlink(missing_ok=True)
    else:
        model, cfg, sample, lineage, count = load_case(path, ROOT, index)
except Exception as error:
    st.error(f'Cannot load this case: {error}')
    st.stop()
st.sidebar.write(f'{count} usable sequences available')
k = int(cfg['eval']['rollout_steps']); draws = int(cfg['eval'].get('n_rollouts', 16)); seed = int(cfg['eval'].get('rollout_seed', 0))
observed = sample.states if source_mode == 'Upload PCAP/CSV' else sample.states[:-1]
with torch.no_grad():
    out = model.forecast(observed, k, n_rollouts=draws, seed=seed, explain=False)
rows = forecast_rows(out, model, observed[-1].timestamp, sample.window_seconds)
case_key = (lineage['checkpoint_sha256'], lineage['dataset_sha256'], source_mode, index, k, draws, seed)
if st.session_state.get('case_key') != case_key:
    st.session_state['case_key'] = case_key
    st.session_state['interventions'] = []
    st.session_state['explanation'] = None
left, center, right = st.columns([1, 1.5, 1])
with left:
    st.subheader('Observed network')
    effects = {r['host_index']: r['risk_reduction'] for r in st.session_state['interventions'] if r['host_index'] is not None}
    graph_slot = st.empty()
    st.caption(f'{len(observed[-1].node_ids)} hosts / {observed[-1].edge_index.shape[1]} edges. Display capped at 80 hosts. Edges show observed connectivity, not inferred attack paths.')
with center:
    st.subheader('Future forecast')
    st.metric('Final model risk', f"{rows[-1]['risk']:.1%}")
    st.line_chart({'risk': [r['risk'] for r in rows]}, height=180)
    st.dataframe(rows, hide_index=True, column_order=['horizon', 'stage', 'risk', 'rollout_std', 'transition_legal'],
                 column_config={'risk': st.column_config.NumberColumn('Risk', format='%.3f'),
                                'rollout_std': st.column_config.NumberColumn('Rollout SD', format='%.3f')})
    st.caption('Step 0 is the encoded observed state; steps 1–4 are future windows when the configured horizon is four. Rollout SD measures stochastic dispersion, not calibrated confidence. Stage names are coarse research mappings, not attack ground truth.')
    illegal = sum(r['transition_legal'] is False for r in rows)
    st.write(f"Decoder: {out['stage_decoding']} · Illegal transitions: {illegal} · Draws: {draws} · Seed: {seed}")
with right:
    st.subheader('Intervention comparison')
    hosts = st.multiselect('Hosts to simulate', range(len(observed[-1].node_ids)), format_func=lambda i: observed[-1].node_ids[i])
    if st.button('Run isolation simulations', disabled=not hosts):
        with st.spinner('Comparing the same observed history and random draws…'):
            st.session_state['interventions'] = compare_isolations(model, observed, hosts, k, draws, seed)
    comparisons = st.session_state['interventions']
    if comparisons:
        st.dataframe(comparisons, hide_index=True)
        best = comparisons[0]
        if best['risk_reduction'] > 0:
            st.write(f"Lowest simulated risk: {best['host']} ({best['future_risk']:.1%}). Analyst review required.")
        else:
            st.write('No simulated isolation reduces model risk.')
    st.caption('Edge-cut sensitivity only: incident edges are removed from the last observed graph; measured node features and history are retained. Random draws match the displayed forecast. This does not model future containment effects or execute a network action. Port blocking is unavailable until raw-port mutation semantics are verified for normalized inputs.')
effects = {r['host_index']: r['risk_reduction'] for r in st.session_state['interventions'] if r['host_index'] is not None}
graph_slot.graphviz_chart(network_dot(observed[-1], effects))
with st.expander('Why this forecast?'):
    if st.button('Compute model explanation'):
        with st.spinner('Computing feature sensitivity and temporal attention…'):
            with torch.no_grad():
                st.session_state['explanation'] = model.forecast(observed, k, n_rollouts=draws, seed=seed)['explanation']
    if st.session_state['explanation'] is not None:
        st.json(st.session_state['explanation'])
    st.caption('Attention and feature perturbations explain model sensitivity, not causality. No attack-path attribution is inferred from topology alone.')
with st.expander('Case lineage and export'):
    st.json(lineage)
    st.caption('Prepared cases exclude their held-out target. Uploaded captures are treated as entirely observed and unlabeled. No future labels are used to declare resets.')
    report = {'lineage': lineage, 'forecast': rows, 'interventions': st.session_state['interventions'],
              'explanation': st.session_state['explanation'], 'seed': seed, 'n_rollouts': draws,
              'interpretation': 'Model-based forecast for analyst review; no causal or autonomous-response claim.'}
    st.download_button('Download case JSON', json.dumps(report, indent=2, allow_nan=False),
                       file_name=f'cybermind_case_{index}.json', mime='application/json')
