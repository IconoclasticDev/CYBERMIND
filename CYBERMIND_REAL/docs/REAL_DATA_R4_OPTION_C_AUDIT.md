# R4 option (c) implementation audit

Date: 2026-09-20  
Decision: reviewer-authorized option (c); options (a) and (b) rejected.  
Status: implementation and verification complete; **training has not restarted**.

## Scope and result

Only the CRF structured training loss can now omit the seven authorized March 1
boundaries. The exclusion is opt-in in `configs/real_chunk_r4.yaml` and is
carried by explicit, provenance-rich metadata on the destination state. A false
entry splits that sample's CRF likelihood into two independent contiguous
segments. This avoids scoring the named edge without inventing a legal
transition or reset.

Stage cross-entropy still receives every target, including all seven destination
states. `StageDecoder.decode()`, `knowledge/stage_mapping.yaml`, and
`src/cybermind/evaluation/metrics.py` are unchanged. The transition matrix,
Viterbi constraint, and illegal-transition-rate definition therefore remain
strict.

The derivative is `data/processed_real_chunk_r4_option_c`. It was created
atomically from `data/processed_real_chunk_r4_reviewed_resets`; the generated
tensors are locally retained and intentionally ignored by Git. Their hashes are
recorded in `crf_loss_exclusion_provenance.json`.

## Exact seven-boundary exception set

| ID | Stage pair | Source window (UTC) | Destination window (UTC) | Corrected-rule context |
|---|---|---|---|---|
| `mar1_dropbox_135342` | Initial Access → Benign | 2018-03-01 13:53:12.813819 | 2018-03-01 13:53:42.813819 | Both starts inside Dropbox interval |
| `mar1_dropbox_135742` | Initial Access → Benign | 2018-03-01 13:57:12.813819 | 2018-03-01 13:57:42.813819 | Both starts inside Dropbox interval |
| `mar1_nmap_142012` | Reconnaissance → Benign | 2018-03-01 14:19:42.813819 | 2018-03-01 14:20:12.813819 | Both starts inside NMAP interval |
| `mar1_nmap_143012` | Reconnaissance → Benign | 2018-03-01 14:29:42.813819 | 2018-03-01 14:30:12.813819 | Both starts inside NMAP interval |
| `mar1_nmap_145642` | Reconnaissance → Benign | 2018-03-01 14:56:12.813819 | 2018-03-01 14:56:42.813819 | Both starts inside NMAP interval |
| `mar1_nmap_184712` | Reconnaissance → Benign | 2018-03-01 18:46:42.813819 | 2018-03-01 18:47:12.813819 | Both starts inside NMAP interval |
| `mar1_nmap_193812` | Reconnaissance → Benign | 2018-03-01 19:37:42.813819 | 2018-03-01 19:38:12.813819 | Source window overlaps the corrected NMAP end; destination starts 0.631093 seconds after it and remains in the explicitly authorized seven-boundary set |

The campaign reference is the pinned
[Distrinet corrected-rule notebook at commit f0ce502](https://github.com/GintsEngelen/CNS2022_Code/blob/f0ce502818e59e6cd062720ab2286c5ff6f2bdec/Labelling/CICIDS2018_labelling_fixed_CICFlowMeter.ipynb).
The preserved local notebook SHA256 is
`e58bea8651f4c891383f3cf1e735de4b48f50c4ec8a9aef078b53972dca1422e`.
This exception is tied to this real-chunk dataset and is not a general
relaxation of the CRF policy.

## Coverage and identity audit

Overlapping 16-state histories repeat physical states and edges. The counts
below distinguish the seven unique boundaries from their repeated appearances.

| Split | Samples | Illegal occurrences under unchanged policy | Modeled CRF edges excluded | First-target occurrences outside CRF edge model | Unhandled modeled illegal edges | Legal modeled edges excluded |
|---|---:|---:|---:|---:|---:|---:|
| Train | 1,699 | 91 | 86 | 5 | 0 | 0 |
| Validation | 428 | 0 | 0 | 0 | 0 | 0 |
| Test | 431 | 0 | 0 | 0 | 0 | 0 |

The audit compared every source and derivative sample. Node tensors, edges,
edge features, labels, timestamps, sample structure, normalization, and existing
metadata are identical. Only the documented exclusion provenance was added.
There are exactly seven unique exclusion IDs; validation and test are clean and
contain no exclusion metadata.

Evidence hashes:

- `crf_loss_exclusion_provenance.json`:
  `61d4755396b116ded160f8615283708269b5ef05b3ad2e3732a841702ba8520d`
- `option_c_audit.json`:
  `fdc6e8bf927c29b24f6512a47449138dd36fff38a084309a439aaacb04dd9f2e`
- unchanged `knowledge/stage_mapping.yaml`:
  `8ffb2afefbebcdbeadb8635c0cb4b313d871a88731521bb82c1fb07885121253`
- unchanged `src/cybermind/evaluation/metrics.py`:
  `310ae920968d891a71b6691baf8ae2a08306b28dad8f670e2971429c0bcd5578`

## Loss behavior verification

Focused tests prove that an exclusion equals the sum of the two independent
segment NLLs, gradients remain finite, a false first mask entry is rejected,
and decoding still produces only policy-legal transitions. The integration
test also proves three conditions: exclusion metadata is refused unless the
reviewed config opts in, the excluded destination remains in stage
cross-entropy, and the original illegal-target failure returns when the
metadata is removed.

Focused result: **25 passed, 3 skipped**.

## Full-suite re-verification and artifact provenance

The final repository-wide run used the project's established repository-local
pytest temporary directory because the default Windows temporary directory is
inaccessible in this environment. It performed unfiltered default discovery:

```text
.\.phase01-venv\Scripts\python.exe -m pytest -q --basetemp=.r4-full-suite-final-tmp --junitxml=examples\real_data_validation\r4\regression_final\pytest.xml
```

Final result: **206 passed, 13 skipped, 64 warnings in 11.19 seconds**. The
increase from the historical 203 passes is exactly the three newly added
option-(c) tests.

| Artifact | SHA256 |
|---|---|
| `regression_final/pytest.log` | `9ba8c1e09545dba9c1d1cc337b3c4ae1ff8773ef13ad070870eb5b07f4e0f1c8` |
| `regression_final/pytest.xml` | `e07145a80b0550b4bdfad7b87ec1918e0748bf70f759685ecac02d11c3297c5d` |
| `regression_final/pytest_run_manifest.json` | `90c0c76202dcd259f93230ad27b663f617666c31272e52ea6e830521a4d6f5e9` |

For completeness, two preceding attempts are also preserved. The first was
blocked during collection by Windows Application Control loading scikit-learn's
native `_cd_fast` module. The second collected but encountered 23 pytest temp
directory access errors. Those are tooling/environment outcomes, not test
failures, and neither is substituted for the final passing run.

## R4 status and mandatory disclosures

No training process was started. No checkpoint or new R4 metric exists. The R4
exit criterion remains **NOT MET** until a reviewer explicitly approves the
second training attempt and that run satisfies the unchanged gates.

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**
