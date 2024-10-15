<div align="center">

![logo](docs/logo/logo.svg)

</div>

# PyPepper

In memory of my father who passed away due to COVID-19.

[![PyPI](https://img.shields.io/pypi/v/pypepper?label=\&logo=pypi\&logoColor=fff)](https://pypi.org/project/pypepper/)
[![GitHub Actions](https://github.com/jovijovi/pypepper/workflows/Test/badge.svg)](https://github.com/jovijovi/pypepper)
[![Coverage](https://img.shields.io/codecov/c/github/jovijovi/pypepper?label=\&logo=codecov\&logoColor=fff)](https://codecov.io/gh/jovijovi/pypepper)

- <https://github.com/jovijovi/pypepper>
- PyPepper is a microservice toolkit written in [Python](https://www.python.org).

## Features

### ***common***

Common packages.

- `common.context` A powerful chained context
- `common.security.crypto.elliptic.ecdsa` Sign/Verify message by ECDSA
- `common.security.crypto.digest` Get hash bytes/hex
- `common.security.crypto.salt` Generates a random salt of the specified size
- `common.utils.random` A class for generating random values
- `common.utils.retry` Retry running the function by random interval, support lambda
- `common.utils.time` Get UTC/local datetime/timezone/timestamp, support sleep
- `common.utils.uuid` UUID(v4) generator
- `common.cache` A thread safe TTL cache-set
- `common.log` A simple logger based on [loguru](https://github.com/Delgan/loguru)
- `common.options` An easy-to-use options
- `common.system` System signals handler

### ***event***

An event package with payload, support sign/verify signature.

### ***fsm***

An out-of-box FSM with event trigger, support custom state.

### ***helper***

Database helper.

- `helper.db.mongodb` MongoDB helper
- `helper.db.mysql` MySQL helper

### ***network***

- `network.http` RESTFul API server based on [FastAPI](https://github.com/tiangolo/fastapi). 

### ***scheduler***

A Workflow-based job scheduler.

### ***loader***

Module loader.

## Development Environment

- python `3.10`,`3.11`,`3.12`
- conda >= `22.9.0`

## Quick Guide

- Build code

  Install all dependencies and compile code.

  ```shell
  make build
  ```

- Test with coverage

  ```shell
  make test
  ```

- Build docker image

  ```shell
  make docker
  ```

- Clean

  ```shell
  make clean
  ```

## Roadmap

- [ ] Documents
- [ ] Tracing
