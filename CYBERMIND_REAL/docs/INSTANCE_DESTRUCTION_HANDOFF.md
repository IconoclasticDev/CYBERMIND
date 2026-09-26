# Vast.ai Instance Destruction Handoff

**Audit date:** 26 September 2026  
**Repository:** `IconoclasticDev/cybermind`  
**Audited artifact commit:** `11b8292aacb7b9d9735e1afb11a26845f64038e0`

The local and remote Git heads matched at the audited commit after the final periodic checkpoints were uploaded. The live `cybermind_status` writer was stopped before this handoff so runtime logs could no longer modify the working tree.

## Preserved on GitHub

- Complete project source, configurations, scripts, tests and knowledge files.
- Final grouped training history, all 25 epoch reports, validation/test evaluations and split audit.
- Baseline suite, raw comparison results, presentation guide and PNG/SVG slide assets.
- Two-page architecture document, final implementation plans and contingency report.
- Streamlit offline analyst console and coverage-aware stage evidence layer.
- Selected epoch-21 checkpoint, final-state checkpoint and periodic epoch 5/10/15/20/25 checkpoints.
- Portable SIH submission ZIP and integrity manifest.

## Critical artifact hashes

| Artifact | SHA-256 |
|---|---|
| `checkpoints/final_grouped/best.pt` | `5324902ca017e946af58b41fbd576561553d7c03b532b37ee9255f4a3677cf39` |
| `checkpoints/final_grouped/best_last.pt` | `624eb40612206d5b9fb7ea78685991e18bbb097d43d357b4f28cc3bc7ca27dc7` |
| `epochs/epoch_0005.pt` | `23b242a1f294cb43c5b1df228b72c1e0db4786a4b691fdea6127736a4f95dae5` |
| `epochs/epoch_0010.pt` | `0e4c259eb6ecd85e0f37a89c8d0f121f26df1dfc36869ebaacc85a65c4bd5456` |
| `epochs/epoch_0015.pt` | `7c37abc9dbcf03d54c0a080f76bc128091c1e8d5dc53e2a4dc39a134197d7ef1` |
| `epochs/epoch_0020.pt` | `a4af68094b40f1cd97fd68a7455563888d418d377be9afee6d5c47952c6a6587` |
| `epochs/epoch_0025.pt` | `66b8a661dac07eae24df54e027506ad5b0046f9112f80dcb0b8a718a0e001097` |
| `releases/CYBERMIND_SIH_SUBMISSION_2026-09-26.zip` | `e1f73ea47cbb0925b36287076a73cde9cbad97e61ffd0c074771af3279931312` |

The ZIP contains 355 verified files, is 12,545,118 bytes, and passed both ZIP integrity validation and every internal per-file SHA-256 check.

## Deliberately not uploaded

- Raw CIC-IDS2018 data and packet captures.
- Intermediate and processed datasets.
- Credentials, environment files, caches and Git metadata.
- Transient 15-minute monitoring-log updates.

Destroying the instance will therefore require re-downloading and rebuilding the datasets for future retraining. It will not remove any code, selected/final/periodic model checkpoint, final metric, report or submission artifact needed for SIH review and demonstration.
