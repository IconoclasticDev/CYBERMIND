# CTU-13 access check — 2026-09-14

- [x] Official dataset documentation and public scenario directory reachable without credentials.
- [x] No access-request portal or reviewer authorization is required for the public files. No request or message was sent.
- [x] No corpus files downloaded in Phase 4.

The official dataset page provides labeled bidirectional flows for 13 scenarios. It states that complete PCAPs containing normal/background traffic are withheld for privacy; public PCAPs contain botnet traffic only. Consequently, public flow access does **not** establish packet-feature parity across the complete held-out population. [Official CTU-13 documentation](https://www.stratosphereips.org/datasets-ctu13), [public scenario directory](https://mcfp.felk.cvut.cz/publicDatasets/CTU-13-Dataset/).

CTU-13 remains held out from primary CIC-IDS2018 training. A packet-required model cannot honestly be evaluated on every CTU-13 class using botnet-only PCAPs, nor should missing packet features be silently filled and reported as feature parity. Record this as a cross-dataset evaluation limitation and resolve the evaluation protocol separately; no gate or packet requirement is loosened here. Flow-only baseline results, if later produced, must be labeled as a separate feature setting.
