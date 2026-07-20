# Common

Shared kernel: config, logging, chained context, TTL cache, crypto, and utilities.

## Config

```python
from pypepper.common.config import config

config.load_config("./conf/app.config.yaml")
yml = config.get_yml_config()
print(yml.network.httpServer.port)
print(yml.sse.authentication.enabled)
```

`load_config()` without a path uses CLI `--config` or the default `./conf/app.config.yaml`.
It applies log level and optional tracing setup. It does **not** configure the scheduler job
store — call `pypepper.scheduler.store.setup_from_config(config.get_yml_config())` after load
when YAML includes `scheduler.jobStore` (see [Scheduler](scheduler.md)). If YAML declares a
non-`memory` `jobStore.backend`, `Job.save` / `Job.get_saved` raise `ValueError` until you
call `setup_from_config`, `configure_job_store`, or `set_job_store`. If a non-memory store is
already installed, a later durable `load_config` does not false-positive. `reset_job_store`
re-arms deferred fail-fast from the current YAML.

## Logging

```python
from pypepper.common.log import log

log.info("hello")
bound = log.request_id("req-123")
bound.info("scoped message")
```

`request_id()` returns a bound logger and does not mutate the process-wide singleton.

## Context

```python
from pypepper.common.context import new, born

ctx = new(context_id="root")
child = ctx.with_value("user_id", 42)
assert child.context["user_id"] == 42

chain = born(length=3)
assert chain.length() == 3
assert chain.head().index == 0
```

## Cache

```python
from pypepper.common.cache import Cache, new_cache_set

cache = Cache(maxsize=128, ttl=60)
cache.set("k", "v")
assert cache.get("k") == "v"

s = new_cache_set()
c = s.new("ns", maxsize=32, ttl=30)
c.set("a", 1)
```

Each `Cache` / `CacheSet` instance owns its own storage and locks.

## Crypto helpers

Prefer `sha256` (or stronger) for digests and ECDSA signatures.
`digest.get` / `get_hex_str` reject `md5` / `sha1` with `ValueError`.
ECDSA `HashAlgorithmName` no longer defines MD5/SHA1; passing those names to
sign/verify raises `InternalException`.

```python
from pypepper.common.security.crypto import digest, salt
from pypepper.common.security.crypto.elliptic.ecdsa import ecdsa

digest_bytes = digest.get(b"payload", "sha256")
random_salt = salt.new(16)

private_key = ecdsa.new_key_pair()
pem = ecdsa.get_private_key_pem(private_key)
pub = ecdsa.get_public_key_pem(private_key)
sig = ecdsa.sign(b"msg", pem, "sha256")
assert ecdsa.verify(b"msg", pub, sig, "sha256")
```

## Utilities

```python
from pypepper.common.utils import time, uuid
from pypepper.common.utils.retry import run

print(time.get_utc_datetime())
print(uuid.new_uuid())

result = run(lambda: 1 + 1, retry_times=3, retry_interval=0)
```

See also: [API Reference / Common](../reference/common.md).
