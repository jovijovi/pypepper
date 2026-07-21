# Changelog

## Unreleased

### Added
- `Task.retry_until_max` (default 1000): per-round attempt cap when `retry_until_completed=True` and `retry_count==0`.

### Changed
- `Workflow` now honors `round_times`, `round_timeout` (soft per-execute timeout in seconds; orphaned work may overlap retries), and `retry_until_completed` with `retry_count` / `retry_until_max`. Previously these fields were stored but unused.

### Fixed
- Soft `round_timeout`: if the worker finishes successfully in the wait-timeout race window, return its result instead of re-raising `TimeoutError`.

## 0.6.2

### Breaking
- `digest.get` / `get_hex_str` reject `md5` / `sha1` with `ValueError` (one-shot warn removed).
- ECDSA `HashAlgorithmName.MD5` / `SHA1` removed from the enum (`AttributeError` on access); constructing those digests raises `InternalException`.
- `config.load_config()` records a deferred durable `scheduler.jobStore.backend`; `Job.save` / `Job.get_saved` raise `ValueError` until `setup_from_config` / `configure_job_store` / `set_job_store` is called (was a warning only). Deferred is cleared when a non-memory store is already installed (configure-before-load / reload). `reset_job_store` re-arms deferred from the current YAML so memory cannot silently replace a YAML-declared but unapplied durable backend.

### Added
- Public `FSM.restore(state)` for lifecycle rollback; `Job.restore_lifecycle` uses it (no `_fsm._current` writes).
- `Job.cancel()` for Scheduled/InProgress jobs; Worker skips cancelled jobs and does not COMPLETE after cancel at workflow boundaries.
- Scheduler E2E example (`example/scheduler/app.py`).
- Tag publish workflow runs lint + pytest before PyPI upload.
- Dependabot Docker updates for `docker/` (literal `FROM python:3.13.14-slim-trixie` pins, aligned with Makefile).
- CI / `make audit` run `pip-audit==2.10.1` on production `requirements.txt` (ignores via `.pip-audit-ignore.txt`; auditor pinned in `requirements-dev`).
- Tutorial: [First service](docs/tutorials/first-service.md) (scheduler COMPLETE + optional SSE).
- `CONTRIBUTING.md` and GitHub issue templates.

### Removed
- Unused ghost config types/keys: `cluster`, `heartbeat`, `network.jsonRPCProxy`, HTTP(S) `timeout`, `log.mode`, `sse.enabled`, `sse.heartbeatIntervalSeconds`.

### Changed
- Scheduler `CANCEL` FSM transition accepts Scheduled and InProgress.
- Worker retries Cancelled persist on cancel exits and does not restore pre-RUN over a winning cancel; cancel persist failures are surfaced.
- Docs: architecture config table drops ghost keys; scheduler guide / CLAUDE / AGENTS Start(`RUN`) note cancel-won skip-restore; Cancel persist rules separated from Worker COMPLETE/FAIL.
- Coverage measurement includes branch coverage (`branch = true`); `fail_under` remains 90.

## 0.6.1

### Added
- Pluggable scheduler `Job.save` store with `memory` (default), `postgres`, `mysql`, and `mongodb` backends.
- Curated domain re-exports (for example `from pypepper.scheduler import Job`); `common.config` / `common.log` stay submodule imports to avoid shadowing.
- `SECURITY.md` vulnerability reporting policy.

### Changed
- `config.load_config()` no longer configures the scheduler job store; apps call `scheduler.store.setup_from_config` explicitly after load.
- `config.load_config()` warns when YAML declares a non-`memory` `scheduler.jobStore.backend` that has not been applied.
- `Job.scheduled()` / `Processor.run` raise `RuntimeError` when an event loop is already running; async callers must `INIT`→`SCHEDULE`, `save()`, then `await Channel.send` + `Worker`.
- Helper DB connectors raise `ValueError` (not `assert`) for falsy config / incomplete SQL discrete fields (Mongo only rejects falsy `cfg`); discrete SQL URIs use `quote_plus` for credentials.
- SSE warns once when authentication is disabled; guide documents auth-off / rate-limit footguns.

### Fixed
- Scheduler persist-failure semantics: roll back pre-execution schedule failures; keep terminal COMPLETE/FAIL when snapshot write fails (retry `save` only).
- SQL job store raises `ValueError` for incomplete connection config instead of `AssertionError`.
- Harden FSM transition checks; preserve `created` on upsert across memory/SQL/Mongo; validate Mongo config.
- Roll back on enqueue failure (channel full or other) with best-effort delete (ghost possible); do not roll back after successful channel send.
- Document post-enqueue raise as committed enqueue (job may still run); Mongo disconnect hard-fails on non-benign errors.
- `Job.to_record()` uses FSM status.

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
