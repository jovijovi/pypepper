# Tracing

PyPepper ships optional [OpenTelemetry](https://opentelemetry.io/) tracing. It is **off by default**.

When enabled, the library creates:

- One **SERVER** span per HTTP request (`TracingMiddleware`), including `request_id` when set by `RequestIdMiddleware`
- One span around `Workflow.run` (`scheduler.workflow.run`)

`Context.trace(index)` in `pypepper.common.context` is unrelated — it walks the local context chain.

## Configuration

Add a `tracing` section to YAML (see `conf/app.config.yaml`):

```yaml
tracing:
  enabled: false
  serviceName: pypepper   # falls back to serviceInfo.serviceName
  console: false          # print spans to the terminal
  otlp:
    enabled: false
    endpoint: http://127.0.0.1:4318   # Jaeger / OTLP HTTP base URL
```

| Setting | Effect |
|---------|--------|
| `enabled: false` | No-op provider; no exporters |
| `enabled: true` + `console: true` | `ConsoleSpanExporter` → terminal |
| `enabled: true` + `otlp.enabled: true` | OTLP HTTP → `{endpoint}/v1/traces` |
| Both console and otlp | Spans go to terminal **and** collector |

`config.load_config()` calls `setup_from_config()` automatically.

## Console (logs)

```yaml
tracing:
  enabled: true
  serviceName: pypepper
  console: true
  otlp:
    enabled: false
    endpoint: http://127.0.0.1:4318
```

Run an example and hit an endpoint; span JSON appears on stdout.

## Jaeger UI (local / devenv only)

Jaeger is provided for **development and manual verification**, not CI or production.

Start the pinned all-in-one image:

```shell
docker compose -f devenv/dev.yaml up -d jaeger
# or:
docker run --rm --name jaeger \
  -p 16686:16686 -p 4317:4317 -p 4318:4318 \
  jaegertracing/all-in-one:1.76.0
```

Enable OTLP (and optionally console):

```yaml
tracing:
  enabled: true
  serviceName: pypepper
  console: true
  otlp:
    enabled: true
    endpoint: http://127.0.0.1:4318
```

```shell
python example/server/app.py
curl -s http://127.0.0.1:55550/health
```

Open http://localhost:16686 → search service **pypepper**.

## Correlation with request_id

HTTP access logs still use `X-Request-ID` / `log.request_id()`. The same value is set as span attribute `request_id` so you can join logs and traces.
