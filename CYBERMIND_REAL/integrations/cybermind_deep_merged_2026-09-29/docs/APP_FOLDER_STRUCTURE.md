# CYBERMIND Full Application Folder Structure

```text
CYBERMIND_REAL/
├── AGENT.md
├── APP_AGENT.md                         # app-building agent contract
├── README.md
├── pyproject.toml
├── requirements.txt
├── requirements-app.txt                 # FastAPI/UI runtime deps
│
├── models/
│   └── cybermind_final.pt               # PLACE FINAL TRAINED MODEL HERE
│
├── export/
│   └── cybermind_compact.onnx           # optional deployment export
│
├── app/
│   ├── main.py                          # FastAPI entrypoint
│   ├── api/
│   │   ├── routes_health.py
│   │   ├── routes_model.py
│   │   ├── routes_telemetry.py
│   │   ├── routes_forecast.py
│   │   ├── routes_scenarios.py
│   │   ├── routes_counterfactual.py
│   │   └── routes_experiments.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── services/
│   │   ├── model_runtime.py             # model loader + inference adapter
│   │   ├── telemetry_service.py
│   │   ├── state_engine.py
│   │   ├── forecast_service.py
│   │   ├── explain_service.py
│   │   ├── counterfactual_service.py
│   │   ├── replay_service.py
│   │   ├── experiment_store.py
│   │   └── websocket_service.py
│   └── adapters/
│       ├── scenario_base.py
│       ├── replay.py
│       └── docker_sandbox.py             # safe isolated adapter
│
├── web/
│   ├── index.html                         # offline war room
│   ├── app.js
│   └── styles.css
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── replay/
│   └── runs/
│
├── knowledge/
│   └── ...
│
├── sandbox/
│   ├── docker-compose.yml
│   └── README.md
│
├── src/cybermind/                         # existing ML core
│   ├── data/
│   ├── models/
│   ├── evaluation/
│   ├── explainability/
│   └── counterfactual/
│
├── scripts/
│   ├── train.py
│   ├── eval.py
│   ├── app.py                             # legacy Streamlit prototype
│   └── ...
│
├── notebooks/
│   └── 08_colab_t4_train.ipynb
│
├── tests/
│   ├── test_imports.py
│   ├── test_onnx_cpu.py
│   ├── app/
│   │   ├── test_health.py
│   │   ├── test_model_runtime.py
│   │   ├── test_telemetry.py
│   │   └── test_forecast.py
│   └── fixtures/
│
└── docs/
    ├── SIH26153_CYBERMIND_Master_Plan.md
    ├── ARCHITECTURE.md
    ├── APP_BUILD_SPEC.md
    ├── APP_ARCHITECTURE.md
    └── APP_FOLDER_STRUCTURE.md
```

## Implementation priority

### Already exists

The ML core, training scripts, public-data preparation, baseline, explainability primitives, counterfactual simulator, and isolated sandbox skeleton already exist.

### New application layer

The `app/` and `web/` trees are intentionally thin. An AI coding IDE should implement production details around these boundaries without changing the ML research core.

### Model placement

The only manual binary dependency for the finished application is:

`models/cybermind_final.pt`

Everything else should be reproducible from source/configuration.
