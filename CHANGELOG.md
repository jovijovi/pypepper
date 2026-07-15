# Changelog

## Unreleased

### Added
- Pluggable scheduler `Job.save` store with `memory` (default), `postgres`, `mysql`, and `mongodb` backends.

### Fixed
- Scheduler persist-failure semantics: roll back pre-execution schedule failures; keep terminal COMPLETE/FAIL when snapshot write fails (retry `save` only).
- SQL job store raises `ValueError` for incomplete connection config instead of `AssertionError`.
- Roll back and delete Scheduled snapshot when a bounded channel rejects enqueue; `Job.to_record()` uses FSM status.

## 0.6.0

### Fixed
- Isolate FSM transition tables per instance; `close()` only clears the current machine.
- Roll back FSM state when a transition or caller handler raises.
- Isolate `CacheSet` storage and per-`Cache` locks across instances.
- Make `Channel.stop` per-instance; enforce explicit singletons for `Dispatcher`, `ChannelManager`, `SSEConnectionManager`, and `Loader`.
- Give each scheduler `Job` its own FSM via `build_scheduler_fsm()`.
- Stop mutating the global logger in `log.request_id()` (returns a bound logger).
- Atomic SSE rate-limit increments; constant-time API key comparison.
- SSE connection limit checks run under the same lock as registration.

### Security
- Remove committed default SSE API keys from `conf/app.config.yaml` (inject via deployment / `PYPEPPER_SSE_API_KEY` for the example).
- Reject query-string `api_key` for SSE (headers only: `X-API-Key` / `Authorization: Bearer`).
- Protect example `/sse/stats` with API key auth.

### Changed
- README refreshed as the project landing page (domains, highlights, quick start; details stay in MkDocs).
- Event `sign`/`verify` use stable JSON canonical bytes instead of `pickle` (existing pickle signatures will not verify).
- SSE connection/queue/stream limits read from YAML `sse.*` with hardcoded fallbacks.
- HTTP server registers default request-id middleware and supports TLS via `certFile`/`keyFile`/`caFile`.
- Tighten mypy on TOP3 static paths (`crypto`, HTTP/SSE skeleton, scheduler structure) with `disallow_untyped_defs` + `warn_return_any` (scoped overrides; dynamic/third-party modules unchanged).

### Added
- Tag-triggered PyPI publish workflow (`.github/workflows/publish.yml`) via Trusted Publisher when `v*` matches `pyproject.toml`.
- Coverage gate: `fail_under = 90` / `--cov-fail-under=90` on local `make test` and CI.
- Dependabot weekly updates for pip (`requirements*.txt` / `pyproject.toml`) and GitHub Actions (not Docker images).
- MkDocs API Reference via `mkdocstrings` (`docs/reference/`, curated public modules).
- OpenTelemetry tracing (opt-in via `tracing` YAML): console exporter and OTLP HTTP to local Jaeger; HTTP + `Workflow.run` spans.
- `py.typed` PEP 561 marker and `Typing :: Typed` classifier (typed package for consumers after next PyPI release).
- `Event.marshal()` JSON envelope.
- Scheduler `CallableExecutor`, sequential `Workflow.run` with retries/optional tasks, and `Worker` channel consumer.
- Structured `/metrics` payload (uptime + optional SSE stats).
- `scripts/check_mutable_class_attrs.py` CI guard; isolation/rollback regression tests.
- MkDocs Material documentation site (`docs/`, `mkdocs.yml`) with architecture and domain guides.
- `ruff` + `mypy` lint gate (`make lint` / CI lint job) and `make docs` (`mkdocs build --strict`).
- GitHub Pages documentation site at https://jovijovi.github.io/pypepper/ (deployed from `main` via `.github/workflows/docs.yml`).
