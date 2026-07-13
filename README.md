<div align="center">

![logo](docs/logo/logo.svg)

</div>

# PyPepper

[![PyPI](https://img.shields.io/pypi/v/pypepper?label=\&logo=pypi\&logoColor=fff)](https://pypi.org/project/pypepper/)
[![GitHub Actions](https://github.com/jovijovi/pypepper/workflows/Test/badge.svg)](https://github.com/jovijovi/pypepper)
[![Coverage](https://img.shields.io/codecov/c/github/jovijovi/pypepper?label=\&logo=codecov\&logoColor=fff)](https://codecov.io/gh/jovijovi/pypepper)

> _In memory of my father, who passed away in 2023 from COVID-19._

PyPepper is a microservice toolkit.

<https://github.com/jovijovi/pypepper>

## :book: Documentation

Online docs: <https://jovijovi.github.io/pypepper/>

Architecture overview, getting started, and domain guides. Local preview:

```shell
make docs-serve
```

Source lives under [`docs/`](docs/index.md) (`mkdocs.yml`). Build with `make docs` (`mkdocs build --strict`).

## :checkered_flag: Features

### ***common***

Common packages.

- `context`
  - `common.context` A powerful chained context
- `security`
  - `common.security.crypto.elliptic.ecdsa` Sign/Verify message by ECDSA
  - `common.security.crypto.digest` Get hash bytes/hex
  - `common.security.crypto.salt` Generates a random salt of the specified size
- `utils`
  - `common.utils.random` A class for generating random values
  - `common.utils.retry` Retry running the function by random interval, support lambda
  - `common.utils.time` Get UTC/local datetime/timezone/timestamp, support sleep
  - `common.utils.uuid` UUID(v4) generator
- `cache`
  - `common.cache` A thread safe TTL cache-set
- `log`
  - `common.log` A simple logger based on [loguru](https://github.com/Delgan/loguru)
- `options`
  - `common.options` An easy-to-use options
- `system`
  - `common.system` System signals handler

### ***event***

An event package with payload, support sign/verify signature.

### ***fsm***

An out-of-box FSM with event trigger, support custom state.

### ***helper***

Database helper.

- `helper.db.mongodb` MongoDB helper
- `helper.db.mysql` MySQL helper
- `helper.db.postgres` PostgreSQL helper

### ***network***

- `network.http` RESTFul API server based on [FastAPI](https://github.com/tiangolo/fastapi). 

### ***scheduler***

A Workflow-based job scheduler.

### ***loader***

Module loader.

## :computer: Quick Guide

- Development Environment
  - python `3.10`,`3.11`,`3.12`,`3.13`,`3.14`
  - uv >= `0.10.7`

- Build code

  Install all dependencies and compile code.

  ```shell
  make build
  ```

- Lint (ruff + mypy)

  ```shell
  make lint
  ```

- Test with coverage

  ```shell
  make test
  ```

  `make test` runs `make check` first (`make lint` + `scripts/check_mutable_class_attrs.py`).

- Docs

  ```shell
  make docs
  make docs-serve
  ```

- Build docker image

  ```shell
  make docker
  ```

- Clean

  ```shell
  make clean
  ```

- SSE example

  Set a local API key (default config ships with empty `validKeys`):

  ```shell
  export PYPEPPER_SSE_API_KEY=your-local-key
  python example/sse/app.py
  ```

## :bulb: Roadmap

- [x] Documents
- [x] Tracing
- [x] Harden shared mutable state / FSM rollback / SSE auth defaults
- [x] ruff + mypy CI gate
