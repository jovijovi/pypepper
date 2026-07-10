# DB Helper

Thin connection helpers for MySQL, PostgreSQL, and MongoDB. Not an ORM or repository layer.

## Local services

```shell
docker compose -f devenv/ci.yaml up -d --wait
```

| Engine | Default URL / settings |
|--------|------------------------|
| MySQL | `mysql+pymysql://root:example@localhost:3306/...` |
| PostgreSQL | `postgresql+psycopg://postgres:example@localhost:5432/...` |
| MongoDB | `mongodb://test:test@localhost:27017/test` |

Exact credentials live in `devenv/ci.yaml` and the helper tests under `tests/helper/`.

## MySQL

```python
from pypepper.helper.db import mysql

cfg = mysql.Config(
    host="localhost",
    port=3306,
    username="root",
    password="example",
    db="test",
)
conn = mysql.connect(cfg)
assert mysql.ping(conn)
```

## PostgreSQL

```python
from pypepper.helper.db import postgres

cfg = postgres.Config(
    host="localhost",
    port=5432,
    username="postgres",
    password="example",
    db="test",
)
conn = postgres.connect(cfg)
assert postgres.ping(conn)
```

## MongoDB

```python
from pypepper.helper.db import mongodb

cfg = mongodb.Config(
    host="localhost",
    port=27017,
    username="test",
    password="test",
    db="test",
)
mongodb.connect(cfg)
mongodb.close()
```

!!! tip
    Prefer environment-specific secrets outside the repo. The devenv passwords are for local/CI only.
