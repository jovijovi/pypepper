from pypepper.common.config import config
from pypepper.common.log import log
from pypepper.scheduler.store import get_job_store, reset_job_store
from pypepper.scheduler.store.memory import InMemoryJobStore


def test_load_config():
    config.load_config("./conf/app.config.yaml")
    result = config.get_yml_config()
    assert result is not None
    assert result.network.httpServer.port == 55550
    assert result.log.level == "TRACE"
    assert result.sse.maxTotalConnections == 100
    assert list(result.sse.authentication.validKeys) == []


def test_load_config_does_not_configure_job_store(monkeypatch, tmp_path):
    """common.config must not import or call scheduler.store (layering)."""
    import pypepper.common.config as config_mod
    import pypepper.scheduler.store as store_mod

    src = open(config_mod.__file__).read()
    assert "from pypepper.scheduler.store" not in src
    assert "import pypepper.scheduler.store" not in src

    calls: list[str] = []
    monkeypatch.setattr(
        store_mod,
        "setup_from_config",
        lambda *a, **k: calls.append("setup_from_config"),
    )
    monkeypatch.setattr(
        store_mod,
        "configure_job_store",
        lambda *a, **k: calls.append("configure_job_store"),
    )

    # Durable backend in YAML would reconfigure the store if setup were wired back.
    cfg = tmp_path / "durable-jobstore.yaml"
    cfg.write_text(
        "scheduler:\n"
        "  jobStore:\n"
        "    backend: postgres\n"
        "    uri: postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper\n"
    )

    reset_job_store()
    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))
    config.load_config(str(cfg))

    assert calls == []
    assert isinstance(get_job_store(), InMemoryJobStore)
    assert any("setup_from_config" in w for w in warns)


def test_load_config_memory_job_store_does_not_warn(monkeypatch):
    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))
    reset_job_store()
    config.load_config("./conf/app.config.yaml")
    assert not any("jobStore" in w for w in warns)
