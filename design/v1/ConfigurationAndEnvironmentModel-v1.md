# OpenQilin v1 - Configuration and Environment Model

## 1. Scope
- Define environment names, config precedence, and secret handling.
- Define local-first configuration expectations for all major runtime services.

## 2. Environments
- `local_dev`
- `ci`
- `staging`
- `production`

v1 initial implementation focus:
- `local_dev`
- `ci`

## 3. Configuration Precedence
Highest to lowest:
1. process environment variables
2. environment-specific local config files not committed with secrets
3. checked-in non-secret defaults

Rules:
- secrets never live in committed config files
- every config value must have one documented owner and source
- production/staging secrets must come from external secret references

## 4. Config Domains
### 4.1 Core Runtime
- `OPENQILIN_ENV`
- `OPENQILIN_LOG_LEVEL`
- `OPENQILIN_TRACE_SAMPLING`

### 4.2 API and Identity
- `DISCORD_APPLICATION_ID`
- `DISCORD_PUBLIC_KEY`
- `DISCORD_BOT_TOKEN` when required
- allowlisted guild/channel identifiers

### 4.3 Data Stores
- `POSTGRES_DSN`
- `REDIS_URL`

### 4.4 Policy and Governance
- `OPA_BASE_URL`
- active policy bundle reference/config

### 4.5 LLM Gateway
- `LITELLM_BASE_URL` when externalized
- `OPENQILIN_LLM_ROUTING_PROFILE`
- `GEMINI_API_KEY`

### 4.6 Observability
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- Grafana/trace/log backend endpoints as selected

## 5. v1 Local Defaults
`local_dev` defaults:
- routing profile: `dev_gemini_free`
- local services resolved through Docker Compose network aliases where possible
- reduced but non-zero tracing enabled

`ci` defaults:
- routing profile: `dev_gemini_free`
- deterministic test-safe settings
- tighter timeouts for test feedback where appropriate

## 6. Secret Handling Rules
- local secrets live in untracked env files or shell environment
- cloud secrets live in managed secret store references
- secrets must not be logged, traced, or written to artifacts
- sample config files may show variable names only, never real values

## 7. Config Validation
- startup must validate required config by app role
- missing required config for governed path must fail closed
- optional config must have documented fallback behavior

## 8. Related Design Follow-Ups
- workstation prerequisites are in `DeveloperWorkstationAndPrerequisites-v1.md`
- local startup flow is in `BootstrapAndMigrationWorkflow-v1.md`
- library/config loader choice is in `ImplementationFrameworkSelection-v1.md`
