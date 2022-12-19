# PyPedro

[![GitHub Actions](https://github.com/jovijovi/pypedro/workflows/Test/badge.svg)](https://github.com/jovijovi/pypedro)
[![Coverage](https://img.shields.io/codecov/c/github/jovijovi/pypedro?label=\&logo=codecov\&logoColor=fff)](https://codecov.io/gh/jovijovi/pypedro)

<https://github.com/jovijovi/pypedro>

PyPedro is a microservice toolkit written in [Python](https://www.python.org).

## Features

- `common`
  - `context` A powerful chained context
  - `security`
    - `crypto.elliptic.ecdsa` Sign/Verify message by ECDSA
    - `crypto.digest` Get hash bytes/hex
    - `crypto.salt` Generates a random salt of the specified size
  - `utils`
    - `random` A class for generating random values
    - `retry` Retry running the function by random interval, support lambda
    - `time` Get UTC/local datetime/timezone/timestamp, support sleep
    - `uuid` UUID(v4) generator
  - `cache` A thread safe TTL cache-set
  - `log` A simple logger in Pedro style
  - `options` An easy-to-use options
  - `system` System signals handler
- `event` An event package with payload, support sign/verify signature
- `fsm` An out-of-box FSM with event trigger, support custom state
- `helper`
  - `db.mongodb` MongoDB helper
  - `db.mysql` MySQL helper
- `network`
  - `http` RESTFul APIs sever based on [Flask](https://github.com/pallets/flask/). 
- `loader` Module loader

## Roadmap

- Documents
- Tracing
