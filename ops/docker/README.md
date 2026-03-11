# ops/docker

Container configuration assets for local and CI runtime topology.

Primary compose entrypoint:
- repository root `compose.yml`

M0 note:
- `api_app`, `orchestrator_worker`, and `communication_worker` are scaffold placeholders in M0.
- these services will be replaced with real runtime commands as M1/M2 implementation lands.

Config assets in this folder:
- `otel-collector-config.yaml`
- `prometheus.yml`
- `tempo.yaml`
- `loki.yaml`
